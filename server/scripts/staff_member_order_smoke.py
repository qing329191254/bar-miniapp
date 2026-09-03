"""Staff in member portal can place their own orders."""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8020"
PASS, FAIL = [], []


def ok(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL.append(name)
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


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
            payload = {"raw": raw}
        return e.code, payload


def main():
    st, accounts = req("GET", "/api/dev/accounts")
    ok("dev accounts", st == 200 and accounts and accounts.get("staff"))
    staff = next((x for x in (accounts or {}).get("staff") or [] if x.get("role") in ("STAFF", "MANAGER", "BOSS")), None)
    ok("has staff", bool(staff), str(staff and staff.get("no")))

    st, login = req(
        "POST",
        "/api/auth/login",
        body={"account": staff["no"], "password": "123456", "agreed": True, "termsVersion": 1, "privacyVersion": 1},
    )
    ok("staff login", st == 200 and login and login.get("token"), f"status={st}")
    token = (login or {}).get("token")
    role = ((login or {}).get("user") or {}).get("role")
    ok("staff role not CUSTOMER", role and role != "CUSTOMER", f"role={role}")

    st, products = req("GET", "/api/products")
    ok("products", st == 200 and products and products.get("products"))
    prod = next((p for p in (products or {}).get("products") or [] if not p.get("offline") and not p.get("soldOut")), None)
    ok("has sellable product", bool(prod), str(prod and prod.get("id")))

    st, order = req(
        "POST",
        "/api/orders",
        token=token,
        body={"items": [{"pid": prod["id"], "qty": 1, "specIds": []}], "payType": "COIN", "tableId": None, "remark": "staff-self-order"},
    )
    detail = order if isinstance(order, dict) else {"raw": order}
    ok(
        "staff create_order allowed",
        st == 200 and detail.get("status") == "PENDING_ACCEPT" and detail.get("uid") == ((login or {}).get("user") or {}).get("id"),
        f"status={st} body={detail.get('detail') or detail.get('status') or detail}",
    )

    # Core regression: staff account can place an order (member-portal use case).
    # Full customer SMS path is covered elsewhere; skip here to avoid phone-collision noise.    print()
    print(f"RESULT {len(PASS)}/{len(PASS) + len(FAIL)} passed")
    if FAIL:
        print("Failed:", ", ".join(FAIL))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
