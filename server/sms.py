"""Tencent Cloud SMS. Keys stay in env; local runs can mock when unset."""
from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import time
import urllib.request
from datetime import timezone

from settings import (
    in_cloud,
    sms_configured,
    sms_region,
    sms_sdk_app_id,
    sms_secret_id,
    sms_secret_key,
    sms_sign_name,
    sms_template_id,
    sms_template_param_count,
)

HOST = "sms.tencentcloudapi.com"
SERVICE = "sms"
ACTION = "SendSms"
VERSION = "2021-01-11"


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def send_code(phone: str, code: str) -> dict:
    """Send a verification SMS. Returns {mock: bool}."""
    if not sms_configured():
        if in_cloud():
            raise ValueError("短信服务未配置，请联系管理员")
        print(f"[sms mock] {phone} -> {code}")
        return {"mock": True}

    minutes = "5"
    params = [code] if sms_template_param_count() <= 1 else [code, minutes]
    payload = {
        "PhoneNumberSet": [f"+86{phone}"],
        "SmsSdkAppId": sms_sdk_app_id(),
        "SignName": sms_sign_name(),
        "TemplateId": sms_template_id(),
        "TemplateParamSet": params,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    timestamp = int(time.time())
    date = datetime.datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")
    hashed_payload = hashlib.sha256(body.encode("utf-8")).hexdigest()
    ct = "application/json; charset=utf-8"
    canonical_headers = f"content-type:{ct}\nhost:{HOST}\nx-tc-action:{ACTION.lower()}\n"
    signed_headers = "content-type;host;x-tc-action"
    canonical_request = (
        f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{hashed_payload}"
    )
    credential_scope = f"{date}/{SERVICE}/tc3_request"
    string_to_sign = (
        "TC3-HMAC-SHA256\n"
        f"{timestamp}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )
    secret_date = _sign(("TC3" + sms_secret_key()).encode("utf-8"), date)
    secret_service = _sign(secret_date, SERVICE)
    secret_signing = _sign(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"TC3-HMAC-SHA256 Credential={sms_secret_id()}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    req = urllib.request.Request(
        f"https://{HOST}",
        data=body.encode("utf-8"),
        headers={
            "Authorization": authorization,
            "Content-Type": ct,
            "Host": HOST,
            "X-TC-Action": ACTION,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": VERSION,
            "X-TC-Region": sms_region(),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ValueError("短信服务暂时不可用") from e

    result = (data.get("Response") or {})
    err = result.get("Error") or {}
    if err:
        raise ValueError(err.get("Message") or "短信发送失败")
    statuses = result.get("SendStatusSet") or []
    if statuses:
        first = statuses[0] or {}
        if str(first.get("Code") or "") not in ("Ok", "ok", ""):
            raise ValueError(first.get("Message") or "短信发送失败")
    return {"mock": False}
