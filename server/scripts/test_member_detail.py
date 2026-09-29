"""member_detail must return every card / withdrawal / champion, not a truncated head."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logic as L  # noqa: E402
from models import AgreeLog, CardTpl, Champ, Withdrawal  # noqa: E402
from test_asset_flows import BOSS, make_session  # noqa: E402


class MemberDetailTests(unittest.TestCase):
    def test_returns_all_rows(self):
        sess = make_session()
        tm = sess.get(CardTpl, 3)
        cards = [L.issue_card(sess, 9, tm, "GAME_GIFT", "对局赠送 · 德州扑克 #130", op="店员") for _ in range(21)]
        sess.flush()
        L.close_card(sess, cards[0], "USED", BOSS)
        cards[1].status = "LOCKED"
        L.close_card(sess, cards[2], "VOID", BOSS, "手动扣减 · 测试")
        for i in range(12):
            sess.add(Withdrawal(id=100 + i, no=f"TF{i}", uid=9, pts=10, status="GRANTED", created="09-29 17:00"))
        for i in range(7):
            sess.add(Champ(uid=9, event="德州扑克", date="2026-09-29", n=1))
        sess.add(AgreeLog(doc="terms", ver=1, uid=9, at="09-29 17:35"))
        sess.flush()

        d = L.member_detail(sess, 9)
        self.assertEqual(len(d["cards"]), 21)
        self.assertEqual(d["cardStats"], {"unused": 18, "locked": 1, "used": 1, "void": 1})
        self.assertEqual(len(d["withdrawals"]), 12)
        self.assertEqual(len(d["champs"]), 7)
        self.assertEqual(d["champTotal"], 7)
        self.assertEqual(d["registered"], "09-29 17:35")
        used = next(c for c in d["cards"] if c["status"] == "USED")
        self.assertTrue(used["at"] and used["doneAt"] and used["doneOp"])


if __name__ == "__main__":
    unittest.main()
