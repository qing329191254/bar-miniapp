"""Verify WS publishes order.created when order is created."""
from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request

import websocket

BASE = "http://127.0.0.1:8012"
WS = "ws://127.0.0.1:8012"


def login(account: str) -> str:
    body = json.dumps({"account": account, "password": "123456"}).encode()
    r = urllib.request.Request(
        f"{BASE}/api/auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(r).read())["token"]


def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())


def customer_token() -> str:
    sys.path.insert(0, __file__.rsplit("scripts", 1)[0])
    import cache
    from database import SessionLocal
    from models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=1).first()
        return cache.session_create(user.id)
    finally:
        db.close()


def main() -> None:
    s_tok = login("900001")
    c_tok = customer_token()
    events: list[dict] = []

    def on_message(_ws, message: str):
        payload = json.loads(message)
        events.append(payload)
        if payload.get("type") != "connected":
            _ws.close()

    ws = websocket.WebSocketApp(
        f"{WS}/ws/staff-reminders?token={s_tok}",
        on_message=on_message,
    )
    threading.Thread(target=ws.run_forever, daemon=True).start()
    time.sleep(1.2)

    products = api("GET", "/api/products", c_tok)["products"]
    order = api(
        "POST",
        "/api/orders",
        c_tok,
        {
            "items": [{"pid": products[0]["id"], "qty": 1, "specIds": []}],
            "payType": "COIN",
            "remark": "ws-event-test",
        },
    )
    time.sleep(3)
    oid = order["id"]
    ok = any(e.get("event") == "order.created" and e.get("id") == oid for e in events)
    print("order.created WS event:", ok, events)
    api("POST", f"/api/staff/orders/{oid}/reject", s_tok, {"reason": "ws-event-test cleanup"})
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
