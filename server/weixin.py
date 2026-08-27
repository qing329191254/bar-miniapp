"""WeChat mini program login. AppSecret stays on the server."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from settings import wx_appid, wx_secret

WX_ERR = {
    40013: "AppID 无效",
    40029: "微信登录码无效，请重试",
    40125: "AppSecret 配置不正确",
    40163: "微信登录码已使用，请重试",
}


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
    url = "https://api.weixin.qq.com/sns/jscode2session?" + qs
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ValueError("微信登录服务暂时不可用") from e
    errcode = int(data.get("errcode") or 0)
    if errcode:
        raise ValueError(WX_ERR.get(errcode) or data.get("errmsg") or "微信登录失败")
    openid = data.get("openid")
    if not openid:
        raise ValueError("微信登录失败")
    return openid
