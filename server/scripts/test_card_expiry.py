"""Card expiry: issue sets an expire date, the daily sweep counts down and expires overdue cards."""
from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import logic as L  # noqa: E402
from models import AssetFlow, Base, Card, CardTpl, User, Wallet  # noqa: E402

STAFF = {"id": 7, "nick": "店员小李", "role": "MANAGER"}


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sess = sessionmaker(bind=engine)()
    sess.add_all([
        User(id=7, no="S7", nick="店员小李", role="MANAGER"),
        User(id=9, no="000009", nick="天才儿童", role="CUSTOMER", status="ACTIVE", tail="9366"),
        Wallet(user_id=9),
        CardTpl(id=3, name="桌游卡", cat="GAME", cost=100, days=30),
        CardTpl(id=4, name="酒水卡", cat="FOOD", cost=100, days=7),
    ])
    sess.flush()
    return sess


def at_day(d: date):
    return patch.object(L, "business_now", return_value=datetime(d.year, d.month, d.day, 15, 0))


class CardExpiryTests(unittest.TestCase):
    def test_issue_sets_expire_and_sweep_counts_down(self):
        sess = make_session()
        with at_day(date(2026, 9, 30)):
            card = L.issue_card(sess, 9, sess.get(CardTpl, 3), "STAFF_GRANT", "补发", op="店员小李")
        self.assertEqual(card.expire, "2026-10-29")
        self.assertEqual(card.days_left, 30)

        with at_day(date(2026, 10, 2)):
            self.assertEqual(L.sweep_card_expiry(sess), 0)
        self.assertEqual(card.days_left, 28)
        self.assertEqual(card.status, "UNUSED")

        with at_day(date(2026, 10, 29)):
            L.sweep_card_expiry(sess)
        self.assertEqual(card.days_left, 1)
        self.assertEqual(card.status, "UNUSED")

        with at_day(date(2026, 10, 30)):
            self.assertEqual(L.sweep_card_expiry(sess), 1)
        self.assertEqual(card.days_left, 0)
        self.assertEqual(card.status, "EXPIRED")
        self.assertEqual(card.done_op, "系统")
        out = sess.query(AssetFlow).filter_by(ref=f"card-out-{card.id}").one()
        self.assertEqual(out.status, "已过期")

    def test_legacy_card_backfills_expire_from_issue_day(self):
        sess = make_session()
        legacy = Card(id=1, uid=9, tpl=4, no="KQ1", status="UNUSED", days_left=7, expire="", at="2026-09-28 20:00")
        locked = Card(id=2, uid=9, tpl=3, no="KQ2", status="LOCKED", days_left=30, expire="", at="2026-08-01 10:00")
        sess.add_all([legacy, locked])
        sess.flush()

        with at_day(date(2026, 10, 2)):
            L.sweep_card_expiry(sess)
        self.assertEqual(legacy.expire, "2026-10-04")
        self.assertEqual(legacy.days_left, 3)
        self.assertEqual(legacy.status, "UNUSED")
        # A card held by a live verify code is never expired mid-checkout, only counted down.
        self.assertEqual(locked.expire, "2026-08-30")
        self.assertEqual(locked.days_left, 0)
        self.assertEqual(locked.status, "LOCKED")

    def test_expired_card_cannot_be_verified(self):
        sess = make_session()
        with at_day(date(2026, 9, 1)):
            card = L.issue_card(sess, 9, sess.get(CardTpl, 4), "STAFF_GRANT", "补发")
        with at_day(date(2026, 9, 8)):
            with self.assertRaisesRegex(ValueError, "已过期"):
                L.gen_verify(sess, 9, [card.id])
            with self.assertRaisesRegex(ValueError, "已过期"):
                L.staff_direct_verify(sess, 9, card.id, "9366", "", STAFF)


if __name__ == "__main__":
    unittest.main()
