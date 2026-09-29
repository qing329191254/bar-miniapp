"""Unit tests: shard records include staff adjustments and skip zero-shard games."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logic as L  # noqa: E402


def _game(gid, time, players, status=None):
    g = SimpleNamespace(
        id=gid, pname="德州扑克", table="", round="", time=time, op="张老板",
        status=status, players=players,
    )
    g.to_dict = lambda: {"id": gid, "pname": g.pname, "table": g.table, "round": g.round, "time": g.time, "op": g.op}
    return g


class ShardRecordsTests(unittest.TestCase):
    def test_adjust_included_and_zero_shard_game_skipped(self):
        games = [
            _game(3, "2026-09-29 15:27", [{"uid": 9, "pts": 500000, "sh": 10}]),
            _game(2, "2026-09-29 14:00", [{"uid": 9, "pts": 100, "sh": 0}]),
            _game(1, "2026-09-28 20:00", [{"uid": 9, "pts": 0, "sh": 5}], status="VOID"),
        ]
        adjust = SimpleNamespace(
            id=40, t="09-29 15:10", op="张老板", action="SHARD_ADJUST",
            detail="快速调整 天才儿童 碎片 +100 · 本周 0→100 · 累计 0→100 · 原因：活动补发",
        )

        def query_side(model):
            q = MagicMock()
            if model is L.GameRecord:
                q.order_by.return_value.limit.return_value = games
            elif model is L.OpLog:
                q.filter.return_value.order_by.return_value.limit.return_value = [adjust]
            return q

        sess = MagicMock()
        sess.query.side_effect = query_side
        rows = L._legacy_shard_records(sess, 9)

        self.assertEqual([r["key"] for r in rows], ["game-3", "adj-40", "game-1"])
        self.assertEqual(rows[0]["delta"], 10)
        self.assertEqual(rows[1]["title"], "店员调整碎片")
        self.assertEqual(rows[1]["delta"], 100)
        self.assertIn("活动补发", rows[1]["meta"])
        self.assertTrue(rows[2]["void"])
        self.assertEqual(sum(r["delta"] for r in rows if not r["void"]), 110)


    def test_void_deduction_and_weekly_reset_rows(self):
        games = [_game(5, "2026-09-29 11:00", [{"uid": 9, "pts": 0, "sh": 8}], status="VOID")]
        logs = [
            SimpleNamespace(id=1, ref="game-void-sh-5", before=20, after=12, at="2026-09-29 12:00", op="张老板"),
            SimpleNamespace(id=2, ref="shardw-2026-09-28", before=30, after=0, at="2026-09-28 12:00", op="系统"),
        ]

        def query_side(model):
            q = MagicMock()
            if model is L.GameRecord:
                q.order_by.return_value.limit.return_value = games
            elif model is L.PointLog:
                q.filter.return_value.order_by.return_value.limit.return_value = logs
            else:
                q.filter.return_value.order_by.return_value.limit.return_value = []
            return q

        sess = MagicMock()
        sess.query.side_effect = query_side
        rows = {r["key"]: r for r in L._legacy_shard_records(sess, 9)}

        self.assertFalse(rows["game-5"]["void"])
        self.assertEqual(rows["void-5"]["delta"], -8)
        self.assertIn("张老板", rows["void-5"]["meta"])
        self.assertEqual(rows["shardw-2026-09-28"]["delta"], -30)
        self.assertIn("历史累计不变", rows["shardw-2026-09-28"]["meta"])


if __name__ == "__main__":
    unittest.main()
