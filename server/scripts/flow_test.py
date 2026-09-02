"""End-to-end API flow smoke test against running backend."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8010").rstrip("/")
PWD = os.environ.get("DEMO_PWD", "123456")
PASS: list[str] = []
FAIL: list[tuple[str, str]] = []
SKIP: list[tuple[str, str]] = []
WARN: list[tuple[str, str]] = []


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


def warn(name: str, detail: str):
    WARN.append((name, detail))
    print(f"  WARN  {name} — {detail}")


def skip(name: str, reason: str):
    SKIP.append((name, reason))
    print(f"  SKIP  {name} — {reason}")


def login_account(account: str) -> tuple[str, dict]:
    code, data = req("POST", "/api/auth/login", body={"account": account, "password": PWD})
    if code != 200 or not data or not data.get("token"):
        raise RuntimeError(f"login {account} failed: {code} {data}")
    return data["token"], data["user"]


def customer_token_local() -> tuple[str, dict]:
    """Dev-only: issue session for seed customer uid=1 without WeChat."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import cache
    from database import SessionLocal
    from logic import public_user
    from models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=1).first()
        if not user:
            raise RuntimeError("seed customer uid=1 missing")
        token = cache.session_create(user.id)
        return token, public_user(db, user)
    finally:
        db.close()


def admin_get(token: str, path: str):
    return req("GET", path, token=token)


def main():
    print(f"API base: {BASE}\n")
    local = "127.0.0.1" in BASE or "localhost" in BASE

    code, accounts = req("GET", "/api/dev/accounts")
    if local:
        ok("dev/accounts", code == 200 and isinstance(accounts, dict), f"status={code}")
    else:
        ok("dev/accounts hidden on cloud", code == 404, f"status={code}")

    if local:
        code, _ = req("POST", "/api/dev/reset")
        ok("dev/reset", code == 200, f"status={code}")
    else:
        skip("dev/reset", "cloud API")

    try:
        if local:
            c_tok, c_user = customer_token_local()
        else:
            skip("C端 customer session", "cloud requires WeChat login — API paths tested via staff/admin only")
            c_tok, c_user = None, None
        s_tok, s_user = login_account("900001")
        m_tok, m_user = login_account("900002")
        b_tok, b_user = login_account("900003")
        ok("login staff/manager/boss", True, f"{s_user['nick']}/{m_user['nick']}/{b_user['nick']}")
        if c_user:
            ok("login customer (local dev token)", True, c_user.get("nick", ""))
    except RuntimeError as e:
        ok("login", False, str(e))
        sys.exit(1)

    if c_tok:
        code, home = req("GET", "/api/home", token=c_tok)
        ok("C home", code == 200 and home is not None)

        code, catalog = req("GET", "/api/products", token=c_tok)
        products = (catalog or {}).get("products") or []
        ok("C products", code == 200 and len(products) > 0, f"count={len(products)}")

        code, me = req("GET", "/api/me", token=c_tok)
        ok("C me", code == 200 and me.get("user"))

        pid = products[0]["id"]
        code, order = req(
            "POST",
            "/api/orders",
            token=c_tok,
            body={"items": [{"pid": pid, "qty": 1, "specIds": []}], "payType": "COIN", "remark": "flow-test"},
        )
        ok("C create COIN order", code == 200 and order.get("id"), f"no={order.get('no') if order else ''}")
        oid = order.get("id") if order else None

        for path in ["/api/orders", "/api/cards", "/api/points", "/api/rank", "/api/shards", "/api/recharges"]:
            code, _ = req("GET", path, token=c_tok)
            ok(f"C GET {path.split('/')[-1]}", code == 200, f"status={code}")

        code, rank_week = req("GET", "/api/rank?kind=CHAMPION&dim=WEEK&subject=USER", token=c_tok)
        code2, rank_all = req("GET", "/api/rank?kind=CHAMPION&dim=MONTH&subject=USER", token=c_tok)
        ok("C rank CHAMPION week/all", code == 200 and code2 == 200, f"week={len((rank_week or {}).get('rows') or [])} all={len((rank_all or {}).get('rows') or [])}")
    else:
        oid = rid = None

    code, todo = req("GET", "/api/staff/todo", token=s_tok)
    accept_n = len((todo or {}).get("accept") or [])
    ok("staff todo", code == 200 and todo is not None, f"accept={accept_n}")
    code, reminder = req("GET", "/api/staff/todo-summary", token=s_tok)
    ok(
        "staff realtime reminder summary",
        code == 200 and isinstance(reminder, dict) and isinstance(reminder.get("accept"), dict),
        f"status={code}",
    )

    if oid:
        code, _ = req("POST", f"/api/staff/orders/{oid}/accept", token=s_tok, body={"reason": "flow-test"})
        ok("staff accept order", code == 200, f"status={code}")
        time.sleep(0.3)
        code, _ = req("POST", f"/api/staff/orders/{oid}/finish", token=s_tok, body={"reason": "flow-test"})
        ok("staff finish order", code == 200, f"status={code}")

    if c_tok:
        code, rech_info = req("GET", "/api/recharges", token=c_tok)
        pending = (rech_info or {}).get("pending")
        if pending:
            req("POST", f"/api/recharges/{pending['id']}/cancel", token=c_tok)
        tiers = (rech_info or {}).get("tiers") or []
        if tiers:
            code, rech = req("POST", "/api/recharges", token=c_tok, body={"tierId": tiers[0]["id"]})
            ok("C create recharge", code == 200 and rech.get("id"), f"status={code}")
            rid = rech.get("id") if rech else None
        else:
            rid = None
            ok("C create recharge", False, "no tiers")
    else:
        rid = None

    if rid:
        code, _ = req("POST", f"/api/staff/recharges/{rid}/confirm", token=s_tok, body={"reason": "flow-test"})
        ok("staff confirm recharge", code == 200, f"status={code}")

    for path in ["/api/staff/projects", "/api/staff/members", "/api/staff/jobs"]:
        code, _ = req("GET", path, token=s_tok)
        ok(f"staff GET {path.split('/')[-1]}", code == 200, f"status={code}")

    code, dash = admin_get(m_tok, "/api/admin/dashboard")
    ok("admin dashboard", code == 200 and dash is not None)

    admin_paths_manager = [
        "/api/admin/orders-page?page=1&pageSize=10",
        "/api/admin/recharges-page?page=1&pageSize=10",
        "/api/admin/members?page=1&pageSize=10",
        "/api/admin/products?page=1&pageSize=10",
        "/api/admin/jobs-page?preset=7d",
        "/api/admin/reports-page?preset=7d",
        "/api/admin/withdrawals-page?page=1&pageSize=10",
        "/api/admin/gameRecords?page=1&pageSize=10",
        "/api/admin/settlement/current?page=1&pageSize=10",
        "/api/admin/settlement/preview",
        "/api/admin/settlement-config",
        "/api/admin/signin-overview?page=1&pageSize=10",
        "/api/admin/cardTpls?pageSize=0",
        "/api/admin/team-management",
        "/api/admin/push",
        "/api/admin/content",
        "/api/admin/config",
        "/api/admin/deactivation?page=1&pageSize=10",
        "/api/admin/coin-adjust?page=1&pageSize=10",
        "/api/admin/daily-biz?preset=7d",
        "/api/admin/projects?pageSize=0",
        "/api/admin/agreements",
        "/api/admin/settlement/history?page=1&pageSize=10",
    ]
    for path in admin_paths_manager:
        code, data = admin_get(m_tok, path)
        short = path.split("?")[0].replace("/api/admin/", "")
        ok(f"admin {short}", code == 200, f"status={code}")

    for path in ["/api/admin/tiers-page?page=1&pageSize=20", "/api/admin/staff-page?page=1&pageSize=20", "/api/admin/logs?page=1&pageSize=10"]:
        code, _ = admin_get(m_tok, path)
        ok(f"admin boss-only blocked for manager ({path.split('/')[-1].split('?')[0]})", code == 403, f"status={code}")
        code, _ = admin_get(b_tok, path)
        ok(f"admin boss-only ok for boss ({path.split('/')[-1].split('?')[0]})", code == 200, f"status={code}")

    code, push = admin_get(m_tok, "/api/admin/push")
    ok("push config readable", code == 200 and isinstance(push, dict))

    # game input uses staff APIs from admin page
    code, _ = req("GET", "/api/staff/projects", token=m_tok)
    ok("admin gameinput via staff/projects", code == 200, f"status={code}")

    print(f"\n=== Summary: {len(PASS)} passed, {len(FAIL)} failed, {len(WARN)} warnings, {len(SKIP)} skipped ===")
    if FAIL:
        print("\nFailures:")
        for name, detail in FAIL:
            print(f"  - {name}: {detail}")
        sys.exit(1)
    if WARN:
        print("\nWarnings:")
        for name, detail in WARN:
            print(f"  - {name}: {detail}")


if __name__ == "__main__":
    main()
