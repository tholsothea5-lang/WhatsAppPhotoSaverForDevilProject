void async function wpsBookmarklet() {
  'use strict';
  const W = window, D = document;
  const VERSION = '1.0.0';
  const enc = new TextEncoder();

  const prev = W.__WPS_BM;
  if (prev && prev.host && prev.host.isConnected) {
    prev.host.style.filter = 'brightness(1.35)';
    setTimeout(() => { prev.host.style.filter = ''; }, 450);
    return;
  }

  /* ---------- small helpers ---------- */
  const mk = (tag, cls, text) => {
    const n = D.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const pad = n => String(n).padStart(2, '0');
  const dmy = d => `${pad(d.getDate())}-${pad(d.getMonth() + 1)}-${d.getFullYear()}`;
  const stamp = d => `${dmy(d)}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));

  // Mirrors safe() in app.py so ZIP folder names match the desktop app.
  function safe(name, limit) {
    limit = limit || 60;
    let s = String(name == null ? '' : name)
      .replace(/[\\/:*?"<>|\r\n\t]+/g, '_')
      .replace(/^[ ._]+|[ ._]+$/g, '');
    if (s.length > limit) {
      let cut = s.slice(0, limit);
      const sp = cut.lastIndexOf(' ');
      if (sp >= Math.floor(limit / 2)) cut = cut.slice(0, sp);
      s = cut;
    }
    s = s.replace(/^[ ._]+|[ ._]+$/g, '');
    return s || 'unnamed';
  }

  const openDb = () => new Promise((res, rej) => {
    const rq = indexedDB.open('model-storage');
    rq.onsuccess = () => res(rq.result);
    rq.onerror = () => rej(rq.error || new Error('could not open WhatsApp storage'));
    rq.onblocked = () => rej(new Error('WhatsApp storage is busy - close other tabs'));
  });

  const storeGetAll = (db, store) => new Promise((res, rej) => {
    const rq = db.transaction(store, 'readonly').objectStore(store).getAll();
    rq.onsuccess = () => res(rq.result || []);
    rq.onerror = () => rej(rq.error || new Error(store + ' read failed'));
  });

  const storeGet = (db, store, key) => new Promise(res => {
    try {
      const rq = db.transaction(store, 'readonly').objectStore(store).get(key);
      rq.onsuccess = () => res(rq.result || null);
      rq.onerror = () => res(null);
    } catch (e) { res(null); }
  });

  function mediaForChat(db, chatId) {
    const pfx = chatId + '_';
    return new Promise((res, rej) => {
      try {
        const idx = db.transaction('message', 'readonly').objectStore('message')
          .index('[internalId+isMediaMsg]');
        const rq = idx.getAll(IDBKeyRange.bound([pfx, -Infinity], [pfx + '\uffff', Infinity]));
        rq.onsuccess = () => res(rq.result || []);
        rq.onerror = () => rej(rq.error || new Error('message query failed'));
      } catch (e) { rej(e); }
    });
  }

  /* ---------- live message models ----------
     IndexedDB stores captions only inside the encrypted msgRowOpaqueData blob, so the
     plain records never carry them. WhatsApp keeps a module loader on the page, and its
     hydrated Msg models do expose .caption. We call that directly - no script injection,
     no eval, nothing that WhatsApp's CSP blocks. If the internals ever change we simply
     fall back to "No caption" instead of failing the download. */
  function msgCollection() {
    try {
      if (typeof W.require !== 'function') return null;
      const mc = W.require('WAWebMsgCollection');
      return (mc && mc.MsgCollection) || null;
    } catch (e) { return null; }
  }

  function withTimeout(p, ms, label) {
    return Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error(label)), ms))]);
  }

  const liveId = m => {
    const id = m && m.id;
    if (!id) return '';
    return typeof id === 'string' ? id : (id._serialized || String(id));
  };

  async function hydrateModels(ids) {
    const MC = msgCollection();
    if (!MC || !ids.length) return [];
    const out = [];
    for (let i = 0; i < ids.length; i += 60) {
      const chunk = ids.slice(i, i + 60);
      let got = null;
      try {
        got = await withTimeout(Promise.resolve(MC.hydrateOrGetMessages(chunk)), 20000, 'timeout');
      } catch (e) { got = null; }
      if (Array.isArray(got)) { out.push(...got); continue; }
      for (const id of chunk) {
        let m = null;
        try { m = MC.get(id); } catch (e) { m = null; }
        if (m) out.push(m);
      }
    }
    return out;
  }

  async function sha1Hex(text) {
    const d = new Uint8Array(await crypto.subtle.digest('SHA-1', enc.encode(text)));
    let s = '';
    for (const b of d) s += b.toString(16).padStart(2, '0');
    return s;
  }

  /* ---------- decrypt ---------- */
  async function decryptMedia(m) {
    let res;
    try {
      res = await fetch('https://mmg.whatsapp.net' + m.directPath,
        { credentials: 'omit', cache: 'no-store' });
    } catch (e) { throw new Error('network error'); }
    if (!res.ok) {
      throw new Error('HTTP ' + res.status + (res.status === 404 || res.status === 410 ? ' (expired)' : ''));
    }
    const buf = new Uint8Array(await res.arrayBuffer());
    if (buf.length < 26) throw new Error('file too small');

    const infoStr = m.type === 'video' ? 'WhatsApp Video Keys' : 'WhatsApp Image Keys';
    const base = await crypto.subtle.importKey('raw', b64(m.mediaKey), 'HKDF', false, ['deriveBits']);
    const d = new Uint8Array(await crypto.subtle.deriveBits(
      { name: 'HKDF', hash: 'SHA-256', salt: new Uint8Array(32), info: enc.encode(infoStr) },
      base, 112 * 8));
    const iv = d.slice(0, 16), cipherKey = d.slice(16, 48), macKey = d.slice(48, 80);

    const aesKey = await crypto.subtle.importKey('raw', cipherKey, 'AES-CBC', false, ['decrypt']);
    const hmacKey = await crypto.subtle.importKey('raw', macKey, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
    const expected = Number(m.size) || 0;

    async function attempt(ciphertext, ivUse, mac) {
      if (!mac || mac.length !== 10 || !ciphertext.length || ciphertext.length % 16) return null;
      const joined = new Uint8Array(ivUse.length + ciphertext.length);
      joined.set(ivUse); joined.set(ciphertext, ivUse.length);
      const sig = new Uint8Array(await crypto.subtle.sign('HMAC', hmacKey, joined)).slice(0, 10);
      for (let i = 0; i < 10; i++) if (sig[i] !== mac[i]) return null;
      try {
        const plain = new Uint8Array(await crypto.subtle.decrypt({ name: 'AES-CBC', iv: ivUse }, aesKey, ciphertext));
        if (expected && plain.length !== expected) return null;
        return plain;
      } catch (e) { return null; }
    }

    // WhatsApp media layout: ciphertext || 10-byte MAC, IV is derived (not stored).
    let plain = await attempt(buf.slice(0, buf.length - 10), iv, buf.slice(buf.length - 10));
    if (plain) return plain;
    // Fallback for builds that prefix the IV.
    plain = await attempt(buf.slice(16, buf.length - 10), buf.slice(0, 16), buf.slice(buf.length - 10));
    if (plain) return plain;
    throw new Error('could not decrypt');
  }

  /* ---------- zip (STORE, no compression) ---------- */
  const CRC = (() => {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      t[n] = c >>> 0;
    }
    return t;
  })();
  function crc32(u8) {
    let c = 0xFFFFFFFF;
    for (let i = 0; i < u8.length; i++) c = CRC[(c ^ u8[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }
  function dosTime(d) {
    const year = Math.max(1980, d.getFullYear());
    return {
      time: (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1),
      date: ((year - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate(),
    };
  }
  function zipAdd(zip, name, data, when) {
    const nb = enc.encode(name);
    const crc = crc32(data);
    const t = dosTime(when);

    const lh = new Uint8Array(30 + nb.length);
    const lv = new DataView(lh.buffer);
    lv.setUint32(0, 0x04034b50, true);
    lv.setUint16(4, 20, true);
    lv.setUint16(6, 0x0800, true);
    lv.setUint16(8, 0, true);
    lv.setUint16(10, t.time, true);
    lv.setUint16(12, t.date, true);
    lv.setUint32(14, crc, true);
    lv.setUint32(18, data.length, true);
    lv.setUint32(22, data.length, true);
    lv.setUint16(26, nb.length, true);
    lv.setUint16(28, 0, true);
    lh.set(nb, 30);

    const at = zip.offset;
    zip.parts.push(lh, data);
    zip.offset += lh.length + data.length;

    const ch = new Uint8Array(46 + nb.length);
    const cv = new DataView(ch.buffer);
    cv.setUint32(0, 0x02014b50, true);
    cv.setUint16(4, 20, true);
    cv.setUint16(6, 20, true);
    cv.setUint16(8, 0x0800, true);
    cv.setUint16(10, 0, true);
    cv.setUint16(12, t.time, true);
    cv.setUint16(14, t.date, true);
    cv.setUint32(16, crc, true);
    cv.setUint32(20, data.length, true);
    cv.setUint32(24, data.length, true);
    cv.setUint16(28, nb.length, true);
    cv.setUint32(42, at, true);
    ch.set(nb, 46);
    zip.central.push(ch);
  }
  function zipBlob(zip) {
    const cdStart = zip.offset;
    let cdSize = 0;
    for (const c of zip.central) { zip.parts.push(c); cdSize += c.length; }
    const e = new Uint8Array(22);
    const dv = new DataView(e.buffer);
    dv.setUint32(0, 0x06054b50, true);
    dv.setUint16(8, zip.central.length, true);
    dv.setUint16(10, zip.central.length, true);
    dv.setUint32(12, cdSize, true);
    dv.setUint32(16, cdStart, true);
    zip.parts.push(e);
    return new Blob(zip.parts, { type: 'application/zip' });
  }

  /* ---------- data shaping ---------- */
  const albumKey = m => {
    if (String(m.associationType || '') !== 'MEDIA_ALBUM') return '';
    const k = m.parentMsgKey;
    if (!k) return '';
    return typeof k === 'string' ? k : (k.id || k._serialized || '');
  };

  function extFor(m) {
    const sub = String(m.mimetype || 'image/jpeg').split('/')[1] || 'jpg';
    return sub.split(';')[0].replace(/jpeg/gi, 'jpg').replace(/[^a-z0-9]/gi, '') || 'jpg';
  }

  /* ---------- state ---------- */
  const S = {
    db: null, chats: [], contacts: new Map(), items: [],
    running: false, cancel: false, chatId: ''
  };

  /* ---------- ui ---------- */
  const CSS = `
    :host { all: initial; }
    * { box-sizing: border-box; }
    .panel {
      width: 380px; max-width: calc(100vw - 24px);
      background: #111b21; color: #e9edef;
      border: 1px solid #2a3942; border-radius: 12px;
      box-shadow: 0 12px 40px rgba(0,0,0,.5);
      font: 13px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      overflow: hidden;
    }
    .hd { display: flex; align-items: center; gap: 8px; padding: 10px 12px;
          background: #202c33; border-bottom: 1px solid #2a3942; }
    .hd b { font-size: 13.5px; font-weight: 600; flex: 1; }
    .ver { color: #8696a0; font-size: 11px; }
    .x { border: 0; background: transparent; color: #8696a0; font-size: 18px;
         line-height: 1; cursor: pointer; padding: 2px 4px; border-radius: 4px; }
    .x:hover { background: #2a3942; color: #e9edef; }
    .bd { padding: 12px; display: grid; gap: 10px; }
    label.f { display: grid; gap: 4px; font-size: 11.5px; color: #8696a0; }
    select, input[type=text], input[type=date] {
      width: 100%; background: #2a3942; color: #e9edef;
      border: 1px solid #3b4a54; border-radius: 7px;
      padding: 7px 8px; font: inherit; font-size: 12.5px; outline: none;
    }
    select:focus, input:focus { border-color: #00a884; }
    .two { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .chk { display: flex; align-items: center; gap: 7px; font-size: 12.5px; color: #d1d7db; }
    .chk input { accent-color: #00a884; width: 14px; height: 14px; }
    .row { display: flex; gap: 8px; }
    button.act {
      flex: 1; border: 0; border-radius: 7px; padding: 8px 10px;
      font: inherit; font-weight: 600; font-size: 12.5px; cursor: pointer;
      background: #00a884; color: #0b141a;
    }
    button.act:hover:not(:disabled) { background: #06cf9c; }
    button.act:disabled { opacity: .4; cursor: default; }
    button.ghost { background: #2a3942; color: #e9edef; }
    button.ghost:hover:not(:disabled) { background: #3b4a54; }
    .hint { font-size: 11px; color: #8696a0; }
    .status { min-height: 32px; font-size: 12px; color: #d1d7db; white-space: pre-wrap; word-break: break-word; }
    .status.err { color: #f15c6d; }
    .status.ok { color: #06cf9c; }
    progress { width: 100%; height: 6px; accent-color: #00a884; }
    .log { max-height: 84px; overflow: auto; font: 11px/1.4 ui-monospace, Consolas, monospace;
           color: #f1aeb5; background: #0b141a; border-radius: 6px; padding: 6px 8px;
           white-space: pre-wrap; word-break: break-word; }
    details { font-size: 11.5px; color: #8696a0; }
    details summary { cursor: pointer; }
    details p { margin: 6px 0 0; }
  `;

  const host = D.createElement('div');
  host.id = 'wps-bm-host';
  host.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2147483647;';
  const root = host.attachShadow({ mode: 'open' });
  const style = D.createElement('style');
  style.textContent = CSS;
  root.appendChild(style);

  const panel = mk('div', 'panel');

  const hd = mk('div', 'hd');
  hd.appendChild(mk('b', null, 'WhatsApp Photo Saver'));
  hd.appendChild(mk('span', 'ver', 'v' + VERSION));
  const btnClose = mk('button', 'x', '\u2715');
  btnClose.type = 'button';
  hd.appendChild(btnClose);
  panel.appendChild(hd);

  const bd = mk('div', 'bd');
  panel.appendChild(bd);

  const fChat = mk('label', 'f', 'Chat');
  const txtFilter = mk('input');
  txtFilter.type = 'text';
  txtFilter.placeholder = 'Filter chats\u2026';
  const selChat = mk('select');
  fChat.appendChild(txtFilter);
  fChat.appendChild(selChat);
  bd.appendChild(fChat);

  const fRange = mk('label', 'f', 'Date range');
  const selRange = mk('select');
  for (const [v, label] of [['1', 'Last 24 hours'], ['7', 'Last 7 days'], ['30', 'Last 30 days'],
    ['90', 'Last 90 days'], ['all', 'All time'], ['custom', 'Custom range']]) {
    const o = mk('option', null, label);
    o.value = v;
    selRange.appendChild(o);
  }
  fRange.appendChild(selRange);
  bd.appendChild(fRange);

  const custom = mk('div', 'two');
  const dFrom = mk('input'); dFrom.type = 'date';
  const dTo = mk('input'); dTo.type = 'date';
  custom.appendChild(dFrom); custom.appendChild(dTo);
  custom.hidden = true;
  bd.appendChild(custom);

  const chkVideo = mk('input'); chkVideo.type = 'checkbox';
  const lblVideo = mk('label', 'chk');
  lblVideo.appendChild(chkVideo);
  lblVideo.appendChild(mk('span', null, 'Include videos (mp4)'));
  bd.appendChild(lblVideo);

  const row = mk('div', 'row');
  const btnScan = mk('button', 'act', 'Scan');
  const btnGo = mk('button', 'act ghost', 'Download ZIP');
  const btnCancel = mk('button', 'act ghost', 'Cancel');
  btnScan.type = btnGo.type = btnCancel.type = 'button';
  btnGo.disabled = true;
  btnCancel.hidden = true;
  row.appendChild(btnScan); row.appendChild(btnGo); row.appendChild(btnCancel);
  bd.appendChild(row);

  const status = mk('div', 'status', 'Loading chats\u2026');
  bd.appendChild(status);

  const prog = mk('progress');
  prog.max = 100; prog.value = 0; prog.hidden = true;
  bd.appendChild(prog);

  const log = mk('div', 'log');
  log.hidden = true;
  bd.appendChild(log);

  const help = mk('details');
  help.appendChild(mk('summary', null, 'How files are organised'));
  help.appendChild(mk('p', null,
    'The ZIP contains one folder per chat, then a folder per date, then a folder per caption ' +
    '(or "No caption"). Files are named sender_date_time_hash.ext, matching the desktop app.'));
  bd.appendChild(help);

  const hint = mk('div', 'hint', 'Nothing leaves your browser. Expired media cannot be recovered.');
  bd.appendChild(hint);

  root.appendChild(panel);

  /* ---------- ui behaviour ---------- */
  const setStatus = (msg, cls) => {
    status.textContent = msg;
    status.className = 'status' + (cls ? ' ' + cls : '');
  };
  const addLog = msg => {
    log.hidden = false;
    log.textContent = (log.textContent ? log.textContent + '\n' : '') + msg;
    log.scrollTop = log.scrollHeight;
  };
  const setBusy = busy => {
    S.running = busy;
    btnScan.disabled = busy;
    btnGo.disabled = busy || !S.items.length;
    btnCancel.hidden = !busy;
    selChat.disabled = busy;
    selRange.disabled = busy;
    dFrom.disabled = busy;
    dTo.disabled = busy;
    chkVideo.disabled = busy;
    txtFilter.disabled = busy;
  };

  function setProgress(done, total, label) {
    prog.hidden = false;
    prog.value = total ? Math.round(done * 100 / total) : 0;
    if (label) setStatus(label);
  }

  panel.addEventListener('keydown', e => e.stopPropagation());
  panel.addEventListener('keyup', e => e.stopPropagation());
  panel.addEventListener('keypress', e => e.stopPropagation());
  panel.addEventListener('pointerdown', e => e.stopPropagation());

  btnClose.addEventListener('click', () => {
    S.cancel = true;
    host.remove();
    if (W.__WPS_BM && W.__WPS_BM.host === host) delete W.__WPS_BM;
  });

  selRange.addEventListener('change', () => {
    custom.hidden = selRange.value !== 'custom';
    if (selRange.value === 'custom' && !dFrom.value) {
      const d = new Date(Date.now() - 7 * 86400000);
      dFrom.value = d.toISOString().slice(0, 10);
      dTo.value = new Date().toISOString().slice(0, 10);
    }
  });

  /* ---------- chat list ---------- */
  function contactName(id) {
    const c = id && S.contacts.get(id);
    if (!c) return '';
    return c.name || c.shortName || c.pushname || c.notifyName || c.verifiedName || '';
  }

  function chatLabel(chat) {
    return chat.name || contactName(chat.id) || String(chat.id).replace(/@.*$/, '');
  }

  function renderChats(filter) {
    const q = String(filter || '').trim().toLowerCase();
    const keep = selChat.value;
    selChat.textContent = '';
    let shown = 0;
    for (const c of S.chats) {
      if (q && c.label.toLowerCase().indexOf(q) < 0) continue;
      const o = mk('option', null, c.label);
      o.value = c.id;
      selChat.appendChild(o);
      shown++;
    }
    if (!shown) {
      const o = mk('option', null, 'No chats match');
      o.value = '';
      selChat.appendChild(o);
    }
    if (keep && [...selChat.options].some(o => o.value === keep)) selChat.value = keep;
  }

  txtFilter.addEventListener('input', () => renderChats(txtFilter.value));

  /* ---------- load chats + contacts ---------- */
  async function loadChats() {
    S.db = await openDb();
    const [chats, contacts] = await Promise.all([
      storeGetAll(S.db, 'chat'),
      storeGetAll(S.db, 'contact')
    ]);
    for (const c of contacts) if (c && c.id) S.contacts.set(c.id, c);

    const skip = /^(status@broadcast|0@c\.us|.*@newsletter|.*@broadcast)$/;
    const list = [];
    for (const c of chats) {
      if (!c || !c.id || skip.test(String(c.id))) continue;
      list.push({ id: String(c.id), name: c.name || '', label: chatLabel(c) });
    }
    list.sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: 'base' }));

    const seen = new Map();
    for (const c of list) {
      const n = seen.get(c.label) || 0;
      seen.set(c.label, n + 1);
      if (n) c.label = c.label + ' \u00b7 ' + c.id.split('@')[0];
    }

    S.chats = list;
    renderChats('');
    setStatus(`Ready. ${list.length} chats found. Pick one, then Scan.`);
  }

  /* ---------- scan ---------- */
  function rangeBounds() {
    const v = selRange.value;
    const now = Math.floor(Date.now() / 1000);
    if (v === 'all') return { start: 0, end: now + 86400 };
    if (v === 'custom') {
      const s = dFrom.value ? Math.floor(new Date(dFrom.value + 'T00:00:00').getTime() / 1000) : 0;
      const e = dTo.value ? Math.floor(new Date(dTo.value + 'T23:59:59').getTime() / 1000) : now;
      return { start: s, end: e };
    }
    return { start: now - (Number(v) || 1) * 86400, end: now + 86400 };
  }

  function senderFor(m, chatId, lm) {
    if (String(m.id || liveId(lm)).startsWith('true_')) return 'Me';
    const raw = (m.author && (m.author._serialized ||
      (m.author.user ? m.author.user + '@' + (m.author.server || 'c.us') : ''))) ||
      (lm && lm.author && (lm.author._serialized ||
        (lm.author.user ? lm.author.user + '@' + (lm.author.server || 'c.us') : ''))) || '';
    const notify = (lm && lm.notifyName) || m.notifyName;
    if (String(chatId).endsWith('@g.us')) {
      return contactName(raw) || notify || (m.author && m.author.user) || 'unknown';
    }
    return contactName(chatId) || contactName(raw) || notify ||
      (raw ? String(raw).split('@')[0] : 'unknown');
  }

  async function scan() {
    if (S.running) return;
    const chatId = selChat.value;
    if (!chatId) { setStatus('Pick a chat first.', 'err'); return; }
    if (selRange.value === 'custom' && !dFrom.value && !dTo.value) {
      setStatus('Pick at least one custom date.', 'err'); return;
    }

    setBusy(true);
    S.cancel = false;
    S.items = [];
    S.chatId = chatId;
    log.hidden = true; log.textContent = '';
    prog.hidden = true;
    setStatus('Reading WhatsApp storage\u2026');

    try {
      const t0 = performance.now();
      const rows = await mediaForChat(S.db, chatId);
      const { start, end } = rangeBounds();
      const withVideo = chkVideo.checked;

      const picked = [];
      let outOfRange = 0, noKey = 0;
      for (const m of rows) {
        if (m.type !== 'image' && !(withVideo && m.type === 'video')) continue;
        const t = Number(m.t) || 0;
        if (t < start || t > end) { outOfRange++; continue; }
        if (!m.mediaKey || !m.directPath) { noKey++; continue; }
        picked.push(m);
      }
      picked.sort((a, b) => (Number(a.t) || 0) - (Number(b.t) || 0));

      // Album membership across ALL media rows, so a caption on an excluded video still counts.
      const albumMembers = new Map();
      for (const m of rows) {
        const a = albumKey(m);
        if (!a) continue;
        if (!albumMembers.has(a)) albumMembers.set(a, []);
        albumMembers.get(a).push(String(m.id || ''));
      }
      const albumKeys = new Set();
      for (const m of picked) {
        const a = albumKey(m);
        if (a) albumKeys.add(a);
      }

      const want = new Set(picked.map(m => String(m.id || '')));
      for (const a of albumKeys) {
        want.add(a);
        for (const id of (albumMembers.get(a) || [])) want.add(id);
      }

      setStatus(`Reading captions for ${want.size} messages\u2026`);
      const liveList = await hydrateModels([...want]);
      const liveById = new Map();
      for (const lm of liveList) liveById.set(liveId(lm), lm);

      const albumCaps = new Map();
      for (const a of albumKeys) {
        for (const id of (albumMembers.get(a) || [])) {
          const lm = liveById.get(id);
          const cap = lm ? String(lm.caption || '').trim() : '';
          if (cap) { albumCaps.set(a, cap); break; }
        }
        if (albumCaps.get(a)) continue;
        const lm = liveById.get(a);
        let cap = lm ? String(lm.caption || lm.body || '').trim() : '';
        if (!cap) {
          const rec = await storeGet(S.db, 'message', a);
          cap = rec ? String(rec.caption || rec.body || '').trim() : '';
        }
        if (cap) albumCaps.set(a, cap);
      }

      const items = picked.map(m => {
        const a = albumKey(m);
        const id = String(m.id || '');
        const lm = liveById.get(id);
        const own = String((lm && lm.caption) || m.caption || '').trim();
        return {
          m,
          id,
          ts: Number(m.t) || 0,
          sender: senderFor(m, chatId, lm),
          caption: a ? (albumCaps.get(a) || own) : own,
          album: a,
          ext: extFor(m),
        };
      });

      S.items = items;
      const ms = Math.round(performance.now() - t0);
      const vids = items.filter(i => i.m.type === 'video').length;
      const capped = items.filter(i => i.caption).length;
      if (!items.length) {
        setStatus(`No downloadable media in that range (${rows.length} media records for this chat).`, 'err');
      } else {
        const albums = albumKeys.size;
        setStatus(`Found ${items.length - vids} photo${items.length - vids === 1 ? '' : 's'}` +
          (vids ? ` + ${vids} video${vids === 1 ? '' : 's'}` : '') +
          (albums ? ` in ${albums} album${albums === 1 ? '' : 's'}` : '') +
          (capped ? `, ${capped} with captions` : '') +
          `.\nScanned in ${ms} ms. Press Download ZIP.`, 'ok');
        if (items.length > 400) {
          addLog(`Warning: ${items.length} files may exceed available browser memory.`);
        }
        if (!liveList.length) {
          addLog('Captions unavailable in this WhatsApp build; files go to "No caption".');
        }
        if (noKey) addLog(`${noKey} media record(s) had no download path (never cached by this device).`);
      }
      prog.hidden = true;
    } catch (e) {
      setStatus('Scan failed: ' + (e && e.message ? e.message : e), 'err');
    } finally {
      setBusy(false);
      btnGo.disabled = !S.items.length;
    }
  }

  /* ---------- download ---------- */
  async function download() {
    if (S.running || !S.items.length) return;
    setBusy(true);
    S.cancel = false;
    log.hidden = true; log.textContent = '';
    prog.hidden = false; prog.value = 0;

    const chat = S.chats.find(c => c.id === S.chatId);
    const chatFolder = safe(chat ? chat.label : S.chatId, 60);
    const zip = { parts: [], offset: 0, central: [] };

    let saved = 0, failed = 0;
    const total = S.items.length;
    let firstTs = 0, lastTs = 0;

    for (let i = 0; i < total; i++) {
      if (S.cancel) break;
      const it = S.items[i];
      setProgress(i, total, `Saving ${i + 1} of ${total}\u2026`);
      try {
        const data = await decryptMedia(it.m);
        const when = new Date(it.ts * 1000);
        const tail = (await sha1Hex(it.id)).slice(0, 6);
        const folder = it.caption ? safe(it.caption, 60) : 'No caption';
        const name = `${safe(it.sender, 30)}_${stamp(when)}_${tail}.${it.ext}`;
        zipAdd(zip, `${chatFolder}/${dmy(when)}/${folder}/${name}`, data, when);
        saved++;
        if (!firstTs || it.ts < firstTs) firstTs = it.ts;
        if (it.ts > lastTs) lastTs = it.ts;
      } catch (e) {
        failed++;
        if (failed <= 25) addLog(`${new Date(it.ts * 1000).toLocaleString()}: ${e && e.message ? e.message : e}`);
      }
    }

    setProgress(saved + failed, total, 'Building ZIP\u2026');
    try {
      const blob = zipBlob(zip);
      const from = new Date((firstTs || S.items[0].ts) * 1000);
      const to = new Date((lastTs || S.items[total - 1].ts) * 1000);
      const zipName = `WhatsApp Photos - ${safe(chat ? chat.label : 'chat', 40)} - ` +
        `${dmy(from)} to ${dmy(to)}.zip`;
      const url = URL.createObjectURL(blob);
      const a = D.createElement('a');
      a.href = url;
      a.download = zipName;
      D.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);

      const sizeMb = (blob.size / (1024 * 1024)).toFixed(1);
      const msg = (S.cancel ? 'Stopped. ' : 'Done. ') +
        `${saved} saved, ${failed} failed (${sizeMb} MB).\nZIP: ${zipName}`;
      setStatus(msg, failed ? 'err' : 'ok');
      if (failed) addLog('Failed files are usually expired on WhatsApp\u2019s servers (404/410).');
    } catch (e) {
      setStatus('ZIP failed: ' + (e && e.message ? e.message : e), 'err');
    } finally {
      prog.hidden = true;
      setBusy(false);
      btnGo.disabled = !S.items.length;
    }
  }

  btnScan.addEventListener('click', scan);
  btnGo.addEventListener('click', download);
  btnCancel.addEventListener('click', () => {
    S.cancel = true;
    setStatus('Cancelling\u2026');
  });

  D.body.appendChild(host);

  W.__WPS_BM = {
    host,
    api: {
      selectChat: id => { selChat.value = id; },
      setRange: v => { selRange.value = v; selRange.dispatchEvent(new Event('change')); },
      setVideos: on => { chkVideo.checked = !!on; },
      scan,
      download,
      state: S,
    }
  };

  try {
    await loadChats();
  } catch (e) {
    setStatus('Could not read WhatsApp storage: ' + (e && e.message ? e.message : e) +
      '\nMake sure WhatsApp Web is fully loaded and try again.', 'err');
  }
}();
