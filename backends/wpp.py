"""Real backend: drives WhatsApp Web in a Chromium window (Playwright) and uses the
open-source WA-JS library (github.com/wppconnect-team/wa-js) to list chats and download media.

All Playwright calls happen on ONE worker thread (Playwright's sync API is not thread-safe);
other threads submit work through a queue.
"""
import concurrent.futures, os, queue, threading, time, base64
from pathlib import Path

from . import qr_data_url

WAJS_URLS = [
    "https://github.com/wppconnect-team/wa-js/releases/latest/download/wppconnect-wa.js",
    "https://cdn.jsdelivr.net/npm/@wppconnect/wa-js@latest/dist/wppconnect-wa.js",
]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")

JS_POLL = """async () => {
  if (!window.WPP || !window.WPP.conn) return {a: false, r: false, code: null, booting: true};
  const a = WPP.conn.isAuthenticated(), r = WPP.conn.isMainReady();
  let code = null;
  if (!a) {
    try {
      const p = WPP.conn.getAuthCode();
      const c = window.__wpsRace ? await window.__wpsRace(p, 8000) : await p;
      code = c && c.fullCode;
    } catch (e) {}
  }
  return {a, r, code};
}"""

# WA-JS calls can hang forever (e.g. chat.list() while WhatsApp is still syncing history),
# which would block the single Playwright worker thread. Race every call against a timer.
JS_RACE = """() => {
  window.__wpsRace = (p, ms) => Promise.race([
    Promise.resolve(p),
    new Promise((_, rej) => setTimeout(() => rej(new Error('wps-timeout')), ms)),
  ]);
}"""

JS_ME = """async () => {
  try {
    const id = WPP.conn.getMyUserId();
    const serialized = (id && id._serialized) || String(id || '');
    let name = '';
    try { name = (WPP.profile && WPP.profile.getMyProfileName && WPP.profile.getMyProfileName()) || ''; } catch (e) {}
    if (!name) {
      try { name = (WPP.whatsapp && WPP.whatsapp.Conn && WPP.whatsapp.Conn.pushname) || ''; } catch (e) {}
    }
    let pic = null;
    try { const p = await window.__wpsRace(WPP.contact.getProfilePicture(serialized), 8000); pic = p && (p.eurl || p.img || null); } catch (e) {}
    return {name, pic};
  } catch (e) { return {}; }
}"""

JS_CHATS = """async () => {
  const list = await window.__wpsRace(WPP.chat.list(), 30000);
  return list.map(c => {
    const id = (c.id && c.id._serialized) || String(c.id);
    const name = c.name || c.formattedTitle || (c.contact && (c.contact.name || c.contact.pushname)) || id.split('@')[0];
    return {id, name};
  });
}"""

# Pages backwards through a chat until we pass the start of the range, returns image messages in range.
JS_PHOTOS = """async ({chatId, start, end}) => {
  const seen = new Map();
  let ref = null, stalls = 0;
  const sid = m => typeof m.id === 'string' ? m.id : (m.id._serialized || String(m.id));
  for (let i = 0; i < 400; i++) {
    const opts = {count: 100, direction: 'before'};
    if (ref) opts.id = ref;
    let msgs = [];
    try { msgs = await window.__wpsRace(WPP.chat.getMessages(chatId, opts), 60000); } catch (e) { break; }
    let before = seen.size, oldest = null;
    for (const m of msgs) {
      const id = sid(m); seen.set(id, m);
      if (!oldest || (m.t || 0) < (oldest.t || 0)) oldest = m;
    }
    if (!oldest || seen.size === before) { if (++stalls >= 2) break; } else stalls = 0;
    if (oldest && oldest.t * 1000 < start) break;
    if (oldest) ref = sid(oldest);
  }
  // Album children carry associationType=MEDIA_ALBUM and point at a parent album message.
  // WhatsApp stores the album's single caption on one of the children, so share it across the group.
  const albumKey = m => {
    try {
      if (String(m.associationType || '') !== 'MEDIA_ALBUM') return '';
      const k = m.parentMsgKey;
      return (k && (k.id || k._serialized)) || '';
    } catch (e) { return ''; }
  };
  const albumCaptions = new Map();
  for (const [, m] of seen) {
    if (m.type !== 'image') continue;
    const a = albumKey(m);
    if (!a) continue;
    const cap = String(m.caption || '').trim();
    if (cap && !albumCaptions.has(a)) albumCaptions.set(a, cap);
  }
  const captionFor = m => {
    const a = albumKey(m);
    if (!a) return String(m.caption || '').trim();
    let cap = albumCaptions.get(a) || '';
    if (!cap) {
      const p = seen.get(a);
      if (p) cap = String(p.caption || p.body || '').trim();
    }
    return cap;
  };
  const out = [];
  for (const [id, m] of seen) {
    if (m.type !== 'image') continue;
    const ms = (m.t || 0) * 1000;
    if (ms < start || ms > end) continue;
    const raw = (m.author && m.author._serialized) || (m.from && m.from._serialized) || '';
    const sender = m.id && m.id.fromMe ? 'Me' :
      (m.notifyName || (m.senderObj && (m.senderObj.name || m.senderObj.pushname)) || raw.split('@')[0] || 'unknown');
    const ext = ((m.mimetype || 'image/jpeg').split('/')[1] || 'jpg').split(';')[0].replace('jpeg', 'jpg');
    out.push({id, ts: m.t, sender, ext, caption: captionFor(m), album: albumKey(m)});
  }
  out.sort((a, b) => a.ts - b.ts);
  return out;
}"""

JS_FETCH = """async (msgId) => {
  const blob = await window.__wpsRace(WPP.chat.downloadMedia(msgId), 60000);
  if (!blob) throw new Error('media not available (expired or still downloading)');
  return await new Promise((res, rej) => {
    const fr = new FileReader();
    fr.onload = () => res(String(fr.result).split(',')[1]);
    fr.onerror = () => rej(new Error('read failed'));
    fr.readAsDataURL(blob);
  });
}"""


class WPPBackend:
    def __init__(self, data_dir, log):
        self.log = log
        self.data_dir = Path(data_dir)
        self.profile = self.data_dir / "wa_profile"
        self.q = queue.Queue()
        self._st = {"state": "starting"}
        self._st_lock = threading.Lock()
        self._code = None
        self._qr = None
        self._me = None
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # ---- state ----
    def _set(self, **kw):
        with self._st_lock:
            self._st = kw

    def status(self):
        with self._st_lock:
            return dict(self._st)

    # ---- calling into the worker thread ----
    def _call(self, fn, timeout=600):
        fut = concurrent.futures.Future()
        self.q.put((fn, fut))
        return fut.result(timeout=timeout)

    def list_chats(self):
        return self._call(lambda p: p.evaluate(JS_CHATS))

    def list_photos(self, chat_id, start_ms, end_ms):
        return self._call(lambda p: p.evaluate(JS_PHOTOS, {"chatId": chat_id, "start": start_ms, "end": end_ms}), timeout=1800)

    def fetch_photo(self, chat_id, meta):
        b64 = self._call(lambda p: p.evaluate(JS_FETCH, meta["id"]), timeout=120)
        return base64.b64decode(b64)

    def logout(self):
        def do(p):
            try:
                p.evaluate("WPP.conn.logout()")
            except Exception:
                pass
            self._boot(p)
        self._call(do, timeout=120)
        self._me = None

    def shutdown(self):
        self._stop = True

    # ---- worker ----
    def _script(self):
        import requests
        cache = self.data_dir / "wppconnect-wa.js"
        if cache.exists() and cache.stat().st_size > 100_000:
            return cache.read_text(encoding="utf-8")
        last = None
        for url in WAJS_URLS:
            try:
                r = requests.get(url, timeout=60)
                r.raise_for_status()
                cache.write_text(r.text, encoding="utf-8")
                return r.text
            except Exception as e:
                last = e
        raise RuntimeError(f"Could not download WA-JS helper library: {last}")

    def _boot(self, page):
        page.goto("https://web.whatsapp.com", wait_until="load")
        # WhatsApp Web sends a strict CSP: add_script_tag() is blocked as an inline script and
        # wait_for_function() is blocked as eval. evaluate() is exempt, so inject that way and
        # poll for readiness from Python instead.
        page.evaluate(self._script())
        for _ in range(120):
            if page.evaluate("() => !!(window.WPP && window.WPP.isReady)"):
                page.evaluate(JS_RACE)
                return
            time.sleep(1)
        raise RuntimeError("WA-JS did not become ready (WhatsApp Web may have changed)")

    def _run(self):
        try:
            from playwright.sync_api import sync_playwright
            self.data_dir.mkdir(parents=True, exist_ok=True)
            pw = sync_playwright().start()
            ctx = pw.chromium.launch_persistent_context(
                str(self.profile),
                headless=os.environ.get("WPS_HEADLESS") == "1",
                viewport={"width": 1100, "height": 800},
                user_agent=UA,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            self.log("Opening WhatsApp Web…")
            self._boot(page)
        except Exception as e:
            self._set(state="error", error=f"{type(e).__name__}: {e}")
            self.log(f"Startup failed: {e}")
            return

        announced = False
        while not self._stop:
            try:
                fn, fut = self.q.get(timeout=1.0)
            except queue.Empty:
                self._poll(page)
                if self.status().get("state") == "ready" and not announced:
                    self.log("WhatsApp Web ready")
                    announced = True
                continue
            try:
                fut.set_result(fn(page))
            except Exception as e:
                fut.set_exception(e)
        try:
            ctx.close()
            pw.stop()
        except Exception:
            pass

    def _poll(self, page):
        try:
            if not page.evaluate("() => typeof window.WPP !== 'undefined'"):
                # WhatsApp Web reloads itself after linking, which wipes the injected WA-JS.
                self.log("WhatsApp Web reloaded — reattaching…")
                page.evaluate(self._script())
                page.evaluate(JS_RACE)
                self._me = None
                self._code = self._qr = None
                self._set(state="authenticated")
                return
            r = page.evaluate(JS_POLL)
            if r.get("booting"):
                self._set(state="starting")
                return
            authed = bool(r.get("a"))
            # isMainReady() is true even on the "scan the QR" screen on current WhatsApp Web,
            # so it on its own would never show the login screen.
            if authed and r.get("r"):
                if self._me is None:
                    self._me = page.evaluate(JS_ME) or {}
                self._set(state="ready", me=self._me)
            elif authed:
                if self.status().get("state") != "authenticated":
                    self.log("Authenticated with WhatsApp")
                self._set(state="authenticated")
            elif r.get("code"):
                if r["code"] != self._code:
                    self._code, self._qr = r["code"], qr_data_url(r["code"])
                self._set(state="qr", qr=self._qr)
            elif self._qr:
                # WhatsApp rotates the QR every ~20 s and getAuthCode() can briefly return
                # null in between. Keep serving the last code so the page doesn't flash.
                self._set(state="qr", qr=self._qr)
            else:
                self._set(state="starting")
        except Exception as e:
            self._set(state="error", error=f"{type(e).__name__}: {e}")
