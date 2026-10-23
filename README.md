# WhatsApp Photo Saver

Save WhatsApp Web photos into folders named after the chat, the date, and the sender's caption.

There are two ways to use it:

- **Bookmarklet** — nothing to install, no server, no password. Runs inside the WhatsApp Web tab you already have open.
- **Local Python app** — runs on your own computer (localhost), links by QR code, writes straight to a folder.

Both save photos as `<chat name>/<dd-mm-yyyy>/<caption>/<sender>_<date>_<time>_<id>.jpg`.
Photos sent without a caption go into a `No caption` folder, and every photo in an album goes into one folder named after the album's caption.

## Bookmarklet (no install)

Open **https://tholsothea5-lang.github.io/WhatsAppPhotoSaverForDevilProject/** and drag the green
**WhatsApp Photo Saver** button to your bookmarks bar. Then open
[web.whatsapp.com](https://web.whatsapp.com), sign in if WhatsApp asks, and click the bookmark.

1. Pick a chat and a date range in the panel.
2. Press **Scan**, then **Download ZIP**.
3. Your browser saves `WhatsApp Photos - <chat> - <from> to <to>.zip`.

How it works: the bookmarklet reads WhatsApp's own IndexedDB, decrypts each photo in memory with WebCrypto,
and builds the ZIP locally. Captions come from WhatsApp's live message models (albums share one caption);
if a future update hides them, files fall back to `No caption`. Nothing is uploaded and no account is created.

Limits: only media this device has cached and that has not expired on WhatsApp's servers can be downloaded
(the panel lists failures). The ZIP is built in memory, so export a few hundred photos at a time. Desktop
Chrome, Edge, and Brave work best — Firefox users should paste the copied code into a bookmark's URL field.

The site is served from this repo's [`docs/`](docs/) folder on `main`; the bookmarklet itself is
[`docs/wps-bookmarklet.js`](docs/wps-bookmarklet.js).

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
