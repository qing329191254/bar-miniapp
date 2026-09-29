"""Purge on a real SQLite DB: business data gone, bosses/config kept, stock and point ledger consistent."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logic as L  # noqa: E402
from models import AssetFlow, Card, CardTpl, Order, Product, Recharge, User, Wallet  # noqa: E402
from test_asset_flows import BOSS, STAFF, make_session  # noqa: E402


@patch.object(L.cache, "lock_pending", return_value=True)
class PurgeTests(unittest.TestCase):
    def _dirty(self, sess):
        sess.get(CardTpl, 3).stock = 10
        sess.get(CardTpl, 3).exch = True
        sess.add(CardTpl(id=4, name="酒水卡", cat="DRINK", cost=50, stock=-1, exch=True))
        sess.flush()
        o = L.create_order(sess, 9, [{"pid": 1, "qty": 1}], "COIN", 1, "")
        L.accept_order(sess, o["id"], STAFF)
        L.finish_order(sess, o["id"])
        L.create_recharge(sess, 9, 1)
        L.do_exchange(sess, 9, 3, 1)
        L.do_exchange(sess, 10, 3, 1)
        L.do_exchange(sess, 9, 4, 1)
        L.member_revoke_cards(sess, 10, 3, 1, "测试", BOSS)
        L.save_setting(sess, "ledger", {"ptCleared": 120, "ptOpening": 5})
        L.save_setting(sess, "content", {"gallery": {"title": "店铺相册", "items": [{"url": "a.png"}]}})
        sess.flush()
        self.assertEqual(sess.get(CardTpl, 3).stock, 9)

    def test_dry_run_changes_nothing(self, _lock):
        sess = make_session()
        self._dirty(sess)
        out = L.purge_test_data_keep_bosses(sess, BOSS, "", dry_run=True)
        self.assertTrue(out["dryRun"])
        self.assertEqual(out["stockBack"], {"桌游卡#3": 1})
        self.assertEqual({u["id"] for u in out["willDeleteUsers"]}, {5, 7, 9, 10})
        self.assertGreater(out["willDelete"]["orders"], 0)
        self.assertGreater(sess.query(Order).count(), 0)
        self.assertEqual(sess.get(CardTpl, 3).stock, 9)

    def test_requires_confirm(self, _lock):
        sess = make_session()
        with self.assertRaises(ValueError):
            L.purge_test_data_keep_bosses(sess, BOSS, "nope")

    def test_purge(self, _lock):
        sess = make_session()
        self._dirty(sess)
        out = L.purge_test_data_keep_bosses(sess, BOSS, L.PURGE_KEEP_BOSSES_CONFIRM)
        sess.flush()
        self.assertTrue(out["ok"])
        for m in (Order, Recharge, Card, AssetFlow):
            self.assertEqual(sess.query(m).count(), 0, m.__tablename__)
        self.assertEqual([u.id for u in sess.query(User).all()], [1])
        self.assertEqual([w.user_id for w in sess.query(Wallet).all()], [1])
        self.assertTrue(sess.get(Wallet, 1).flow_ready)
        self.assertEqual(sess.get(CardTpl, 3).stock, 10)
        self.assertEqual(sess.get(CardTpl, 4).stock, -1)
        self.assertEqual(sess.query(Product).count(), 1)
        self.assertEqual(L.setting(sess, "content")["gallery"]["items"], [{"url": "a.png"}])
        ledger = L.setting(sess, "ledger")
        self.assertEqual((ledger["ptCleared"], ledger["ptOpening"]), (0, 0))
        recon = L.pt_identity_check(sess)
        self.assertTrue(recon["ok"], recon)


if __name__ == "__main__":
    unittest.main()
