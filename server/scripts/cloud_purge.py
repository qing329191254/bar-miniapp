"""Call cloud purge endpoint after deploy.

  python scripts/cloud_purge.py
  python scripts/cloud_purge.py --dry-run   # only inspect counts
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("API_BASE", "https://api-303869-11-1476141553.sh.run.tcloudbase.com").rstrip("/")
ACCOUNT = os.environ.get("BOSS_ACCOUNT", "13121309366")
PASSWORD = os.environ.get("BOSS_PASSWORD", "123456")
CONFIRM = "PURGE_KEEP_BOSSES"


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
        with urllib.request.urlopen(r, timeout=120) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw[:500]}
        return e.code, payload


def login() -> str:
    code, data = req("POST", "/api/auth/login", body={"account": ACCOUNT, "password": PASSWORD})
    if code != 200 or not data or not data.get("token"):
        raise SystemExit(f"login failed: {code} {data}")
    return data["token"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    tok = login()

    code, staff = req("GET", "/api/admin/staff-page?page=1&pageSize=100", token=tok)
    rows = (staff or {}).get("rows") or []
    bosses = [r for r in rows if r.get("role") == "BOSS"]
    others = [r for r in rows if r.get("role") != "BOSS"]
    code, members = req("GET", "/api/admin/members?page=1&pageSize=100", token=tok)
    mtotal = (members or {}).get("total")
    print(f"before: bosses={len(bosses)} staff_others={len(others)} members_total={mtotal}")
    for b in bosses:
        print(f"  KEEP boss id={b['id']} no={b['no']} nick={b['nick']} phone={b['phone']}")

    if args.dry_run:
        print("dry-run only, not purging")
        return 0

    code, out = req(
        "POST",
        "/api/admin/ops/purge-test-data",
        token=tok,
        body={"data": {"confirm": CONFIRM}},
    )
    print("purge status", code)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if code != 200:
        return 1

    # re-login may still work; verify
    tok = login()
    code, staff = req("GET", "/api/admin/staff-page?page=1&pageSize=100", token=tok)
    rows = (staff or {}).get("rows") or []
    code, members = req("GET", "/api/admin/members?page=1&pageSize=100", token=tok)
    print(
        "after: staff_rows=",
        len(rows),
        "roles=",
        sorted({r.get("role") for r in rows}),
        "members_total=",
        (members or {}).get("total"),
    )
    code, agr = req("GET", "/api/admin/agreements", token=tok)
    print("agreements still ok", code, list((agr or {}).keys()) if isinstance(agr, dict) else agr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
