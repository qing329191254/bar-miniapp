"""Card / shard ledger rows should carry before→after balance for reconciliation."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import logic as L  # noqa: E402
from models import AssetFlow, Base, CardTpl, User, Wallet  # noqa: E402


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sess = sessionmaker(bind=engine)()
    sess.add_all([
        User(id=9, no="000009", nick="天才儿童", role="CUSTOMER", status="ACTIVE"),
        Wallet(user_id=9, shard_w=3, shard_t=10),
        CardTpl(id=1, name="游戏卡", cat="GAME", days=30, cost=0, use="", rules=""),
    ])
    sess.flush()
    return sess


class CardShardBalanceFlowTests(unittest.TestCase):
    def test_card_in_and_out_write_held_balance(self):
        sess = make_session()
        c1 = L.issue_card(sess, 9, sess.get(CardTpl, 1), "SIGN_IN_REWARD", "连续签到 14 天奖励", op="系统")
        sess.flush()
        inn = sess.query(AssetFlow).filter_by(uid=9, ref=f"card-in-{c1.id}").one()
        self.assertEqual((inn.bal_before, inn.bal_after), (0, 1))

        c2 = L.issue_card(sess, 9, sess.get(CardTpl, 1), "MANUAL_GRANT", "店员补发 · 测试", op="小马")
        sess.flush()
        inn2 = sess.query(AssetFlow).filter_by(uid=9, ref=f"card-in-{c2.id}").one()
        self.assertEqual((inn2.bal_before, inn2.bal_after), (1, 2))

        L.close_card(sess, c1, "VOID", {"nick": "小马"}, "手动扣减 · 积分赛上桌")
        sess.flush()
        out = sess.query(AssetFlow).filter_by(uid=9, ref=f"card-out-{c1.id}").one()
        self.assertEqual((out.bal_before, out.bal_after), (2, 1))

        page = L.member_ledger_page(sess, 9, kind="card", page=1, page_size=10)
        by_id = {x["id"]: x for x in page["items"]}
        self.assertEqual(by_id[f"card-in-{c1.id}"]["process"], "游戏卡 0→1")
        self.assertEqual(by_id[f"card-out-{c1.id}"]["process"], "游戏卡 2→1")
        cust = L.customer_ledger_page(sess, 9, kind="card", limit=10)
        self.assertEqual(
            next(x for x in cust["items"] if x["id"] == f"card-out-{c1.id}")["process"],
            "游戏卡 2→1",
        )

    def test_shard_adjust_writes_cumulative_balance(self):
        sess = make_session()
        L.member_adjust_shard(sess, 9, 5, "测试加碎片", {"role": "BOSS", "nick": "老板", "id": 1})
        sess.flush()
        row = sess.query(AssetFlow).filter_by(uid=9, asset="SHARD").order_by(AssetFlow.id.desc()).first()
        self.assertEqual((row.bal_before, row.bal_after), (10, 15))
        page = L.member_ledger_page(sess, 9, kind="shard", page=1, page_size=5)
        self.assertEqual(page["items"][0]["process"], "10→15")
        records = L.shard_records_page(sess, 9, limit=5)
        self.assertEqual(records["items"][0]["process"], "10→15")

    def test_batch_grant_increments_balance_each_card(self):
        sess = make_session()
        # Seed 9 held cards first.
        for _ in range(9):
            L.issue_card(sess, 9, sess.get(CardTpl, 1), "MANUAL_GRANT", "底数", op="系统")
        sess.flush()
        L.member_grant_cards(
            sess, 9, 1, 4, "快速调整",
            {"role": "BOSS", "nick": "秋阳", "id": 1},
            require_reason=False,
        )
        sess.flush()
        rows = (
            sess.query(AssetFlow)
            .filter_by(uid=9, asset="CARD", typ="card_in")
            .order_by(AssetFlow.id.asc())
            .all()
        )
        batch = [r for r in rows if "快速调整" in (r.content or "")]
        self.assertEqual(len(batch), 4)
        self.assertEqual(
            [(r.bal_before, r.bal_after) for r in batch],
            [(9, 10), (10, 11), (11, 12), (12, 13)],
        )

    def test_backfill_restores_missing_card_balances(self):
        sess = make_session()
        c1 = L.issue_card(sess, 9, sess.get(CardTpl, 1), "SIGN_IN_REWARD", "连签奖励", op="系统")
        c2 = L.issue_card(sess, 9, sess.get(CardTpl, 1), "MANUAL_GRANT", "补发", op="小马")
        L.close_card(sess, c1, "VOID", {"nick": "小马"}, "积分赛上桌")
        sess.flush()
        for row in sess.query(AssetFlow).filter_by(uid=9, asset="CARD"):
            row.bal_before = None
            row.bal_after = None
        sess.flush()

        result = L.backfill_member_flow_balances(sess, 9)
        self.assertTrue(result["cards"]["ok"])
        by_ref = {r.ref: r for r in sess.query(AssetFlow).filter_by(uid=9, asset="CARD")}
        self.assertEqual((by_ref[f"card-in-{c1.id}"].bal_before, by_ref[f"card-in-{c1.id}"].bal_after), (0, 1))
        self.assertEqual((by_ref[f"card-in-{c2.id}"].bal_before, by_ref[f"card-in-{c2.id}"].bal_after), (1, 2))
        self.assertEqual((by_ref[f"card-out-{c1.id}"].bal_before, by_ref[f"card-out-{c1.id}"].bal_after), (2, 1))

    def test_balance_is_per_card_type(self):
        sess = make_session()
        sess.add(CardTpl(id=2, name="钢琴点歌卡", cat="SERVICE", days=30, cost=0, use="", rules=""))
        sess.flush()
        game = L.issue_card(sess, 9, sess.get(CardTpl, 1), "MANUAL_GRANT", "补发游戏卡", op="秋阳")
        piano = L.issue_card(sess, 9, sess.get(CardTpl, 2), "MANUAL_GRANT", "补发点歌卡", op="秋阳")
        sess.flush()
        by_ref = {r.ref: r for r in sess.query(AssetFlow).filter_by(uid=9, asset="CARD")}
        # Each type starts its own counter — not a shared pack total.
        self.assertEqual((by_ref[f"card-in-{game.id}"].bal_before, by_ref[f"card-in-{game.id}"].bal_after), (0, 1))
        self.assertEqual((by_ref[f"card-in-{piano.id}"].bal_before, by_ref[f"card-in-{piano.id}"].bal_after), (0, 1))
        page = L.member_ledger_page(sess, 9, kind="card", page=1, page_size=10)
        by_id = {x["id"]: x for x in page["items"]}
        self.assertEqual(by_id[f"card-in-{game.id}"]["process"], "游戏卡 0→1")
        self.assertEqual(by_id[f"card-in-{piano.id}"]["process"], "钢琴点歌卡 0→1")


if __name__ == "__main__":
    unittest.main()
