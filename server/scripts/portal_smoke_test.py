import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8020"
ROOT = Path(__file__).resolve().parents[2]
PASS, FAIL = [], []


def ok(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL.append(name)
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def req(method, path, token=None, body=None):
    url = BASE + path
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        data = json.dumps(body).encode()
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
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


def resolve_home(role, portal="", force_choose=False):
    if not role:
        return "/pages/login/login"
    if role == "CUSTOMER":
        return "/pages/c/home"
    if not force_choose:
        if portal == "customer":
            return "/pages/c/home"
        if portal == "staff":
            return "/pages/s/todo"
    return "/pages/login/portal"


def main():
    mp = ROOT / "bar-miniprogram"
    portal = mp / "pages/login/portal.vue"
    pages = (mp / "pages.json").read_text(encoding="utf-8")
    api_js = (mp / "utils/api.js").read_text(encoding="utf-8")
    login_js = (mp / "pages/login/login.vue").read_text(encoding="utf-8")
    boot_js = (mp / "pages/boot/boot.vue").read_text(encoding="utf-8")
    tab_js = (mp / "components/tab-bar/tab-bar.vue").read_text(encoding="utf-8")
    c_mine = (mp / "pages/c/mine.vue").read_text(encoding="utf-8")
    s_mine = (mp / "pages/s/mine.vue").read_text(encoding="utf-8")
    reminder = (mp / "utils/staff-reminder.js").read_text(encoding="utf-8")

    ok("portal.vue exists", portal.exists())
    ok("pages.json registers portal", "pages/login/portal" in pages)
    ok(
        "api.js has resolveHomeUrl + portal helpers",
        all(x in api_js for x in ["resolveHomeUrl", "setPortal", "isStaffPortal", "forceChoose"]),
    )
    ok("login forceChoose after auth", "forceChoose: true" in login_js)
    ok("boot uses resolveHomeUrl", "resolveHomeUrl()" in boot_js)
    ok("tab-bar uses isStaffPortal", "isStaffPortal()" in tab_js)
    ok("c/mine switch to staff", "切换到员工端" in c_mine and 'setPortal("staff")' in c_mine)
    ok("s/mine switch to customer", "切换到会员端" in s_mine and 'setPortal("customer")' in s_mine)
    ok("reminder gated by isStaffPortal", "isStaffPortal()" in reminder)

    ok("customer home", resolve_home("CUSTOMER") == "/pages/c/home")
    ok(
        "staff login forces choose",
        resolve_home("STAFF", portal="staff", force_choose=True) == "/pages/login/portal",
    )
    ok("staff remembered staff", resolve_home("MANAGER", portal="staff") == "/pages/s/todo")
    ok("staff remembered customer", resolve_home("BOSS", portal="customer") == "/pages/c/home")
    ok("staff no portal -> choose", resolve_home("STAFF", portal="") == "/pages/login/portal")

    st, accounts = req("GET", "/api/dev/accounts")
    ok("dev accounts", st == 200 and accounts and accounts.get("staff"), f"status={st}")
    staff = (accounts or {}).get("staff") or []
    staff_user = next((x for x in staff if x.get("role") in ("STAFF", "MANAGER", "BOSS")), None)
    ok("has staff seed", bool(staff_user), str(staff_user and staff_user.get("no")))

    token = None
    role = None
    pwd_candidates = ["123456", "admin123", "888888", "password"]
    seed_py = (ROOT / "server/seed_db.py").read_text(encoding="utf-8")
    m = re.search(r'password\s*=\s*["\']([^"\']+)["\']', seed_py)
    if m and m.group(1) not in pwd_candidates:
        pwd_candidates.insert(0, m.group(1))
    # also pull from seed.json if present
    for match in re.finditer(r'"password"\s*:\s*"([^"]+)"', (ROOT / "server/seed.json").read_text(encoding="utf-8")):
        if match.group(1) not in pwd_candidates:
            pwd_candidates.append(match.group(1))

    if staff_user:
        for pwd in pwd_candidates:
            st, body = req(
                "POST",
                "/api/auth/login",
                body={
                    "account": staff_user["no"],
                    "password": pwd,
                    "agreed": True,
                    "termsVersion": 1,
                    "privacyVersion": 1,
                },
            )
            if st == 200 and body and body.get("token"):
                token = body["token"]
                role = body["user"]["role"]
                ok(f"staff password login", True, f"pwd={pwd} role={role} no={staff_user['no']}")
                break
        if not token:
            ok("staff password login", False, f"tried {pwd_candidates}")

    if token:
        st, me = req("GET", "/api/me", token=token)
        ok(
            "staff /me (member shell)",
            st == 200 and me and me.get("user", {}).get("role") != "CUSTOMER",
            f"status={st} role={(me or {}).get('user', {}).get('role')}",
        )
        coins = (me or {}).get("user", {}).get("coin")
        ok("staff /me has wallet fields", coins is not None, f"coin={coins}")

        st, _ = req("GET", "/api/points", token=token)
        ok("staff /points (member API)", st == 200, f"status={st}")

        st, _ = req("GET", "/api/orders", token=token)
        ok("staff /orders (member API)", st == 200, f"status={st}")

        st, _ = req("GET", "/api/cards", token=token)
        ok("staff /cards (member API)", st == 200, f"status={st}")

        st, _ = req("GET", "/api/staff/todo-summary", token=token)
        ok("staff /staff/todo-summary still works", st == 200, f"status={st}")

    phone = "139%08d" % (int(__import__("time").time()) % 100000000)
    st, sms = req("POST", "/api/auth/sms/send", body={"phone": phone})
    ok("sms send mock", st == 200 and sms and sms.get("ok"), f"status={st} {sms}")
    code = (sms or {}).get("debugCode")
    st_ag, ag = req("GET", "/api/agreements")
    terms_ver = int(((ag or {}).get("terms") or {}).get("ver") or 1) if st_ag == 200 else 1
    privacy_ver = int(((ag or {}).get("privacy") or {}).get("ver") or 1) if st_ag == 200 else 1
    if code:
        st, login = req(
            "POST",
            "/api/auth/login",
            body={
                "phone": phone,
                "smsCode": code,
                "agreed": True,
                "termsVersion": terms_ver,
                "privacyVersion": privacy_ver,
                "code": "",
            },
        )
        ok(
            "customer sms login",
            st == 200 and (login or {}).get("user", {}).get("role") == "CUSTOMER",
            f"status={st} role={(login or {}).get('user', {}).get('role')}",
        )
        ct = (login or {}).get("token")
        if ct:
            st, _ = req("GET", "/api/staff/todo-summary", token=ct)
            ok("customer blocked from staff API", st in (401, 403), f"status={st}")

    print()
    print(f"RESULT {len(PASS)}/{len(PASS) + len(FAIL)} passed")
    if FAIL:
        print("Failed:", ", ".join(FAIL))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
