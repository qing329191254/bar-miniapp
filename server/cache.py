from __future__ import annotations

import json
import base64
import hashlib
import hmac
import time
import uuid

import redis

from settings import redis_url, session_secret

REDIS_URL = redis_url()
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

SESSION_TTL = 7 * 24 * 3600


def _signed_token(user_id: int) -> str:
    payload = f"{int(user_id)}:{int(time.time()) + SESSION_TTL}".encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    sig = hmac.new(session_secret().encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"s1.{body}.{sig}"


def _signed_user(token: str) -> int | None:
    try:
        version, body, sig = token.split(".", 2)
        if version != "s1":
            return None
        expected = hmac.new(session_secret().encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        padded = body + "=" * (-len(body) % 4)
        uid, expires = base64.urlsafe_b64decode(padded).decode().split(":", 1)
        if int(expires) <= int(time.time()):
            return None
        return int(uid)
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


def ping() -> bool:
    try:
        return r.ping()
    except Exception:
        return False


def session_create(user_id: int) -> str:
    token = uuid.uuid4().hex
    try:
        r.setex(f"sess:{token}", SESSION_TTL, str(user_id))
        return token
    except Exception:
        return _signed_token(user_id)


def session_get(token: str) -> int | None:
    if not token:
        return None
    if token.startswith("s1."):
        return _signed_user(token)
    try:
        uid = r.get(f"sess:{token}")
        return int(uid) if uid else None
    except Exception:
        return None


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
