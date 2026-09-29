"""Unit tests: customer_ledger includes sign-in and game points."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logic as L  # noqa: E402


class CustomerLedgerPointSourcesTests(unittest.TestCase):
    def test_sign_and_game_points_appear_in_point_ledger(self):
        sign = SimpleNamespace(id=11, uid=9, month="2026-09", day=28, pts=100, extra_pts=50)
        game = SimpleNamespace(
            id=77, pname="德扑", table="A1", round="", time="09-28 21:00",
            op="店员", status=None,
            players=[{"uid": 9, "pts": 300, "sh": 1}],
        )

        def query_side(model):
            q = MagicMock()
            name = getattr(model, "__name__", "")
            if model is L.Withdrawal or name == "Withdrawal":
                q.filter_by.return_value.order_by.return_value.limit.return_value = []
            elif model is L.OpLog or name == "OpLog":
                q.filter.return_value.order_by.return_value.limit.return_value = []
            elif model is L.Card or name == "Card":
                q.filter_by.return_value.order_by.return_value.limit.return_value = []
            elif model is L.SignRecord or name == "SignRecord":
                # _signed_date_set uses .all(); ledger uses order_by.limit
                q.filter_by.return_value.all.return_value = [sign]
                q.filter_by.return_value.order_by.return_value.limit.return_value = [sign]
            elif model is L.GameRecord or name == "GameRecord":
                q.order_by.return_value.limit.return_value = [game]
            elif model is L.SignRule or name == "SignRule":
                q.all.return_value = []
            else:
                q.filter_by.return_value.order_by.return_value.limit.return_value = []
                q.filter.return_value.order_by.return_value.limit.return_value = []
                q.order_by.return_value.limit.return_value = []
                q.all.return_value = []
            return q

        sess = MagicMock()
        sess.query.side_effect = query_side

        with patch.object(L, "setting", return_value={"signPoints": 100}):
            items = L.customer_ledger(sess, uid=9, kind="POINT", limit=80)

        titles = [x["title"] for x in items]
        self.assertIn("签到积分", titles)
        self.assertTrue(any(t.startswith("对局积分") for t in titles))
        sign_row = next(x for x in items if x["title"] == "签到积分")
        self.assertEqual(sign_row["amount"], "+150")
        game_row = next(x for x in items if x["title"].startswith("对局积分"))
        self.assertEqual(game_row["amount"], "+300")

    def test_streak_ending_on(self):
        signed = {date(2026, 9, 26), date(2026, 9, 27), date(2026, 9, 28)}
        self.assertEqual(L._streak_ending_on(signed, date(2026, 9, 28)), 3)
        self.assertEqual(L._streak_ending_on(signed, date(2026, 9, 26)), 1)


if __name__ == "__main__":
    unittest.main()
