"""E2E: staff as member can order; todo/accept/finish; customer still orders."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8020"
PASS, FAIL = [], []


def ok(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL") + f"  {name}" + (f" — {detail}" if detail else ""))


def req(method, path, token=None, body=None):
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        data = json.dumps(body).encode()
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"detail": raw}
        return e.code, payload


def main():
    # --- staff login ---
    st, accounts = req("GET", "/api/dev/accounts")
    ok("dev accounts", st == 200 and bool((accounts or {}).get("staff")))
    staff = next(x for x in accounts["staff"] if x.get("role") in ("STAFF", "MANAGER", "BOSS"))
    st, login = req(
        "POST",
        "/api/auth/login",
        body={"account": staff["no"], "password": "123456", "agreed": True, "termsVersion": 1, "privacyVersion": 1},
    )
    ok("staff login", st == 200 and bool((login or {}).get("token")), f"status={st}")
    token = login["token"]
    uid = login["user"]["id"]
    role = login["user"]["role"]
    ok("staff is not CUSTOMER", role != "CUSTOMER", f"role={role}")

    st, me = req("GET", "/api/me", token=token)
    ok("staff /me", st == 200 and (me or {}).get("user", {}).get("id") == uid)
    coin_before = ((me or {}).get("user") or {}).get("coin") or {}
    bal_before = int(coin_before.get("total") or 0)
    ok("staff has wallet", "p" in coin_before and "b" in coin_before, f"coin={coin_before}")

    st, products = req("GET", "/api/products")
    prod = next(p for p in products["products"] if not p.get("offline") and not p.get("soldOut"))
    # pick cheapest simple product without required multi-spec if possible
    simple = None
    for p in products["products"]:
        if p.get("offline") or p.get("soldOut"):
            continue
        specs = p.get("specs") or []
        if p.get("hasSpec") and not specs:
            continue
        simple = p
        if not p.get("hasSpec"):
            break
    prod = simple or prod
    item = {"pid": prod["id"], "qty": 1, "specIds": []}
    if prod.get("hasSpec") and (prod.get("specs") or []):
        item["specIds"] = [prod["specs"][0]["id"]]

    # --- staff places own order (member portal) ---
    st, order = req(
        "POST",
        "/api/orders",
        token=token,
        body={"items": [item], "payType": "COIN", "remark": "e2e-staff-self"},
    )
    ok(
        "staff create_order",
        st == 200 and (order or {}).get("status") == "PENDING_ACCEPT" and (order or {}).get("uid") == uid,
        f"status={st} detail={(order or {}).get('detail') or (order or {}).get('status')}",
    )
    oid = (order or {}).get("id")
    total = int((order or {}).get("total") or 0)

    # appears in todo accept list
    st, todo = req("GET", "/api/staff/todo", token=token)
    ok("staff todo loads", st == 200)
    accept_ids = [o["id"] for o in (todo or {}).get("accept") or []]
    ok("self order in 待接单", oid in accept_ids, f"oid={oid} accept_n={len(accept_ids)}")

    # --- accept own order (deduct coins) ---
    st, acc = req("POST", f"/api/staff/orders/{oid}/accept", token=token, body={"reason": "店员操作"})
    ok("accept self order", st == 200, f"status={st} detail={(acc or {}).get('detail') if isinstance(acc, dict) else acc}")

    st, todo2 = req("GET", "/api/staff/todo", token=token)
    making_ids = [o["id"] for o in (todo2 or {}).get("making") or []]
    accept_ids2 = [o["id"] for o in (todo2 or {}).get("accept") or []]
    ok("moved to 制作中", oid in making_ids and oid not in accept_ids2, f"making={oid in making_ids}")

    st, me2 = req("GET", "/api/me", token=token)
    bal_after = int((((me2 or {}).get("user") or {}).get("coin") or {}).get("total") or 0)
    ok("coins deducted on accept", bal_after == bal_before - total, f"before={bal_before} after={bal_after} total={total}")

    # 今日接单 should count (order at is today)
    st_orders = int(((todo2 or {}).get("stat") or {}).get("orders") or 0)
    ok("今日接单 >= 1 after accept", st_orders >= 1, f"orders={st_orders}")

    # finish
    st, fin = req("POST", f"/api/staff/orders/{oid}/finish", token=token, body={})
    ok("finish self order", st == 200, f"status={st}")

    # list own orders as member
    st, mine_orders = req("GET", "/api/orders", token=token)
    ok("staff list own orders", st == 200 and any(o.get("id") == oid for o in (mine_orders or [])), f"status={st}")

    # offline order path
    st, off = req(
        "POST",
        "/api/orders",
        token=token,
        body={"items": [item], "payType": "OFFLINE", "remark": "e2e-staff-offline"},
    )
    ok(
        "staff offline order",
        st == 200 and (off or {}).get("status") == "PENDING_PAY",
        f"status={st} {(off or {}).get('detail') or (off or {}).get('status')}",
    )

    # --- customer SMS still can order ---
    st, ag = req("GET", "/api/agreements")
    tv = int(((ag or {}).get("terms") or {}).get("ver") or 1)
    pv = int(((ag or {}).get("privacy") or {}).get("ver") or 1)
    phone = "158%08d" % (int(time.time() * 1000) % 100000000)
    st, sms = req("POST", "/api/auth/sms/send", body={"phone": phone})
    ok("sms send", st == 200 and (sms or {}).get("debugCode"), f"status={st}")
    st, cust = req(
        "POST",
        "/api/auth/login",
        body={
            "phone": phone,
            "smsCode": (sms or {}).get("debugCode"),
            "agreed": True,
            "termsVersion": tv,
            "privacyVersion": pv,
            "code": "",
        },
    )
    ok("customer sms login", st == 200 and ((cust or {}).get("user") or {}).get("role") == "CUSTOMER", f"status={st}")
    ct = (cust or {}).get("token")
    if ct:
        st, cord = req(
            "POST",
            "/api/orders",
            token=ct,
            body={"items": [item], "payType": "COIN", "remark": "e2e-customer"},
        )
        ok(
            "customer create_order",
            st == 200 and (cord or {}).get("status") == "PENDING_ACCEPT",
            f"status={st} detail={(cord or {}).get('detail') if isinstance(cord, dict) else cord}",
        )
        # customer cannot staff-accept
        st, blocked = req("POST", f"/api/staff/orders/{(cord or {}).get('id')}/accept", token=ct, body={})
        ok("customer blocked from staff accept", st in (401, 403), f"status={st}")
    else:
        ok("customer create_order", False, "no token")
        ok("customer blocked from staff accept", False, "skipped")

    # --- still reject inactive nonsense: no token ---
    st, anon = req("POST", "/api/orders", body={"items": [item], "payType": "COIN"})
    ok("anonymous order rejected", st in (401, 403), f"status={st}")

    print()
    print(f"RESULT {len(PASS)}/{len(PASS) + len(FAIL)} passed")
    if FAIL:
        print("Failed:", ", ".join(FAIL))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
