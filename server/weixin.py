"""WeChat mini program login. AppSecret stays on the server."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import requests

from settings import wx_appid, wx_secret

WX_ERR = {
    40013: "AppID 无效",
    40029: "微信登录码无效，请重试",
    40125: "AppSecret 配置不正确",
    40163: "微信登录码已使用，请重试",
    40001: "微信 access_token 无效，请重试",
    47001: "手机号授权码格式错误",
}

_memory_access_token = ""
_memory_access_token_expires = 0


def _cached_access_token() -> str:
    if _memory_access_token and _memory_access_token_expires > time.time():
        return _memory_access_token
    return ""


def _save_access_token(token: str, ttl: int) -> None:
    global _memory_access_token, _memory_access_token_expires
    _memory_access_token = token
    _memory_access_token_expires = time.time() + ttl


def _clear_access_token() -> None:
    global _memory_access_token, _memory_access_token_expires
    _memory_access_token = ""
    _memory_access_token_expires = 0


def _wx_json(url: str, payload: dict | None = None, timeout: int = 8) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ValueError("微信服务暂时不可用") from e


def access_token() -> str:
    cached = _cached_access_token()
    if cached:
        return cached
    appid = wx_appid()
    secret = wx_secret()
    if not appid or not secret:
        raise ValueError("未配置微信登录，请在服务端填写 WX_APPID / WX_SECRET")
    qs = urllib.parse.urlencode({
        "grant_type": "client_credential",
        "appid": appid,
        "secret": secret,
    })
    data = _wx_json("https://api.weixin.qq.com/cgi-bin/token?" + qs)
    errcode = int(data.get("errcode") or 0)
    if errcode:
        raise ValueError(WX_ERR.get(errcode) or data.get("errmsg") or "微信 access_token 获取失败")
    token = data.get("access_token")
    if not token:
        raise ValueError("微信 access_token 获取失败")
    ttl = max(int(data.get("expires_in") or 7200) - 120, 60)
    _save_access_token(token, ttl)
    return token


def code2openid(code: str) -> str:
    appid = wx_appid()
    secret = wx_secret()
    if not appid or not secret:
        raise ValueError("未配置微信登录，请在服务端填写 WX_APPID / WX_SECRET")
    raw = (code or "").strip()
    if not raw:
        raise ValueError("缺少微信登录码")
    qs = urllib.parse.urlencode({
        "appid": appid,
        "secret": secret,
        "js_code": raw,
        "grant_type": "authorization_code",
    })
    data = _wx_json("https://api.weixin.qq.com/sns/jscode2session?" + qs)
    errcode = int(data.get("errcode") or 0)
    if errcode:
        raise ValueError(WX_ERR.get(errcode) or data.get("errmsg") or "微信登录失败")
    openid = data.get("openid")
    if not openid:
        raise ValueError("微信登录失败")
    return openid


def phone_from_code(code: str) -> str:
    raw = (code or "").strip()
    if not raw:
        raise ValueError("缺少手机号授权码")
    token = access_token()
    data = _wx_json(
        f"https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={urllib.parse.quote(token)}",
        {"code": raw},
    )
    errcode = int(data.get("errcode") or 0)
    if errcode == 40001:
        _clear_access_token()
        token = access_token()
        data = _wx_json(
            f"https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={urllib.parse.quote(token)}",
            {"code": raw},
        )
        errcode = int(data.get("errcode") or 0)
    if errcode:
        raise ValueError(WX_ERR.get(errcode) or data.get("errmsg") or "手机号授权失败")
    info = data.get("phone_info") or {}
    phone = (info.get("purePhoneNumber") or info.get("phoneNumber") or "").strip()
    if not phone:
        raise ValueError("未获取到手机号")
    return phone


def upload_cloud_file(env_id: str, cloud_path: str, raw: bytes, content_type: str) -> None:
    """Upload bytes to the object storage attached to the WeChat Cloud Hosting env."""
    if not env_id:
        raise ValueError("未获取到微信云托管环境 ID")

    def ticket() -> dict:
        token = access_token()
        return _wx_json(
            "https://api.weixin.qq.com/tcb/uploadfile?access_token="
            + urllib.parse.quote(token),
            {"env": env_id, "path": cloud_path},
        )

    data = ticket()
    errcode = int(data.get("errcode") or 0)
    if errcode == 40001:
        _clear_access_token()
        data = ticket()
        errcode = int(data.get("errcode") or 0)
    if errcode:
        raise ValueError(data.get("errmsg") or f"微信对象存储上传授权失败（{errcode}）")

    required = ("url", "token", "authorization", "cos_file_id")
    if any(not data.get(key) for key in required):
        raise ValueError("微信对象存储未返回完整上传凭证")

    # COS requires the file field to be the final multipart field.
    parts = [
        ("key", (None, cloud_path)),
        ("Signature", (None, data["authorization"])),
        ("x-cos-security-token", (None, data["token"])),
        ("x-cos-meta-fileid", (None, data["cos_file_id"])),
        ("file", (Path(cloud_path).name, raw, content_type)),
    ]
    try:
        response = requests.post(data["url"], files=parts, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError("图片上传到微信对象存储失败，请稍后重试") from exc
