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
        self.assertEqual(by_id[f"card-in-{c1.id}"]["process"], "0→1")
        self.assertEqual(by_id[f"card-out-{c1.id}"]["process"], "2→1")
        cust = L.customer_ledger_page(sess, 9, kind="card", limit=10)
        self.assertEqual(
            next(x for x in cust["items"] if x["id"] == f"card-out-{c1.id}")["process"],
            "2→1",
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


if __name__ == "__main__":
    unittest.main()
