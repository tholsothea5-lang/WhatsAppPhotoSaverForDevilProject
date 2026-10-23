"""WhatsApp Photo Saver - local web tool.  Run:  python app.py   (add --demo to try the UI without WhatsApp)"""
import argparse, collections, hashlib, os, platform, re, subprocess, sys, threading, time, webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, abort, jsonify, render_template, request, send_file

from store import Store

DATA_DIR = Path(os.environ.get("WPS_DATA", Path.home() / ".whatsapp_photo_saver"))
DEFAULT_FOLDER = os.environ.get("WPS_FOLDER") or str(Path.home() / "WhatsAppPhotos")

app = Flask(__name__)
store = Store(DATA_DIR)
activity = collections.deque(maxlen=500)
act_lock = threading.Lock()
act_counter = 0
chat_names = {}
job = {"running": False, "message": ""}
backend = None


def log(msg):
    global act_counter
    with act_lock:
        act_counter += 1
        activity.append({"n": act_counter, "t": datetime.now().strftime("%I:%M:%S %p").lstrip("0"), "msg": msg})


def safe(name, limit=60):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", str(name)).strip(" ._")
    if len(name) > limit:
        cut = name[:limit]
        space = cut.rfind(" ")
        if space >= limit // 2:
            cut = cut[:space]
        name = cut
    return name.strip(" ._") or "unnamed"


def clipboard_path():
    """First path on the Windows clipboard (copied folder/file, or copied text)."""
    if platform.system() != "Windows":
        raise RuntimeError("reading the clipboard is only supported on Windows")
    import ctypes
    from ctypes import wintypes

    user32, shell32, kernel32 = ctypes.windll.user32, ctypes.windll.shell32, ctypes.windll.kernel32
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
    kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
    shell32.DragQueryFileW.restype = wintypes.UINT
    shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]

    opened = False
    for _ in range(20):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.05)
    if not opened:
        raise RuntimeError("the clipboard is busy — try again")
    try:
        text = ""
        if user32.IsClipboardFormatAvailable(15):  # CF_HDROP: files/folders copied in Explorer
            handle = user32.GetClipboardData(15)
            if shell32.DragQueryFileW(handle, 0xFFFFFFFF, None, 0):
                buf = ctypes.create_unicode_buffer(32768)
                shell32.DragQueryFileW(handle, 0, buf, len(buf))
                text = buf.value
        if not text and user32.IsClipboardFormatAvailable(13):  # CF_UNICODETEXT
            handle = user32.GetClipboardData(13)
            ptr = kernel32.GlobalLock(handle)
            if ptr:
                try:
                    text = ctypes.wstring_at(ptr)
                finally:
                    kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()

    text = (text or "").strip()
    if text:
        text = text.splitlines()[0].strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    if text.lower().startswith("file://"):
        from urllib.parse import unquote
        text = unquote(text[7:])
        if re.match(r"^/[A-Za-z]:", text):
            text = text[1:]
        text = text.replace("/", "\\")
    if not text:
        raise RuntimeError("the clipboard is empty")
    try:
        p = Path(os.path.expandvars(os.path.expanduser(text)))
        if p.is_file():
            p = p.parent
    except OSError:
        p = Path(text)
    return str(p)


@app.before_request
def same_origin_only():
    # Stop other websites from poking this local tool.
    if request.method == "POST":
        origin = request.headers.get("Origin")
        if origin and urlparse(origin).netloc != request.host:
            abort(403)


@app.get("/")
def index():
    return render_template("index.html", default_folder=DEFAULT_FOLDER)


@app.get("/api/status")
def status():
    s = backend.status()
    return jsonify({**s, "stats": store.stats(), "job": job, "demo": ARGS.demo})


@app.get("/api/chats")
def chats():
    try:
        items = backend.list_chats()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    chat_names.update({c["id"]: c["name"] for c in items})
    log(f"Found {len(items)} chats")
    return jsonify(items)


@app.get("/api/activity")
def get_activity():
    since = int(request.args.get("since", 0))
    with act_lock:
        return jsonify([a for a in activity if a["n"] > since])


@app.post("/api/download")
def download():
    if job["running"]:
        return jsonify({"error": "A download is already running."}), 409
    p = request.get_json(force=True)
    ids = p.get("chats") or []
    if not ids:
        return jsonify({"error": "Tick at least one chat."}), 400
    try:
        start, end = int(p["start"]), int(p["end"])
    except Exception:
        return jsonify({"error": "Choose a start and end date."}), 400
    if start >= end:
        return jsonify({"error": "Start must be before end."}), 400
    folder = Path(p.get("folder") or DEFAULT_FOLDER).expanduser()
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return jsonify({"error": f"Can't use that folder: {e}"}), 400
    threading.Thread(
        target=run_download,
        args=(ids, start, end, (p.get("sender") or "").strip().lower(), bool(p.get("skip", True)), folder),
        daemon=True,
    ).start()
    return jsonify({"ok": True})


def run_download(ids, start, end, sender, skip, folder):
    job.update(running=True, message="Downloading…")
    saved = skipped = failed = 0
    try:
        for cid in ids:
            cname = chat_names.get(cid, cid)
            log(f"Scanning {cname}…")
            try:
                metas = backend.list_photos(cid, start, end)
            except Exception as e:
                log(f"Could not read {cname}: {e}")
                store.bump("failed")
                failed += 1
                continue
            if sender:
                metas = [m for m in metas if sender in (m.get("sender") or "").lower()]
            log(f"{cname}: {len(metas)} photos in range")
            for m in metas:
                key = f"{cid}|{m['id']}"
                if skip and store.has(key):
                    store.bump("skipped")
                    skipped += 1
                    continue
                try:
                    data = backend.fetch_photo(cid, m)
                    when = datetime.fromtimestamp(m["ts"])
                    caption = (m.get("caption") or "").strip()
                    d = (folder / safe(cname) / when.strftime("%d-%m-%Y")
                         / (safe(caption, 60) if caption else "No caption"))
                    d.mkdir(parents=True, exist_ok=True)
                    tail = hashlib.md5(key.encode()).hexdigest()[:6]
                    path = d / f"{safe(m.get('sender'), 30)}_{when.strftime('%d-%m-%Y_%H%M%S')}_{tail}.{m.get('ext', 'jpg')}"
                    path.write_bytes(data)
                    store.add(key, path, {"chat": cname, "sender": m.get("sender"), "caption": caption, "ts": m["ts"]})
                    saved += 1
                except Exception as e:
                    store.bump("failed")
                    failed += 1
                    log(f"Failed one photo in {cname}: {e}")
        log(f"Done: {saved} saved, {skipped} skipped, {failed} failed")
    finally:
        job.update(running=False, message="")


@app.get("/api/recent")
def recent():
    return jsonify([
        {"id": r["id"], "name": Path(r["path"]).name, "folder": str(Path(r["path"]).parent)}
        for r in store.recent(int(request.args.get("n", 50)))
    ])


@app.get("/api/photo")
def photo():
    p = store.path_for(request.args.get("id", ""))
    if not p or not p.exists():
        abort(404)
    return send_file(p)


@app.post("/api/paste-path")
def paste_path():
    try:
        return jsonify({"path": clipboard_path()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.post("/api/open-folder")
def open_folder():
    folder = Path((request.get_json(force=True).get("folder") or DEFAULT_FOLDER)).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    try:
        if platform.system() == "Windows":
            os.startfile(folder)  # noqa
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})


@app.post("/api/logout")
def logout():
    try:
        backend.logout()
        log("Logged out of WhatsApp")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})


@app.post("/api/shutdown")
def shutdown():
    backend.shutdown()
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return jsonify({"ok": True})


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="fake WhatsApp (no login) to preview the UI")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--no-browser", action="store_true")
    return ap.parse_args(argv)


ARGS = parse_args([]) if __name__ != "__main__" else parse_args()


def make_backend():
    if ARGS.demo:
        from backends.mock import MockBackend
        return MockBackend(log)
    from backends.wpp import WPPBackend
    return WPPBackend(DATA_DIR, log)


if __name__ == "__main__":
    backend = make_backend()
    url = f"http://127.0.0.1:{ARGS.port}"
    print(f"\n  WhatsApp Photo Saver running at {url}\n  Press Ctrl+C to stop.\n")
    if not ARGS.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=ARGS.port, debug=False, threaded=True)
