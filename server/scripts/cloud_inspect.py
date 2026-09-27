"""Inspect cloud prod data before purge. Usage: python scripts/cloud_inspect.py"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("API_BASE", "https://api-303869-11-1476141553.sh.run.tcloudbase.com").rstrip("/")
ACCOUNT = os.environ.get("BOSS_ACCOUNT", "13121309366")
PASSWORD = os.environ.get("BOSS_PASSWORD", "123456")


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
            payload = {"raw": raw[:400]}
        return e.code, payload


def main() -> int:
    code, data = req("POST", "/api/auth/login", body={"account": ACCOUNT, "password": PASSWORD})
    if code != 200 or not data or not data.get("token"):
        print("login failed", code, data)
        return 1
    tok = data["token"]
    print("logged in as", data.get("user", {}).get("nick"), data.get("user", {}).get("role"), data.get("user", {}).get("id"))

    code, staff = req("GET", "/api/admin/staff-page?page=1&pageSize=100", token=tok)
    print("\n=== staff ===")
    for r in (staff or {}).get("rows") or []:
        print(f"  id={r['id']} role={r['role']} no={r['no']} nick={r['nick']} phone={r['phone']} status={r['status']}")

    code, members = req("GET", "/api/admin/members?page=1&pageSize=100", token=tok)
    items = (members or {}).get("items") or (members or {}).get("rows") or []
    print(f"\n=== members page1={len(items)} total={ (members or {}).get('total') } ===")
    for r in items:
        print(f"  id={r['id']} no={r['no']} nick={r['nick']} phone={r.get('phone')} status={r.get('status')}")

    for path in ["/api/admin/agreements", "/api/admin/content", "/api/admin/config"]:
        code, d = req("GET", path, token=tok)
        keys = list(d.keys())[:15] if isinstance(d, dict) else type(d)
        print(f"\n{path} => {code} {keys}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
