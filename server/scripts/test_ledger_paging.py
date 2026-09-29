"""Ledger / shard paging: walking every page returns every row exactly once, newest first."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logic as L  # noqa: E402
from models import AssetFlow, Wallet  # noqa: E402
from test_asset_flows import make_session  # noqa: E402


def seed(sess, uid, asset, n, same_time_every=3):
    for i in range(n):
        minute = i // same_time_every
        sess.add(AssetFlow(
            uid=uid, asset=asset, ref=f"{asset.lower()}-{i}", typ="adjust", title=f"#{i}",
            amount="+1", delta=1, at=f"2026-09-29 10:{minute:02d}", sort_at=f"2026-09-29 10:{minute:02d}:00", op="店员",
        ))
    sess.get(Wallet, uid).flow_ready = True
    sess.flush()


def walk(fetch):
    seen, before, pages = [], "", 0
    while True:
        page = fetch(before)
        seen.extend(page["items"])
        pages += 1
        if not page["hasMore"]:
            return seen, pages
        before = page["cursor"]
        assert pages < 100


class LedgerPagingTests(unittest.TestCase):
    def test_ledger_pages_cover_everything_once(self):
        sess = make_session()
        seed(sess, 9, "CARD", 95)
        seed(sess, 9, "COIN", 7)
        rows, pages = walk(lambda b: L.customer_ledger_page(sess, 9, "card", b, 30))
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), 95)
        self.assertEqual(len(set(ids)), 95)
        self.assertEqual(pages, 4)
        self.assertEqual(ids[0], "card-94")
        self.assertEqual(ids[-1], "card-0")

        rows, _ = walk(lambda b: L.customer_ledger_page(sess, 9, "all", b, 25))
        self.assertEqual(len({(r["kind"], r["id"]) for r in rows}), 102)

    def test_first_page_matches_legacy_call(self):
        sess = make_session()
        seed(sess, 9, "POINT", 100)
        self.assertEqual(len(L.customer_ledger(sess, 9, "point")), 80)
        page = L.customer_ledger_page(sess, 9, "point")
        self.assertTrue(page["hasMore"])

    def test_shard_pages(self):
        sess = make_session()
        seed(sess, 9, "SHARD", 64)
        rows, pages = walk(lambda b: L.shard_records_page(sess, 9, b, 30))
        self.assertEqual(len({r["key"] for r in rows}), 64)
        self.assertEqual(pages, 3)
        self.assertEqual(len(L.shard_records(sess, 9, 30)), 30)


if __name__ == "__main__":
    unittest.main()
