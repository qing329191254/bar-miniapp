"""In-memory JSON store matching the interactive prototype seed."""
from __future__ import annotations

import copy
import json
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED_PATH = ROOT / "seed.json"
DATA_PATH = ROOT / "data.json"

_lock = threading.RLock()
DB: dict = {}

TODAY = "2026-08-25"
MIN_MS = 60 * 1000


def _ikey(d: dict | None) -> dict:
    if not d:
        return {}
    out = {}
    for k, v in d.items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            out[k] = v
    return out


def normalize(db: dict) -> dict:
    for key in ("coin", "point", "shard", "signStreak", "staff"):
        db[key] = _ikey(db.get(key) or {})
    seq = db.get("seq") or {}
    seq.setdefault("card", 200)
    seq.setdefault("code", 200)
    seq.setdefault("rec", 200)
    seq.setdefault("champ", 200)
    seq.setdefault("wdr", 200)
    seq.setdefault("deact", 200)
    db["seq"] = seq
    now = int(time.time() * 1000)
    for r in db.get("recharges") or []:
        if r.get("status") == "PENDING_PAY":
            r["expireAt"] = now + 30 * MIN_MS
    for w in db.get("withdrawals") or []:
        if w.get("status") == "PENDING_CONFIRM":
            w["expireAt"] = now + 30 * MIN_MS
    return db


def load() -> dict:
    global DB
    src = DATA_PATH if DATA_PATH.exists() else SEED_PATH
    raw = json.loads(src.read_text(encoding="utf-8"))
    DB = normalize(raw)
    return DB


def save() -> None:
    DATA_PATH.write_text(json.dumps(DB, ensure_ascii=False, default=str), encoding="utf-8")


def reset() -> dict:
    global DB
    if DATA_PATH.exists():
        DATA_PATH.unlink()
    DB = normalize(json.loads(SEED_PATH.read_text(encoding="utf-8")))
    save()
    return DB


def locked():
    return _lock


def snapshot() -> dict:
    with _lock:
        return copy.deepcopy(DB)


load()
