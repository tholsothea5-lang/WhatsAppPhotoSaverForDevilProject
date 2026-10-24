# WhatsApp Photo Saver

Save WhatsApp Web photos into folders named after the chat, the date, and the sender's caption.

There are two ways to use it:

- **Bookmarklet** — nothing to install, no server, no password. Runs inside the WhatsApp Web tab you already have open.
- **Local Python app** — runs on your own computer (localhost), links by QR code, writes straight to a folder.

Both save photos as `<chat name>/<dd-mm-yyyy>/<caption>/<sender>_<date>_<time>_<id>.jpg`.
Photos sent without a caption go into a `No caption` folder, and every photo in an album goes into one folder named after the album's caption.

## Browser (paste into DevTools) — no install

Open **https://tholsothea5-lang.github.io/WhatsAppPhotoSaverForDevilProject/**, copy the script, then:

1. Open [web.whatsapp.com](https://web.whatsapp.com) and wait for your chats to load.
2. Press **Ctrl+Shift+J** (Windows/Linux) or **⌥⌘J** (Mac) to open DevTools → **Console**.
3. If Chrome asks, type `allow pasting` and press **Enter**.
4. Paste the script and press **Enter**. A panel appears in the corner of WhatsApp Web — pick a chat and date range, **Scan**, then **Download ZIP**.

How it works: the script runs inside the WhatsApp Web tab (the same context that has access to WhatsApp's local IndexedDB), reads WhatsApp's live message models for captions, decrypts each photo in memory with WebCrypto, and builds a STORE-only ZIP locally. Nothing is uploaded. If you reload WhatsApp Web you'll need to run it again; for repeat use save it as a **DevTools Snippet**.

**Why DevTools, not a bookmarklet?** WhatsApp Web uses a strict Content Security Policy that blocks `javascript:` bookmarklets in Chrome/Edge. Running the code in the browser's built-in DevTools console is exempt from that policy and requires nothing to install. The script is served from this repo's [`docs/`](docs/) folder on `main` ([`docs/wps-script.js`](docs/wps-script.js)).

## Local app (Windows)
1. Install **Python 3.10+** from python.org (tick "Add Python to PATH") and **Git**.
2. ```
   git clone https://github.com/tholsothea5-lang/WhatsAppPhotoSaverForDevilProject.git
   cd WhatsAppPhotoSaverForDevilProject
   ```
3. Double-click **run.bat** (first run installs everything, ~2 min). Your browser opens at http://127.0.0.1:5000.

## Local app (Mac / Linux)
```
git clone https://github.com/tholsothea5-lang/WhatsAppPhotoSaverForDevilProject.git
cd WhatsAppPhotoSaverForDevilProject
./run.sh
```

## Using it
1. A Chromium window opens WhatsApp Web in the background; leave it open (minimise is fine). The tool page shows the QR code. Scan it in WhatsApp -> Linked devices -> Link a device.
2. Tick chats, set Start/End, optionally filter by sender, choose the download folder, press **Download range**.
3. "Skip already-downloaded files" means re-running the same range won't save duplicates.
4. Each person links **their own** WhatsApp. The session is remembered in `~/.whatsapp_photo_saver`, so you only scan once.

## Try the UI without WhatsApp
`python app.py --demo` (or `run.bat --demo`) uses fake chats and generated photos.

## Notes / limits
- It automates WhatsApp Web with [WA-JS](https://github.com/wppconnect-team/wa-js). WhatsApp does not offer an official API for this, and automating it is outside WhatsApp's terms of service, so use it only with your own account and at your own risk. WhatsApp Web updates can break it until WA-JS is updated.
- The bookmarklet automates your own WhatsApp Web session in the same way. It never sees your password and never creates a linked device, but the terms-of-service and update risk are the same.
- Only messages WhatsApp Web can load are available; very old media may have expired from WhatsApp's servers (counted as "failed").
- The server only listens on 127.0.0.1, so it isn't reachable from other computers.
