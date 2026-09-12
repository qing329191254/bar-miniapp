from __future__ import annotations

import base64
import hashlib
import hmac
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import AppLock, SmsCode
from settings import session_secret

SESSION_TTL = 7 * 24 * 3600
SMS_TTL = 300
SMS_COOLDOWN = 60
SMS_DAY_LIMIT = 8
SMS_MAX_TRIES = 5


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


def _claim_ttl_key(sess: Session, key: str, ttl: int) -> bool:
    """Insert or refresh a TTL key if missing/expired. Safe under concurrent instances."""
    ttl = max(ttl, 1)
    now = time.time()
    exp = now + ttl
    result = sess.execute(
        text(
            "INSERT INTO app_locks (lock_key, expire_at) VALUES (:key, :exp) "
            "ON DUPLICATE KEY UPDATE "
            "expire_at = IF(expire_at <= :now, VALUES(expire_at), expire_at)"
        ),
        {"key": key, "exp": exp, "now": now},
    )
    sess.flush()
    # MySQL: 1=insert, 2=update changed, 0=update no-change (still held)
    return int(result.rowcount or 0) > 0


def lock_pending(sess: Session, kind: str, uid: int, ttl: int) -> bool:
    return _claim_ttl_key(sess, f"lock:{kind}:{uid}", max(ttl, 5))


def unlock_pending(sess: Session, kind: str, uid: int) -> None:
    row = sess.get(AppLock, f"lock:{kind}:{uid}")
    if row:
        sess.delete(row)
        sess.flush()


def sms_send_guard(sess: Session, phone: str) -> str | None:
    """Return an error message if this number cannot receive a new code yet."""
    now = time.time()
    rec = sess.query(SmsCode).filter_by(phone=phone).with_for_update().first()
    if not rec:
        return None
    if float(rec.sent_at or 0) + SMS_COOLDOWN > now:
        wait = int(float(rec.sent_at or 0) + SMS_COOLDOWN - now)
        return f"请 {max(wait, 1)} 秒后再获取验证码"
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    if rec.day == day and int(rec.day_count or 0) >= SMS_DAY_LIMIT:
        return "该手机号今日获取次数已达上限"
    return None


def sms_store(sess: Session, phone: str, code: str) -> None:
    now = time.time()
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    rec = sess.query(SmsCode).filter_by(phone=phone).with_for_update().first()
    if rec:
        day_count = int(rec.day_count or 0) + 1 if rec.day == day else 1
        rec.code = code
        rec.expire_at = now + SMS_TTL
        rec.tries = 0
        rec.sent_at = now
        rec.day = day
        rec.day_count = day_count
    else:
        sess.add(SmsCode(
            phone=phone,
            code=code,
            expire_at=now + SMS_TTL,
            tries=0,
            sent_at=now,
            day=day,
            day_count=1,
        ))
    sess.flush()


def sms_verify(sess: Session, phone: str, code: str) -> bool:
    now = time.time()
    rec = sess.query(SmsCode).filter_by(phone=phone).with_for_update().first()
    if not rec:
        return False
    if float(rec.expire_at or 0) <= now:
        sess.delete(rec)
        sess.flush()
        return False
    rec.tries = int(rec.tries or 0) + 1
    if rec.tries > SMS_MAX_TRIES:
        sess.delete(rec)
        sess.flush()
        return False
    if not hmac.compare_digest(str(rec.code or ""), str(code or "").strip()):
        sess.flush()
        return False
    sess.delete(rec)
    sess.flush()
    return True


def idem_begin(sess: Session, key: str, ttl: int = 60) -> bool:
    return _claim_ttl_key(sess, f"idem:{key}", ttl)
