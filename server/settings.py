from __future__ import annotations

import os
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv

if not os.getenv("CBR_ENV_ID"):
    load_dotenv()

LOCAL_MYSQL = "mysql+pymysql://wanka:wanka@127.0.0.1:3308/wanka"
LOCAL_REDIS = "redis://127.0.0.1:6379/0"


def in_cloud() -> bool:
    return bool(os.getenv("CBR_ENV_ID"))


def mysql_url() -> str:
    addr = (os.getenv("MYSQL_ADDRESS") or "").strip()
    user = os.getenv("MYSQL_USERNAME")
    if addr and user:
        password = os.getenv("MYSQL_PASSWORD") or ""
        db = os.getenv("MYSQL_DATABASE") or os.getenv("MYSQL_DB") or "wanka"
        return (
            f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
            f"@{addr}/{db}?charset=utf8mb4"
        )
    url = (os.getenv("MYSQL_URL") or "").strip()
    if url and not (in_cloud() and is_loopback(url)):
        return url
    return LOCAL_MYSQL


def redis_url() -> str:
    if os.getenv("REDIS_URL"):
        return os.environ["REDIS_URL"]
    raw = (os.getenv("REDIS_ADDRESS") or os.getenv("REDIS_HOST") or "").strip()
    if raw:
        password = os.getenv("REDIS_PASSWORD") or ""
        if "://" in raw:
            return raw
        if ":" not in raw.rsplit("@", 1)[-1]:
            raw = f"{raw}:{os.getenv('REDIS_PORT') or '6379'}"
        if password:
            return f"redis://:{quote_plus(password)}@{raw}/0"
        return f"redis://{raw}/0"
    return LOCAL_REDIS


def is_loopback(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        host = ""
    return host in ("127.0.0.1", "localhost", "::1")


def host_for_log(url: str) -> str:
    try:
        p = urlparse(url)
        return f"{p.hostname}:{p.port or ''}/{p.path.lstrip('/')}"
    except Exception:
        return "(unparsed)"
