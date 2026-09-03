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


_sms_codes: dict[str, dict] = {}
SMS_TTL = 300
SMS_COOLDOWN = 60
SMS_DAY_LIMIT = 8
SMS_MAX_TRIES = 5


def sms_send_guard(phone: str) -> str | None:
    """Return an error message if this number cannot receive a new code yet."""
    now = time.time()
    rec = _sms_codes.get(phone)
    if not rec:
        return None
    if rec.get("sent_at", 0) + SMS_COOLDOWN > now:
        wait = int(rec["sent_at"] + SMS_COOLDOWN - now)
        return f"请 {max(wait, 1)} 秒后再获取验证码"
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    if rec.get("day") == day and int(rec.get("day_count") or 0) >= SMS_DAY_LIMIT:
        return "该手机号今日获取次数已达上限"
    return None


def sms_store(phone: str, code: str) -> None:
    now = time.time()
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    rec = _sms_codes.get(phone) or {}
    day_count = int(rec.get("day_count") or 0) + 1 if rec.get("day") == day else 1
    _sms_codes[phone] = {
        "code": code,
        "exp": now + SMS_TTL,
        "tries": 0,
        "sent_at": now,
        "day": day,
        "day_count": day_count,
    }


def sms_verify(phone: str, code: str) -> bool:
    rec = _sms_codes.get(phone)
    if not rec:
        return False
    if rec.get("exp", 0) <= time.time():
        _sms_codes.pop(phone, None)
        return False
    rec["tries"] = int(rec.get("tries") or 0) + 1
    if rec["tries"] > SMS_MAX_TRIES:
        _sms_codes.pop(phone, None)
        return False
    if not hmac.compare_digest(str(rec.get("code") or ""), str(code or "").strip()):
        return False
    _sms_codes.pop(phone, None)
    return True


def idem_begin(key: str, ttl: int = 60) -> bool:
    store_key = f"idem:{key}"
    ttl = max(ttl, 1)
    _drop_expired(_idem_keys)
    now = time.time()
    if _idem_keys.get(store_key, 0) > now:
        return False
    _idem_keys[store_key] = now + ttl
    return True
