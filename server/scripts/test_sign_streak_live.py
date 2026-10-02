"""Sign streak reads as broken once a day is missed, even though it is only written on sign-in."""
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
from models import Base, User, Wallet  # noqa: E402


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sess = sessionmaker(bind=engine)()
    sess.add_all([
        User(id=9, no="000009", nick="天才儿童", role="CUSTOMER", status="ACTIVE"),
        Wallet(user_id=9),
    ])
    L.save_setting(sess, "config", {"signPoints": 10})
    sess.flush()
    return sess


def at(y, m, d):
    return patch.object(L, "business_now", return_value=datetime(y, m, d, 10, 0))


class SignStreakLiveTests(unittest.TestCase):
    def test_streak_survives_until_a_day_is_missed(self):
        sess = make_session()
        for day in (28, 29, 30):
            with at(2026, 9, day):
                L.do_sign(sess, 9)
        self.assertEqual(sess.get(Wallet, 9).sign_streak, 3)

        with at(2026, 9, 30):
            self.assertEqual(L.live_sign_streak(sess, 9), 3)
        # Next morning, not signed yet: still unbroken, and across the month boundary.
        with at(2026, 10, 1):
            self.assertEqual(L.live_sign_streak(sess, 9), 3)
        # A full day missed: shown as 0, not the stale 3.
        with at(2026, 10, 2):
            self.assertEqual(L.live_sign_streak(sess, 9), 0)
            self.assertEqual(L.do_sign(sess, 9)["streak"], 1)
            self.assertEqual(L.live_sign_streak(sess, 9), 1)


if __name__ == "__main__":
    unittest.main()
