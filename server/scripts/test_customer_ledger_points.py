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
    def test_parse_point_adjust_detail(self):
        amount, process, remark = L._parse_point_adjust_detail(
            "快速调整 天才儿童 积分 -300 · 可用 40300→40000 · 原因：测备注"
        )
        self.assertEqual(amount, "-300")
        self.assertEqual(process, "40,300→40,000")
        self.assertEqual(remark, "测备注")

    def test_sign_and_game_points_appear_in_point_ledger(self):
        sign = SimpleNamespace(id=11, uid=9, month="2026-09", day=28, pts=100, extra_pts=50)
        game = SimpleNamespace(
            id=77, pname="德扑", table="A1", round="", time="2026-09-28 21:00",
            op="店员小王", status=None,
            players=[{"uid": 9, "pts": 300, "sh": 1}],
        )
        adjust = SimpleNamespace(
            id=3, uid=9, action="POINT_ADJUST", t="09-28 23:27", op="老板",
            detail="快速调整 天才儿童 积分 +300 · 可用 40000→40300 · 原因：补发",
        )

        def query_side(model):
            q = MagicMock()
            name = getattr(model, "__name__", "")
            if model is L.Withdrawal or name == "Withdrawal":
                q.filter_by.return_value.order_by.return_value.limit.return_value = []
            elif model is L.OpLog or name == "OpLog":
                q.filter.return_value.order_by.return_value.limit.return_value = [adjust]
            elif model is L.Card or name == "Card":
                q.filter_by.return_value.order_by.return_value.limit.return_value = []
            elif model is L.SignRecord or name == "SignRecord":
                q.filter_by.return_value.all.return_value = [sign]
                q.filter_by.return_value.order_by.return_value.limit.return_value = [sign]
            elif model is L.GameRecord or name == "GameRecord":
                q.order_by.return_value.limit.return_value = [game]
            elif model is L.SignRule or name == "SignRule":
                q.all.return_value = []
            elif model is L.PointLog:
                q.filter.return_value.order_by.return_value.limit.return_value = [
                    SimpleNamespace(ref="sign-11", before=0, after=150, at="2026-09-28 09:15"),
                    SimpleNamespace(ref="game-pts-77", before=150, after=450, at="2026-09-28 21:00"),
                    SimpleNamespace(id=99, ref="clear-2026-09-01", before=2000, after=0, at="2026-09-01 13:00"),
                ]
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
        self.assertIn("对局积分", titles)
        self.assertIn("店员调整积分", titles)

        sign_row = next(x for x in items if x["title"] == "签到积分")
        self.assertEqual(sign_row["amount"], "+150")
        self.assertEqual(sign_row["operator"], "系统")
        self.assertEqual(sign_row["process"], "0→150")
        self.assertEqual(sign_row["at"], "2026-09-28 09:15")

        game_row = next(x for x in items if x["title"] == "对局积分")
        self.assertEqual(game_row["amount"], "+300")
        self.assertEqual(game_row["process"], "150→450")

        clear_row = next(x for x in items if x["title"] == "积分月清零")
        self.assertEqual(clear_row["amount"], "−2,000")
        self.assertEqual(clear_row["process"], "2,000→0")
        self.assertEqual(clear_row["operator"], "系统")
        self.assertEqual(game_row["operator"], "店员小王")
        self.assertIn("德扑", game_row["content"])

        adj = next(x for x in items if x["title"] == "店员调整积分")
        self.assertEqual(adj["amount"], "+300")
        self.assertEqual(adj["process"], "40,000→40,300")
        self.assertEqual(adj["content"], "补发")
        self.assertEqual(adj["operator"], "老板")
        self.assertTrue(adj["at"].startswith("20"))

    def test_card_ledger_fields(self):
        def card(**kw):
            base = dict(uid=9, expire="", void_reason=None, at="", op="", done_at="", done_op="")
            base.update(kw)
            return SimpleNamespace(**base)

        combo = card(id=24, tpl=1, no="KQ614", src="ORDER_COMBO", src_desc="套餐自动发放 · DD260928158026",
                     status="UNUSED")
        legacy_grant = card(id=23, tpl=2, no="KQ427", src="MANUAL_GRANT", src_desc="店员补发 · 09-28",
                            status="UNUSED")
        used = card(id=22, tpl=1, no="KQ333", src="EXCHANGE", src_desc="积分兑换", status="USED",
                    at="2026-09-29 14:30")
        voided = card(id=20, tpl=2, no="KQ222", src="GAME_GIFT", src_desc="对局赠送 · 德州扑克 #124",
                      status="VOID", void_reason="对局作废 · 测试",
                      done_at="2026-09-29 15:00", done_op="老板")
        game = SimpleNamespace(id=124, time="2026-09-28 21:00", op="店员小王")
        order = SimpleNamespace(no="DD260928158026", at="2026-09-28 18:02")
        grant_log = SimpleNamespace(t="09-28 23:10", op="老板", detail="快速补发 天才儿童 · 酒水小食卡 ×5")
        verify = SimpleNamespace(card_no="KQ333", at="2026-09-29 16:05", op_uid=5)
        tpls = {1: SimpleNamespace(name="游戏卡"), 2: SimpleNamespace(name="酒水小食卡")}

        def query_side(model):
            q = MagicMock()
            if model is L.Card:
                q.filter_by.return_value.order_by.return_value.limit.return_value = [combo, legacy_grant, used, voided]
            elif model is L.Order:
                q.filter.return_value.first.return_value = order
            elif model is L.VerifyLog:
                q.filter.return_value.all.return_value = [verify]
            elif model is L.OpLog:
                q.filter.return_value.all.return_value = [grant_log]
            return q

        def get_side(model, pk):
            if model is L.GameRecord and pk == 124:
                return game
            if model is L.User and pk == 5:
                return SimpleNamespace(nick="店员小李")
            return None

        sess = MagicMock()
        sess.query.side_effect = query_side
        sess.get.side_effect = get_side

        with patch.object(L, "tpl", side_effect=lambda _s, tid: tpls.get(tid)):
            items = L.customer_ledger(sess, uid=9, kind="CARD", limit=80)
        by_id = {x["id"]: x for x in items}

        c = by_id["card-24"]
        self.assertEqual(c["form"], "套餐自动发放")
        self.assertEqual(c["content"], "订单 DD260928158026")
        self.assertEqual(c["at"], "2026-09-28 18:02")
        self.assertEqual(c["cardNo"], "KQ614")
        self.assertEqual(c["doneAt"], "")

        g = by_id["card-23"]
        self.assertEqual(g["form"], "店员补发")
        self.assertEqual(g["content"], "")
        self.assertTrue(g["at"].endswith("09-28 23:10"))

        u = by_id["card-22"]
        self.assertEqual(u["doneLabel"], "核销")
        self.assertEqual(u["doneAt"], "2026-09-29 16:05")
        self.assertEqual(u["operator"], "店员小李")

        v = by_id["card-20"]
        self.assertEqual(v["form"], "对局赠送")
        self.assertEqual(v["content"], "德州扑克 #124；对局作废 · 测试")
        self.assertEqual(v["at"], "2026-09-28 21:00")
        self.assertEqual(v["doneLabel"], "作废")
        self.assertEqual(v["doneAt"], "2026-09-29 15:00")
        self.assertEqual(v["operator"], "老板")

    def test_coin_ledger_fields(self):
        order = SimpleNamespace(
            id=5, no="DD1", uid=9, items=[{"name": "可乐", "qty": 2}], pay_type="COIN", status="FINISHED",
            table_name="A1", total=30, at="2026-09-29 12:00", ago="", accepted_by=7, op_uid=7, cancel_reason=None,
        )
        order.to_dict = lambda: {"id": 5, "status": "FINISHED"}
        recharge = SimpleNamespace(
            id=6, no="CZ1", uid=9, amount=100, bonus=20, status="PAID", at="2026-09-29 10:00",
            created="", reject_remark=None, op_uid=7,
        )
        boss_adj = SimpleNamespace(
            id=8, t="09-29 13:00", op="张老板", action="COIN_ADJUST",
            detail="调整 天才儿童 金币 +1000 · 余额 120→1120 · 原因：活动",
        )
        logs = [
            SimpleNamespace(ref="rc-6", before=0, after=120, at=""),
            SimpleNamespace(ref="ord-5", before=1120, after=1090, at=""),
        ]

        def query_side(model):
            q = MagicMock()
            if model is L.Order:
                q.filter_by.return_value.order_by.return_value.limit.return_value = [order]
            elif model is L.Recharge:
                q.filter_by.return_value.order_by.return_value.limit.return_value = [recharge]
            elif model is L.CoinAdjust:
                q.filter_by.return_value.order_by.return_value.limit.return_value = []
            elif model is L.OpLog:
                q.filter.return_value.order_by.return_value.limit.return_value = [boss_adj]
            elif model is L.PointLog:
                q.filter.return_value.order_by.return_value.limit.return_value = logs
            return q

        sess = MagicMock()
        sess.query.side_effect = query_side
        sess.get.side_effect = lambda model, pk: SimpleNamespace(nick="店员小李") if model is L.User and pk == 7 else None
        items = {x["id"]: x for x in L.customer_ledger(sess, uid=9, kind="COIN", limit=80)}

        o = items["ord-5"]
        self.assertEqual(o["amount"], "−30")
        self.assertEqual(o["process"], "1,120→1,090")
        self.assertEqual(o["operator"], "店员小李")
        self.assertIn("金币支付", o["content"])
        r = items["rc-6"]
        self.assertEqual(r["amount"], "+120")
        self.assertEqual(r["process"], "0→120")
        a = items["clog-8"]
        self.assertEqual(a["amount"], "+1,000")
        self.assertEqual(a["process"], "120→1,120")
        self.assertEqual(a["content"], "活动")
        self.assertEqual(a["operator"], "张老板")

    def test_do_sign_writes_point_log(self):
        wallet = SimpleNamespace(point_av=0, point_wg=0, point_mg=0, point_pd=0, sign_streak=0)
        sess = MagicMock()
        sess.query.return_value.filter_by.return_value.first.return_value = None
        sess.query.return_value.all.return_value = []
        added = []
        sess.add.side_effect = added.append

        def flush():
            for obj in added:
                if isinstance(obj, L.SignRecord) and not obj.id:
                    obj.id = 31

        sess.flush.side_effect = flush
        with patch.object(L, "setting", return_value={"signPoints": 1000}), \
                patch.object(L, "wallet_of", return_value=wallet):
            L.do_sign(sess, 9)

        logs = [x for x in added if isinstance(x, L.PointLog)]
        self.assertEqual(len(logs), 1)
        self.assertEqual((logs[0].ref, logs[0].before, logs[0].after), ("sign-31", 0, 1000))

    def test_close_card_records_time_and_operator(self):
        c = SimpleNamespace(status="UNUSED", void_reason=None, done_at="", done_op="")
        L.close_card(c, "VOID", {"nick": "店长A"}, "手动扣减 · 测试")
        self.assertEqual(c.status, "VOID")
        self.assertEqual(c.void_reason, "手动扣减 · 测试")
        self.assertEqual(c.done_op, "店长A")
        self.assertRegex(c.done_at, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

    def test_streak_ending_on(self):
        signed = {date(2026, 9, 26), date(2026, 9, 27), date(2026, 9, 28)}
        self.assertEqual(L._streak_ending_on(signed, date(2026, 9, 28)), 3)
        self.assertEqual(L._streak_ending_on(signed, date(2026, 9, 26)), 1)


if __name__ == "__main__":
    unittest.main()
