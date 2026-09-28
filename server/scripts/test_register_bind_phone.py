"""Unit tests for register_or_bind_phone openid / phone identity."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logic as L  # noqa: E402


def _user(**kwargs):
    u = MagicMock()
    u.id = kwargs.get("id", 1)
    u.role = kwargs.get("role", "CUSTOMER")
    u.phone = kwargs.get("phone", "")
    u.tail = kwargs.get("tail", "")
    u.wx_openid = kwargs.get("wx_openid", "")
    return u


class RegisterOrBindPhoneTests(unittest.TestCase):
    def test_user_matches_phone(self):
        u = _user(phone="131****9366", tail="9366")
        self.assertTrue(L.user_matches_phone(u, "13121309366"))
        self.assertFalse(L.user_matches_phone(u, "18811479069"))

    def test_same_openid_same_phone_returns_existing(self):
        boss = _user(id=1, role="BOSS", phone="131****9366", tail="9366", wx_openid="oid-a")
        sess = MagicMock()
        sess.query.return_value.filter.return_value.first.return_value = boss

        with patch.object(L, "find_user_by_phone") as find_phone:
            out = L.register_or_bind_phone(sess, "13121309366", "oid-a")
            find_phone.assert_not_called()
        self.assertIs(out, boss)
        self.assertEqual(boss.phone, "131****9366")
        self.assertEqual(boss.wx_openid, "oid-a")

    def test_same_openid_different_phone_does_not_overwrite_staff_phone(self):
        boss = _user(id=1, role="BOSS", phone="131****9366", tail="9366", wx_openid="oid-a")
        customer = _user(id=2, role="CUSTOMER", phone="188****9069", tail="9069", wx_openid="")

        def query_side_effect(model):
            q = MagicMock()
            # first() used for openid lookup
            q.filter.return_value.first.return_value = boss if boss.wx_openid == "oid-a" else None
            q.filter.return_value.all.return_value = []
            return q

        sess = MagicMock()
        sess.query.side_effect = query_side_effect

        with patch.object(L, "find_user_by_phone", return_value=customer):
            out = L.register_or_bind_phone(sess, "18811479069", "oid-a")

        self.assertIs(out, customer)
        # Boss phone must stay; openid moved to the phone account
        self.assertEqual(boss.phone, "131****9366")
        self.assertEqual(boss.role, "BOSS")
        self.assertEqual(boss.wx_openid, "")
        self.assertEqual(customer.wx_openid, "oid-a")
        self.assertEqual(customer.phone, "188****9069")

    def test_same_openid_new_phone_creates_customer_without_touching_boss(self):
        boss = _user(id=1, role="BOSS", phone="131****9366", tail="9366", wx_openid="oid-a")
        created = []

        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value.first.return_value = boss if boss.wx_openid else None
            q.filter.return_value.all.return_value = []
            return q

        sess = MagicMock()
        sess.query.side_effect = query_side_effect
        sess.add.side_effect = lambda u: created.append(u)

        with patch.object(L, "find_user_by_phone", return_value=None), \
             patch.object(L, "new_id", return_value=99), \
             patch.object(L, "alloc_member_no", return_value="100099"), \
             patch.object(L, "wallet_of"), \
             patch.object(L, "demo_starter_enabled", return_value=False):
            out = L.register_or_bind_phone(sess, "18811479069", "oid-a")

        self.assertEqual(boss.phone, "131****9366")
        self.assertEqual(boss.wx_openid, "")
        self.assertEqual(out.role, "CUSTOMER")
        self.assertEqual(out.phone, "188****9069")
        self.assertEqual(out.wx_openid, "oid-a")
        self.assertEqual(out.nick, "玩咖用户100099")
        self.assertTrue(created)


if __name__ == "__main__":
    unittest.main()
