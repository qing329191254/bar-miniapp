from __future__ import annotations

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
_local_locks: dict[str, float] = {}


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
    key = f"lock:{kind}:{uid}"
    ttl = max(ttl, 5)
    try:
        return bool(r.set(key, "1", nx=True, ex=ttl))
    except Exception:
        now = time.time()
        if _local_locks.get(key, 0) > now:
            return False
        _local_locks[key] = now + ttl
        return True


def unlock_pending(kind: str, uid: int) -> None:
    key = f"lock:{kind}:{uid}"
    _local_locks.pop(key, None)
    try:
        r.delete(key)
    except Exception:
        pass


def idem_begin(key: str, ttl: int = 60) -> bool:
    return bool(r.set(f"idem:{key}", "1", nx=True, ex=ttl))
