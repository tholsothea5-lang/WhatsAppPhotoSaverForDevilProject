# WhatsApp Photo Saver

A small Python web tool that runs **on your own computer** (localhost). Link your WhatsApp by QR code,
tick the chats you want, pick a date range, and it saves the photos into a folder.

Photos are saved as `<folder>/<chat name>/<dd-mm-yyyy>/<caption>/<sender>_<date>_<time>_<id>.jpg`.
Photos sent without a caption go into a `No caption` folder, and every photo in an album goes into one folder named after the album's caption.

## Run it (Windows)
1. Install **Python 3.10+** from python.org (tick "Add Python to PATH") and **Git**.
2. ```
   git clone https://github.com/tholsothea5-lang/WhatsAppPhotoSaverForDevilProject.git
   cd WhatsAppPhotoSaverForDevilProject
   ```
3. Double-click **run.bat** (first run installs everything, ~2 min). Your browser opens at http://127.0.0.1:5000.

## Run it (Mac / Linux)
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
- Only messages WhatsApp Web can load are available; very old media may have expired from WhatsApp's servers (counted as "failed").
- The server only listens on 127.0.0.1, so it isn't reachable from other computers.
