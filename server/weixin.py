"""WeChat mini program login. AppSecret stays on the server."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from cache import r
from settings import wx_appid, wx_secret

WX_ERR = {
    40013: "AppID 无效",
    40029: "微信登录码无效，请重试",
    40125: "AppSecret 配置不正确",
    40163: "微信登录码已使用，请重试",
    40001: "微信 access_token 无效，请重试",
    47001: "手机号授权码格式错误",
}


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
    cached = r.get("wx:access_token")
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
    r.setex("wx:access_token", ttl, token)
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
        r.delete("wx:access_token")
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
