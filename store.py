"""Tiny JSON store: what has been downloaded + running counters."""
import json, threading, time
from pathlib import Path


class Store:
    def __init__(self, directory):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file = self.dir / "state.json"
        self.lock = threading.RLock()
        self.data = {"stats": {"saved": 0, "skipped": 0, "failed": 0}, "files": {}}
        if self.file.exists():
            try:
                self.data = json.loads(self.file.read_text(encoding="utf-8"))
            except Exception:
                pass

    def _save(self):
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data), encoding="utf-8")
        tmp.replace(self.file)

    def has(self, key):
        with self.lock:
            f = self.data["files"].get(key)
            return bool(f and Path(f["path"]).exists())

    def add(self, key, path, meta):
        with self.lock:
            self.data["files"][key] = {"path": str(path), "saved_at": time.time(), **meta}
            self.data["stats"]["saved"] += 1
            self._save()

    def bump(self, name, n=1):
        with self.lock:
            self.data["stats"][name] += n
            self._save()

    def stats(self):
        with self.lock:
            return dict(self.data["stats"])

    def recent(self, n=50):
        with self.lock:
            items = sorted(self.data["files"].items(), key=lambda kv: kv[1]["saved_at"], reverse=True)
            return [{"id": k, **v} for k, v in items[:n] if Path(v["path"]).exists()]

    def path_for(self, key):
        with self.lock:
            f = self.data["files"].get(key)
            return Path(f["path"]) if f else None

    def reset_stats(self):
        with self.lock:
            self.data["stats"] = {"saved": 0, "skipped": 0, "failed": 0}
            self._save()
