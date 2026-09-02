"""Smoke test for staff reminder / push config (API + WebSocket)."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

try:
    import websocket
except ImportError:
    websocket = None

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8010").rstrip("/")
PWD = os.environ.get("DEMO_PWD", "123456")
PASS: list[str] = []
FAIL: list[tuple[str, str]] = []


def req(method: str, path: str, token: str | None = None, body: dict | None = None):
    url = f"{BASE}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=45) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return e.code, payload


def ok(name: str, cond: bool, detail: str = ""):
    if cond:
        PASS.append(name)
        print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL.append((name, detail))
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def login(account: str) -> str:
    code, data = req("POST", "/api/auth/login", body={"account": account, "password": PWD})
    if code != 200 or not data or not data.get("token"):
        raise RuntimeError(f"login {account} failed: {code} {data}")
    return data["token"]


def customer_token_local() -> str:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import cache
    from database import SessionLocal
    from models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=1).first()
        if not user:
            raise RuntimeError("seed customer uid=1 missing")
        return cache.session_create(user.id)
    finally:
        db.close()


def bucket_ids(summary: dict, key: str) -> set[int]:
    bucket = summary.get(key) or {}
    return set(bucket.get("ids") or [])


def reminder_keys(cfg: dict) -> list[str]:
    return [
        "enabled", "order", "pay", "recharge", "withdrawal",
        "pcVoice", "miniVoice", "miniVibrate", "miniBadge",
        "repeatEnabled", "repeatSeconds", "repeatTimes",
    ]


def test_push_config(m_tok: str):
    print("\n=== Push config (admin) ===")
    code, cur = admin_get(m_tok, "/api/admin/push")
    ok("GET /api/admin/push", code == 200 and isinstance(cur, dict), f"status={code}")
    if not isinstance(cur, dict):
        return
    missing = [k for k in reminder_keys(cur) if k not in cur]
    ok("push config has reminder fields", not missing, f"missing={missing}")

    patch = {**cur, "repeatTimes": int(cur.get("repeatTimes") or 5)}
    code, _ = req("PUT", "/api/admin/push", token=m_tok, body={"data": patch})
    ok("PUT /api/admin/push", code == 200, f"status={code}")
    code, again = admin_get(m_tok, "/api/admin/push")
    ok("push config persisted", code == 200 and again.get("repeatTimes") == patch["repeatTimes"])


def admin_get(token: str, path: str):
    return req("GET", path, token=token)


def test_todo_summary(s_tok: str, m_tok: str):
    print("\n=== Todo summary & /me push ===")
    code, me = req("GET", "/api/me", token=s_tok)
    ok("staff /api/me includes push", code == 200 and isinstance(me.get("push"), dict))

    code, summary = req("GET", "/api/staff/todo-summary", token=s_tok)
    ok("GET todo-summary", code == 200 and isinstance(summary, dict))
    if not isinstance(summary, dict):
        return summary
    for key in ("accept", "payOrder", "recharge", "withdrawal", "total", "reminder"):
        ok(f"todo-summary has {key}", key in summary)
    rem = summary.get("reminder") or {}
    missing = [k for k in reminder_keys(rem) if k not in rem]
    ok("todo-summary.reminder fields", not missing, f"missing={missing}")
    return summary


def test_create_triggers(c_tok: str, s_tok: str):
    print("\n=== Create triggers (order / recharge / withdrawal) ===")
    code, summary0 = req("GET", "/api/staff/todo-summary", token=s_tok)
    if code != 200:
        ok("baseline todo-summary", False, f"status={code}")
        return
    accept0 = bucket_ids(summary0, "accept")
    rech0 = bucket_ids(summary0, "recharge")
    wdr0 = bucket_ids(summary0, "withdrawal")

    code, catalog = req("GET", "/api/products", token=c_tok)
    products = (catalog or {}).get("products") or []
    if products:
        code, order = req(
            "POST",
            "/api/orders",
            token=c_tok,
            body={"items": [{"pid": products[0]["id"], "qty": 1, "specIds": []}], "payType": "COIN", "remark": "push-test"},
        )
        ok("create order", code == 200 and order.get("id"), f"status={code}")
        if code == 200 and order.get("id"):
            code, s1 = req("GET", "/api/staff/todo-summary", token=s_tok)
            accept1 = bucket_ids(s1 or {}, "accept")
            ok(
                "order visible immediately after publish",
                order["id"] in accept1 and len(accept1) >= len(accept0),
                f"accept ids={sorted(accept1)}",
            )
            req("POST", f"/api/staff/orders/{order['id']}/reject", token=s_tok, body={"reason": "push-test cleanup"})
    else:
        ok("create order", False, "no products")

    code, rech_info = req("GET", "/api/recharges", token=c_tok)
    pending = (rech_info or {}).get("pending")
    if pending:
        req("POST", f"/api/recharges/{pending['id']}/cancel", token=c_tok)
    tiers = (rech_info or {}).get("tiers") or []
    if tiers:
        code, rech = req("POST", "/api/recharges", token=c_tok, body={"tierId": tiers[0]["id"]})
        ok("create recharge", code == 200 and rech.get("id"), f"status={code}")
        if code == 200 and rech.get("id"):
            code, s2 = req("GET", "/api/staff/todo-summary", token=s_tok)
            rech1 = bucket_ids(s2 or {}, "recharge")
            ok(
                "recharge visible immediately after publish",
                rech["id"] in rech1,
                f"recharge ids={sorted(rech1)}",
            )
            req("POST", f"/api/staff/recharges/{rech['id']}/reject", token=s_tok, body={"reason": "push-test cleanup"})
    else:
        ok("create recharge", False, "no tiers")

    code, pts = req("GET", "/api/points", token=c_tok)
    av = int((pts or {}).get("point", {}).get("av") or 0)
    if av >= 10:
        pending_w = (pts or {}).get("pending")
        if pending_w:
            req("POST", "/api/withdrawals/cancel", token=c_tok)
        code, wdr = req("POST", "/api/withdrawals", token=c_tok, body={"pts": 10})
        ok("create withdrawal", code == 200 and wdr.get("id"), f"status={code}")
        if code == 200 and wdr.get("id"):
            code, s3 = req("GET", "/api/staff/todo-summary", token=s_tok)
            wdr1 = bucket_ids(s3 or {}, "withdrawal")
            ok(
                "withdrawal visible immediately after publish",
                wdr["id"] in wdr1,
                f"withdrawal ids={sorted(wdr1)}",
            )
            req("POST", f"/api/staff/withdrawals/{wdr['id']}/reject", token=s_tok, body={"reason": "push-test cleanup"})
    else:
        ok("create withdrawal", False, f"insufficient points av={av}")


def test_websocket(s_tok: str):
    print("\n=== WebSocket staff-reminders ===")
    if websocket is None:
        ok("websocket client", False, "pip install websocket-client")
        return
    ws_base = BASE.replace("https://", "wss://").replace("http://", "ws://")
    url = f"{ws_base}/ws/staff-reminders?token={s_tok}"
    events: list[dict] = []
    try:
        ws = websocket.create_connection(url, timeout=10)
        hello = json.loads(ws.recv())
        ok("WS connected message", hello.get("type") == "connected", str(hello))
        ws.send("ping")
        pong = json.loads(ws.recv())
        ok("WS ping/pong", pong.get("type") == "pong", str(pong))
        ws.close()
    except Exception as e:
        ok("WS connect", False, str(e))


def main():
    local = "127.0.0.1" in BASE or "localhost" in BASE
    print(f"API base: {BASE}\n")
    try:
        s_tok = login("900001")
        m_tok = login("900002")
        ok("login staff/manager", True)
    except RuntimeError as e:
        ok("login", False, str(e))
        sys.exit(1)

    if local:
        try:
            c_tok = customer_token_local()
            ok("customer dev token", True)
        except RuntimeError as e:
            ok("customer dev token", False, str(e))
            c_tok = None
    else:
        c_tok = None
        print("  SKIP  customer flows — cloud requires WeChat login")

    test_push_config(m_tok)
    test_todo_summary(s_tok, m_tok)
    if c_tok:
        test_create_triggers(c_tok, s_tok)
    test_websocket(s_tok)

    print(f"\n=== Summary: {len(PASS)} passed, {len(FAIL)} failed ===")
    if FAIL:
        print("\nFailures:")
        for name, detail in FAIL:
            print(f"  - {name}: {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
