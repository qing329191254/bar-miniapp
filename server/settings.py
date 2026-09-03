from __future__ import annotations

import os
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv

if not os.getenv("CBR_ENV_ID"):
    load_dotenv()

LOCAL_MYSQL = "mysql+pymysql://wanka:wanka@127.0.0.1:3308/wanka"

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


def is_loopback(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        host = ""
    return host in ("127.0.0.1", "localhost", "::1")


def wx_appid() -> str:
    return (os.getenv("WX_APPID") or os.getenv("WECHAT_APPID") or "").strip()


def wx_secret() -> str:
    return (os.getenv("WX_SECRET") or os.getenv("WECHAT_SECRET") or "").strip()


def cloud_env_id() -> str:
    return (
        os.getenv("CBR_ENV_ID")
        or os.getenv("TCB_ENV_ID")
        or os.getenv("CLOUD_ENV_ID")
        or "prod-d2gc6jcwy846bd613"
    ).strip()


def cos_public_base() -> str:
    return (
        os.getenv("COS_PUBLIC_BASE")
        or "https://7072-prod-d2gc6jcwy846bd613-1476141553.tcb.qcloud.la"
    ).strip().rstrip("/")


def sms_secret_id() -> str:
    return (os.getenv("SMS_SECRET_ID") or "").strip()


def sms_secret_key() -> str:
    return (os.getenv("SMS_SECRET_KEY") or "").strip()


def sms_sdk_app_id() -> str:
    return (os.getenv("SMS_SDK_APP_ID") or "").strip()


def sms_sign_name() -> str:
    return (os.getenv("SMS_SIGN_NAME") or "").strip()


def sms_template_id() -> str:
    return (os.getenv("SMS_TEMPLATE_ID") or "").strip()


def sms_region() -> str:
    return (os.getenv("SMS_REGION") or "ap-guangzhou").strip() or "ap-guangzhou"


def sms_template_param_count() -> int:
    try:
        n = int(os.getenv("SMS_TEMPLATE_PARAM_COUNT") or "2")
    except ValueError:
        n = 2
    return 1 if n <= 1 else 2


def sms_configured() -> bool:
    return bool(
        sms_secret_id()
        and sms_secret_key()
        and sms_sdk_app_id()
        and sms_sign_name()
        and sms_template_id()
    )


def session_secret() -> str:
    value = (
        os.getenv("SESSION_SECRET")
        or os.getenv("WX_SECRET")
        or os.getenv("WECHAT_SECRET")
        or os.getenv("MYSQL_PASSWORD")
        or ""
    ).strip()
    if value:
        return value
    if in_cloud():
        raise RuntimeError("SESSION_SECRET 未配置")
    return "wanka-local-development-session-secret"


def host_for_log(url: str) -> str:
    try:
        p = urlparse(url)
        return f"{p.hostname}:{p.port or ''}/{p.path.lstrip('/')}"
    except Exception:
        return "(unparsed)"
