"""Unit checks for exchange perLimit / revoke stock and inactive identity release."""
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


class ExchangePerLimitTests(unittest.TestCase):
    def test_void_exchange_cards_do_not_count_toward_per_limit(self):
        wallet = SimpleNamespace(point_av=1000, user_id=9)
        tpl = SimpleNamespace(id=3, exch=True, cost=100, per_limit=1, stock=-1, name="桌游卡")
        card_filters = []

        def query_side_effect(model):
            q = MagicMock()
            if model is L.CardTpl:
                q.filter_by.return_value.with_for_update.return_value.first.return_value = tpl
            elif model is L.Wallet:
                q.filter_by.return_value.with_for_update.return_value.first.return_value = wallet
            elif model is L.Card:
                def capture_filter(*args):
                    card_filters.append(args)
                    cq = MagicMock()
                    cq.count.return_value = 0
                    return cq
                q.filter.side_effect = capture_filter
            return q

        sess = MagicMock()
        sess.query.side_effect = query_side_effect
        with patch.object(L, "issue_card") as issue:
            ok = L.do_exchange(sess, uid=9, tid=3, qty=1)
        self.assertTrue(ok)
        self.assertEqual(wallet.point_av, 900)
        issue.assert_called_once()
        # per_limit path queried Card with status != VOID (4 predicates)
        self.assertTrue(card_filters)
        self.assertGreaterEqual(len(card_filters[0]), 4)
        joined = " ".join(str(a) for a in card_filters[0])
        self.assertIn("status", joined.lower())

    def test_revoke_exchange_restores_stock(self):
        sess = MagicMock()
        user = SimpleNamespace(id=9, role="CUSTOMER", status="ACTIVE", nick="测")
        tm = SimpleNamespace(id=3, name="桌游卡", stock=0)
        card = SimpleNamespace(id=1, uid=9, tpl=3, status="UNUSED", src="EXCHANGE", void_reason=None)

        def get_side(model, pk):
            if model is L.User:
                return user
            if model is L.CardTpl:
                return tm
            return None

        sess.get.side_effect = get_side
        q = MagicMock()
        q.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = [card]
        sess.query.return_value = q
        admin = {"id": 1, "role": "BOSS", "nick": "老板"}

        out = L.member_revoke_cards(sess, 9, 3, 1, "测限额", admin)
        self.assertEqual(out["qty"], 1)
        self.assertEqual(card.status, "VOID")
        self.assertEqual(tm.stock, 1)


class InactiveIdentityTests(unittest.TestCase):
    def test_release_disabled_breaks_phone_match(self):
        gone = MagicMock()
        gone.id = 8
        gone.status = "DISABLED"
        gone.phone = "131****9366"
        gone.tail = "9366"
        gone.wx_openid = "oid-z"
        gone.no = "000008"
        sess = MagicMock()
        L.release_inactive_login_identity(sess, gone)
        self.assertEqual(gone.wx_openid, "")
        self.assertTrue(str(gone.phone).startswith("已停用-"))
        self.assertFalse(L.user_matches_phone(gone, "13121309366"))


class CreateStaffInactiveTests(unittest.TestCase):
    @patch("logic.bind_wx_phone")
    @patch("logic.log")
    @patch("logic.new_id", return_value=9002)
    @patch("logic.alloc_staff_no", return_value="S9002")
    @patch("logic.hash_pwd", return_value="hashed")
    @patch("logic.public_user", side_effect=lambda sess, u: {"id": u.id, "role": u.role, "nick": u.nick})
    def test_deactivated_customer_phone_can_be_hired(self, *_mocks):
        gone = SimpleNamespace(
            id=8, role="CUSTOMER", status="DEACTIVATED",
            phone="188****1830", tail="1830", wx_openid="oid-x", no="000008",
            nick="旧会员", pwd="",
        )
        calls = {"n": 0}

        def users_by_phone(_sess, _phone):
            calls["n"] += 1
            if calls["n"] == 1:
                return [gone]
            return []

        sess = MagicMock()
        with patch.object(L, "users_by_phone", side_effect=users_by_phone):
            out = L.create_staff(
                sess,
                {"phone": "18810801830", "nick": "新员工", "role": "STAFF"},
                {"role": "BOSS", "id": 1, "nick": "老板"},
            )
        self.assertEqual(out["role"], "STAFF")
        self.assertEqual(out["nick"], "新员工")
        sess.add.assert_called_once()
        self.assertTrue(str(gone.phone).startswith("已注销-"))


if __name__ == "__main__":
    unittest.main()
