"""Demo backend: fake QR link, fake chats, generated photos. Run with: python app.py --demo"""
import hashlib, io, time
from PIL import Image, ImageDraw
from . import qr_data_url

CHATS = [
    "Project Alpha - Survey + Build", "Project Beta - Station Upgrade", "Project Gamma - Depot Works",
    "Project Delta - Panel Build", "Project Epsilon - Station Fitout", "Project Zeta - Controls Upgrade",
    "Project Eta - Network Migration", "Project Theta - Tunnel Link", "Project Iota - Street Works",
    "Project Kappa - Station IBC", "Project Lambda - Tunnel A&B End",
]
SENDERS = ["Alex", "Sam", "Jordan", "Riley"]
CAPTIONS = [
    "Cable tray installed",
    "MRS moved to right hand side",
    "SPLT06 installation",
    "Termination check before power up",
    "",
    "Duct entry sealed",
]


class MockBackend:
    def __init__(self, log):
        self.log = log
        self.t0 = time.time()
        self.linked_after = 7

    def status(self):
        el = time.time() - self.t0
        if el < 2:
            return {"state": "starting"}
        if el < self.linked_after:
            return {"state": "qr", "qr": qr_data_url(f"demo-whatsapp-link-{int(el // 2)}")}
        return {"state": "ready", "me": {"name": "Demo User", "pic": None}}

    def list_chats(self):
        return [{"id": f"chat{i}@g.us", "name": n} for i, n in enumerate(CHATS)]

    def list_photos(self, chat_id, start_ms, end_ms):
        seed = int(hashlib.md5(chat_id.encode()).hexdigest()[:6], 16)
        out, step = [], 6 * 3600
        t = int(end_ms / 1000) - (seed % 5) * 3600
        n = album_no = 0

        def add(ts, caption, album):
            sender = SENDERS[(seed + n) % len(SENDERS)]
            out.append({"id": f"{chat_id}-{ts}-{len(out)}", "ts": ts, "sender": sender,
                        "ext": "jpg", "caption": caption, "album": album})

        while t * 1000 >= start_ms and n < 12:
            # Every few photos arrive as an album: one caption shared by 2-3 photos.
            if n % 5 == 1:
                album_no += 1
                album = f"{chat_id}-album{album_no}"
                size = 2 + (seed + n) % 2
                caption = CAPTIONS[(seed + n) % len(CAPTIONS)] or CAPTIONS[0]
                for k in range(size):
                    if n >= 12 or t * 1000 < start_ms:
                        break
                    add(t, caption, album)
                    n += 1
                    t -= 45 + k * 11
                t -= step
            else:
                add(t, CAPTIONS[(seed + n) % len(CAPTIONS)], "")
                n += 1
                t -= step + (seed % 7) * 600
        return out

    def fetch_photo(self, chat_id, meta):
        h = int(hashlib.md5(meta["id"].encode()).hexdigest()[:6], 16)
        img = Image.new("RGB", (640, 480), ((h >> 16) & 255, (h >> 8) & 255, h & 255))
        d = ImageDraw.Draw(img)
        d.text((20, 20), f"{meta['sender']}\n{time.strftime('%d-%m-%Y %H:%M', time.localtime(meta['ts']))}\n(demo photo)", fill="white")
        buf = io.BytesIO()
        img.save(buf, "JPEG")
        return buf.getvalue()

    def logout(self):
        self.t0 = time.time()

    def shutdown(self):
        pass
