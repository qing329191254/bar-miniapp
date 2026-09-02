from __future__ import annotations

import base64
import hashlib
import hmac
import time

from settings import session_secret

SESSION_TTL = 7 * 24 * 3600
_local_locks: dict[str, float] = {}
_idem_keys: dict[str, float] = {}


def _drop_expired(store: dict[str, float]) -> None:
    now = time.time()
    for key in list(store.keys()):
        if store[key] <= now:
            del store[key]


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


def session_create(user_id: int) -> str:
    return _signed_token(user_id)


def session_get(token: str) -> int | None:
    if not token:
        return None
    if token.startswith("s1."):
        return _signed_user(token)
    return None


def lock_pending(kind: str, uid: int, ttl: int) -> bool:
    key = f"lock:{kind}:{uid}"
    ttl = max(ttl, 5)
    _drop_expired(_local_locks)
    now = time.time()
    if _local_locks.get(key, 0) > now:
        return False
    _local_locks[key] = now + ttl
    return True


def unlock_pending(kind: str, uid: int) -> None:
    _local_locks.pop(f"lock:{kind}:{uid}", None)


def idem_begin(key: str, ttl: int = 60) -> bool:
    store_key = f"idem:{key}"
    ttl = max(ttl, 1)
    _drop_expired(_idem_keys)
    now = time.time()
    if _idem_keys.get(store_key, 0) > now:
        return False
    _idem_keys[store_key] = now + ttl
    return True
