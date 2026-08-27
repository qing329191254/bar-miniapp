from __future__ import annotations

import json
import os
import uuid

import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

SESSION_TTL = 7 * 24 * 3600


def ping() -> bool:
    try:
        return r.ping()
    except Exception:
        return False


def session_create(user_id: int) -> str:
    token = uuid.uuid4().hex
    r.setex(f"sess:{token}", SESSION_TTL, str(user_id))
    return token


def session_get(token: str) -> int | None:
    if not token:
        return None
    uid = r.get(f"sess:{token}")
    return int(uid) if uid else None


def lock_pending(kind: str, uid: int, ttl: int) -> bool:
    return bool(r.set(f"lock:{kind}:{uid}", "1", nx=True, ex=max(ttl, 5)))


def unlock_pending(kind: str, uid: int) -> None:
    r.delete(f"lock:{kind}:{uid}")


def verify_put(code: str, payload: dict, ttl: int) -> None:
    r.setex(f"verify:{code}", max(ttl, 5), json.dumps(payload, ensure_ascii=False))


def verify_get(code: str) -> dict | None:
    raw = r.get(f"verify:{code}")
    if not raw:
        return None
    return json.loads(raw)


def verify_delete(code: str) -> None:
    r.delete(f"verify:{code}")


def verify_find(code: str) -> tuple[str, dict] | tuple[None, None]:
    payload = verify_get(code)
    if payload:
        return code, payload
    for key in r.scan_iter("verify:*"):
        full = key.split(":", 1)[-1]
        if full.endswith(code):
            found = verify_get(full)
            if found:
                return full, found
    return None, None


def live_verify_card_ids() -> set[int]:
    ids: set[int] = set()
    for key in r.scan_iter("verify:*"):
        payload = verify_get(key.split(":", 1)[-1])
        if payload:
            ids.update(int(x) for x in (payload.get("cardIds") or []))
    return ids


def idem_begin(key: str, ttl: int = 60) -> bool:
    return bool(r.set(f"idem:{key}", "1", nx=True, ex=ttl))
