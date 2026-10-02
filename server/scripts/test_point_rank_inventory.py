"""POINT leaderboard uses live point_av inventory."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logic as L  # noqa: E402


class PointRankInventoryTests(unittest.TestCase):
    def test_point_rank_uses_available_balance_not_week_gain(self):
        u1 = SimpleNamespace(id=1, team_id=None, role="CUSTOMER", status="ACTIVE")
        u2 = SimpleNamespace(id=2, team_id=None, role="CUSTOMER", status="ACTIVE")
        wallets = {
            1: SimpleNamespace(point_av=7666, point_wg=100, point_mg=200, shard_w=0, shard_t=0),
            2: SimpleNamespace(point_av=500, point_wg=9000, point_mg=9000, shard_w=0, shard_t=0),
        }

        def wallet_of(_sess, uid):
            return wallets[uid]

        sess = MagicMock()
        with patch.object(L, "custs", return_value=[u1, u2]), \
             patch.object(L, "wallet_of", side_effect=wallet_of), \
             patch.object(L, "_reg_keys", return_value={1: 1, 2: 2}), \
             patch.object(L, "public_user", side_effect=lambda _s, u: {"id": u.id, "nick": f"u{u.id}"}), \
             patch.object(L, "champ_count", return_value=0):
            # Even with WEEK dim, ranking must follow point_av (staff adjust included).
            rows = L.rank_rows(sess, "POINT", "WEEK", "USER")

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["user"]["id"], 1)
        self.assertEqual(rows[0]["v"], 7666)
        self.assertEqual(rows[1]["user"]["id"], 2)
        self.assertEqual(rows[1]["v"], 500)

    def test_point_team_rank_sums_member_inventory(self):
        team = SimpleNamespace(id=10, name="飞行家", status="ACTIVE")
        u1 = SimpleNamespace(id=1, team_id=10, role="CUSTOMER", status="ACTIVE")
        u2 = SimpleNamespace(id=2, team_id=10, role="CUSTOMER", status="ACTIVE")
        wallets = {
            1: SimpleNamespace(point_av=1000, point_wg=0, point_mg=0, shard_w=1, shard_t=1),
            2: SimpleNamespace(point_av=2500, point_wg=0, point_mg=0, shard_w=0, shard_t=0),
        }
        sess = MagicMock()
        sess.query.return_value.all.return_value = [team]
        with patch.object(L, "custs", return_value=[u1, u2]), \
             patch.object(L, "wallet_of", side_effect=lambda _s, uid: wallets[uid]), \
             patch.object(L, "_reg_keys", return_value={1: 1, 2: 2}), \
             patch.object(L, "champ_count", return_value=0):
            rows = L.rank_rows(sess, "POINT", "MONTH", "TEAM")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["v"], 3500)
        self.assertEqual(rows[0]["team"]["name"], "飞行家")

    def test_shard_all_time_board_orders_by_all_time_total(self):
        u1 = SimpleNamespace(id=1, team_id=None, role="CUSTOMER", status="ACTIVE")
        u2 = SimpleNamespace(id=2, team_id=None, role="CUSTOMER", status="ACTIVE")
        wallets = {
            1: SimpleNamespace(point_av=0, point_wg=0, point_mg=0, shard_w=5, shard_t=10),
            2: SimpleNamespace(point_av=0, point_wg=0, point_mg=0, shard_w=1, shard_t=100),
        }
        sess = MagicMock()
        with patch.object(L, "custs", return_value=[u1, u2]), \
             patch.object(L, "wallet_of", side_effect=lambda _s, uid: wallets[uid]), \
             patch.object(L, "_reg_keys", return_value={1: 1, 2: 2}), \
             patch.object(L, "public_user", side_effect=lambda _s, u: {"id": u.id, "nick": f"u{u.id}"}):
            total = L.rank_rows(sess, "SHARD", "ALL", "USER")
        self.assertEqual([(r["user"]["id"], r["v"]) for r in total], [(2, 100), (1, 10)])


if __name__ == "__main__":
    unittest.main()
