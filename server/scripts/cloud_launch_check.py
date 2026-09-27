"""List remaining cloud catalog/config after purge."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("API_BASE", "https://api-303869-11-1476141553.sh.run.tcloudbase.com").rstrip("/")


def req(method, path, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=45) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw[:300]}
        return e.code, payload


def main():
    code, data = req("POST", "/api/auth/login", body={"account": "13121309366", "password": "123456"})
    tok = data["token"]
    print("user", data["user"]["nick"], data["user"]["role"])

    checks = [
        ("/api/admin/staff-page?page=1&pageSize=50", "staff"),
        ("/api/admin/members?page=1&pageSize=5", "members"),
        ("/api/admin/products?page=1&pageSize=100", "products"),
        ("/api/admin/cardTpls?pageSize=0", "cardTpls"),
        ("/api/admin/tiers-page?page=1&pageSize=50", "tiers"),
        ("/api/admin/projects?pageSize=0", "projects"),
        ("/api/admin/team-management", "teams"),
        ("/api/admin/gameRecords?page=1&pageSize=5", "games"),
        ("/api/admin/orders-page?page=1&pageSize=5", "orders"),
        ("/api/admin/logs?page=1&pageSize=5", "logs"),
        ("/api/admin/agreements", "agreements"),
        ("/api/admin/content", "content"),
        ("/api/admin/config", "config"),
        ("/api/admin/settlement-config", "settle"),
        ("/api/admin/signin-overview?page=1&pageSize=5", "signin"),
    ]
    for path, name in checks:
        code, d = req("GET", path, token=tok)
        if not isinstance(d, dict):
            print(f"\n[{name}] {code}", d)
            continue
        # summarize
        if name == "staff":
            rows = d.get("rows") or []
            print(f"\n[{name}] {len(rows)}", [(r.get("id"), r.get("role"), r.get("nick")) for r in rows])
        elif name == "members":
            print(f"\n[{name}] total={d.get('total')} items={len(d.get('items') or [])}")
        elif name == "products":
            items = d.get("items") or d.get("rows") or d.get("list") or []
            if not items and isinstance(d.get("cats"), list):
                # maybe nested
                print(f"\n[{name}] keys={list(d.keys())[:10]} total={d.get('total')}")
            else:
                print(f"\n[{name}] total={d.get('total', len(items))} sample=", [
                    (x.get("id"), x.get("name") or x.get("title")) for x in items[:8]
                ])
        elif name in ("cardTpls", "projects"):
            items = d if isinstance(d, list) else (d.get("items") or d.get("rows") or d.get("list") or [])
            if isinstance(d, dict) and not items:
                print(f"\n[{name}] keys={list(d.keys())} total={d.get('total')}")
            else:
                print(f"\n[{name}] n={len(items)}", [
                    (x.get("id"), x.get("name")) for x in (items[:10] if isinstance(items, list) else [])
                ])
        elif name == "tiers":
            items = d.get("items") or d.get("rows") or []
            print(f"\n[{name}] total={d.get('total', len(items))}", [
                (x.get("id"), x.get("amount"), x.get("bonus")) for x in items[:10]
            ])
        elif name == "teams":
            print(f"\n[{name}] keys={list(d.keys())[:12]}", str(d)[:300])
        elif name in ("games", "orders", "logs", "signin"):
            print(f"\n[{name}] total={d.get('total')} keys={list(d.keys())[:8]}")
        elif name in ("agreements", "content", "config", "settle"):
            print(f"\n[{name}] keys={list(d.keys())[:15]}")
            if name == "content":
                shop = (d.get("shopInfo") or {})
                print("  shopInfo.name=", shop.get("name"), "addr=", (shop.get("addr") or shop.get("address") or "")[:40])
            if name == "agreements":
                for k in ("terms", "privacy"):
                    doc = d.get(k) or {}
                    body = doc.get("body") or doc.get("html") or doc.get("content") or ""
                    print(f"  {k} ver={doc.get('ver')} bodyLen={len(str(body))}")
        else:
            print(f"\n[{name}] {list(d.keys())[:12]}")


if __name__ == "__main__":
    main()
