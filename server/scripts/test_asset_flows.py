"""End-to-end checks on a real (SQLite) database: every asset change writes a complete asset_flows row."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import logic as L  # noqa: E402
from models import (  # noqa: E402
    AssetFlow, Base, CardTpl, Order, PointLog, Product, Project, Recharge, TableSeat, Tier, User, Wallet,
    Withdrawal,
)

TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
STAFF = {"id": 7, "nick": "店员小李", "role": "STAFF"}
MANAGER = {"id": 5, "nick": "店长A", "role": "MANAGER"}
BOSS = {"id": 1, "nick": "张老板", "role": "BOSS"}


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sess = sessionmaker(bind=engine)()
    sess.add_all([
        User(id=1, no="B1", nick="张老板", role="BOSS"),
        User(id=5, no="M5", nick="店长A", role="MANAGER"),
        User(id=7, no="S7", nick="店员小李", role="STAFF"),
        User(id=9, no="000009", nick="天才儿童", role="CUSTOMER", tail="9366"),
        User(id=10, no="000010", nick="老会员", role="CUSTOMER", tail="1234"),
        Wallet(user_id=9, coin_p=500, point_av=1000, flow_ready=False),
        Wallet(user_id=10, coin_p=300, point_av=800, point_fz=100, flow_ready=False),
        Product(id=1, name="可乐", price=30),
        TableSeat(id=1, name="A1"),
        CardTpl(id=3, name="桌游卡", cat="GAME", cost=100),
        Tier(id=1, amount=100, bonus=20),
        Project(id=1, name="德州扑克"),
    ])
    L.save_setting(sess, "config", {"signPoints": 100})
    sess.flush()
    return sess


def ledger(sess, uid, kind="ALL"):
    return {row["id"]: row for row in L.customer_ledger(sess, uid, kind=kind, limit=200)}


@patch.object(L.cache, "lock_pending", return_value=True)
class AssetFlowTests(unittest.TestCase):
    def test_every_operation_writes_complete_rows(self, _lock):
        sess = make_session()
        uid = 9
        L.do_sign(sess, uid)

        coin_order = L.create_order(sess, uid, [{"pid": 1, "qty": 1}], "COIN", 1, "")
        L.accept_order(sess, coin_order["id"], STAFF)
        L.finish_order(sess, coin_order["id"])
        L.refund_order(sess, coin_order["id"], "做错了", BOSS)

        cancelled = L.create_order(sess, uid, [{"pid": 1, "qty": 1}], "OFFLINE", 1, "")
        L.cancel_order(sess, uid, cancelled["id"])
        rejected = L.create_order(sess, uid, [{"pid": 1, "qty": 1}], "COIN", 1, "")
        L.reject_order(sess, rejected["id"], "售罄", STAFF)
        offline = L.create_order(sess, uid, [{"pid": 1, "qty": 2}], "OFFLINE", 1, "")
        L.confirm_pay_order(sess, offline["id"], STAFF)
        L.accept_order(sess, offline["id"], STAFF)
        pending = L.create_order(sess, uid, [{"pid": 1, "qty": 1}], "COIN", 1, "")

        rc = L.create_recharge(sess, uid, 1)
        L.confirm_recharge(sess, rc["id"], STAFF)
        rc2 = L.create_recharge(sess, uid, 1)
        L.reject_recharge(sess, rc2["id"], "未收到款", STAFF)
        rc3 = L.create_recharge(sess, uid, 1)
        sess.get(Recharge, rc3["id"]).expire_at = 1
        L.expire_timeouts(sess)

        w1 = L.create_withdraw(sess, uid, 200)
        L.confirm_withdraw(sess, w1["id"], STAFF)
        w2 = L.create_withdraw(sess, uid, 100)
        L.reject_withdraw(sess, w2["id"], "信息不符", STAFF)
        w3 = L.create_withdraw(sess, uid, 50)
        L.cancel_withdraw(sess, uid)

        L.do_exchange(sess, uid, 3, 2)
        cards = sorted(c.id for c in sess.query(L.Card).filter_by(uid=uid).all())
        L.staff_direct_verify(sess, uid, cards[0], "9366", "", STAFF)
        L.member_revoke_cards(sess, uid, 3, 1, "测试扣减", MANAGER)
        L.member_grant_cards(sess, uid, 3, 1, "补发", MANAGER)

        game = L.submit_game(sess, STAFF, 1, 1, [{"uid": uid, "pts": 300, "sh": 2}], [], "")
        gid = game["id"] if "id" in game else sess.query(L.GameRecord).first().id
        L.void_game(sess, gid, "录错了", False, BOSS)

        L.member_adjust_point(sess, uid, 50, "补偿", BOSS)
        L.member_adjust_shard(sess, uid, 1, "补碎片", BOSS)
        L.member_adjust_coin(sess, uid, 100, "活动奖励", BOSS)
        L.member_adjust_coin(sess, uid, 10, "申请加币", MANAGER)
        L.member_adjust_coin(sess, uid, 20, "再申请", MANAGER)
        adjusts = sorted(a.id for a in sess.query(L.CoinAdjust).all())
        L.approve_coin_adjust(sess, adjusts[0], "approve", BOSS)
        L.approve_coin_adjust(sess, adjusts[1], "reject", BOSS, "不合理")
        sess.flush()

        rows = ledger(sess, uid)
        for rid, row in rows.items():
            with self.subTest(row=rid):
                self.assertRegex(row["at"], TIME_RE)
                self.assertTrue(row["operator"], "operator missing")
                self.assertTrue(row["content"], "content missing")
                self.assertTrue(row["amount"], "amount missing")
                if row["kind"] == "card":
                    self.assertTrue(row["cardNo"], "card number missing")
                else:
                    self.assertTrue(row["process"], "balance missing")

        def one(prefix, **match):
            hits = [r for k, r in rows.items() if k.startswith(prefix)
                    and all(r.get(f) == v for f, v in match.items())]
            self.assertTrue(hits, f"no row {prefix} {match}")
            return hits[0]

        self.assertEqual(rows[f"ord-{coin_order['id']}"]["process"], "500→470")
        self.assertEqual(rows[f"ord-{coin_order['id']}"]["status"], "已退款")
        self.assertEqual(rows[f"ord-{coin_order['id']}"]["operator"], "店员小李")
        self.assertEqual(one("refund-", operator="张老板")["process"], "470→500")
        self.assertEqual(rows[f"ord-{cancelled['id']}"]["operator"], "本人")
        self.assertIn("顾客取消", rows[f"ord-{cancelled['id']}"]["content"])
        self.assertEqual(rows[f"ord-{rejected['id']}"]["operator"], "店员小李")
        self.assertEqual(rows[f"ord-{offline['id']}"]["process"], L.NO_BALANCE_CHANGE)
        self.assertEqual(rows[f"ord-{pending['id']}"]["operator"], "本人")
        self.assertEqual(rows[f"ord-{pending['id']}"]["order"]["status"], "PENDING_ACCEPT")
        self.assertEqual(rows[f"rc-{rc['id']}"]["amount"], "+120")
        self.assertEqual(rows[f"rc-{rc2['id']}"]["operator"], "店员小李")
        self.assertEqual(rows[f"rc-{rc3['id']}"]["operator"], "系统")
        self.assertEqual(rows[f"wdr-{w1['id']}"]["operator"], "店员小李")
        self.assertEqual(rows[f"wdr-back-{w2['id']}"]["amount"], "+100")
        self.assertEqual(rows[f"wdr-back-{w3['id']}"]["operator"], "本人")
        self.assertEqual(one("card-out-", status="已核销")["operator"], "店员小李")
        self.assertEqual(one("card-out-", status="已作废")["operator"], "店长A")
        self.assertEqual(one("card-in-", operator="店长A")["title"], "卡券新增 · 桌游卡")
        self.assertEqual(rows[f"game-void-{gid}"]["operator"], "张老板")
        self.assertEqual(rows[f"game-pts-{gid}"]["status"], "已作废")
        self.assertEqual(one("cadj-", status="已生效")["operator"], "店长A")
        self.assertEqual(one("cadj-", status="已驳回")["process"], L.NO_BALANCE_CHANGE)

        # balance chain is continuous on both tabs (each row starts where the previous one ended)
        for kind, first in (("POINT", "1,000"), ("COIN", "500")):
            chain = [r for r in L.customer_ledger(sess, uid, kind=kind, limit=200) if "→" in r["process"]]
            self.assertEqual(chain[-1]["process"].split("→")[0], first)
            for newer, older in zip(chain, chain[1:]):
                self.assertEqual(newer["process"].split("→")[0], older["process"].split("→")[1],
                                 f"{kind}: {older['id']} -> {newer['id']}")

        shards = L.shard_records(sess, uid)
        keys = {r["key"] for r in shards}
        self.assertIn(f"game-{gid}", keys)
        self.assertIn(f"void-{gid}", keys)
        self.assertTrue(any(k.startswith("adj-") for k in keys))
        for r in shards:
            self.assertTrue(r["meta"])
            self.assertTrue(r["op"])

    def test_history_copied_once_before_first_new_row(self, _lock):
        sess = make_session()
        sess.add(Order(
            id=50, no="DD50", uid=10, items=[{"name": "雪碧", "qty": 1}], total=20, pay_type="COIN",
            status="FINISHED", table_name="A1", at="2026-09-01 12:00", accepted_by=7, op_uid=7,
            paid_principal=20, paid_bonus=0,
        ))
        sess.add(PointLog(uid=10, ref="ord-50", before=320, after=300, at="2026-09-01 12:00"))
        sess.add(Withdrawal(
            id=60, no="TF60", uid=10, pts=100, status="PENDING_CONFIRM", created="09-01 13:00",
            at="2026-09-01 13:00",
        ))
        sess.add(PointLog(uid=10, ref="wdr-60", before=900, after=800, at="2026-09-01 13:00"))
        sess.flush()

        L.confirm_withdraw(sess, 60, STAFF)
        sess.flush()
        rows = ledger(sess, 10)
        self.assertEqual(rows["ord-50"]["process"], "320→300")
        self.assertEqual(rows["ord-50"]["operator"], "店员小李")
        self.assertEqual(rows["wdr-60"]["process"], "900→800")
        self.assertEqual(rows["wdr-60"]["operator"], "店员小李")
        self.assertEqual(rows["wdr-60"]["status"], "已发放")
        self.assertTrue(sess.get(Wallet, 10).flow_ready)

        count = sess.query(AssetFlow).filter_by(uid=10).count()
        L.customer_ledger(sess, 10)
        self.assertEqual(sess.query(AssetFlow).filter_by(uid=10).count(), count)

    def test_member_ledger_covers_coin_point_card_and_shard(self, _lock):
        sess = make_session()
        uid = 9
        L.do_sign(sess, uid)
        rc = L.create_recharge(sess, uid, 1)
        L.confirm_recharge(sess, rc["id"], STAFF)
        game = L.submit_game(sess, STAFF, 1, 1, [{"uid": uid, "pts": 300, "sh": 2}], [], "")
        L.member_grant_cards(sess, uid, 3, 1, "补发", MANAGER)
        L.member_adjust_shard(sess, uid, 1, "补碎片", BOSS)
        sess.flush()

        all_rows = L.member_ledger_page(sess, uid, "all", 1, 200)["items"]
        kinds = {r["kind"] for r in all_rows}
        self.assertEqual(kinds, {"coin", "point", "card", "shard"})
        shard = [r for r in all_rows if r["kind"] == "shard"]
        self.assertTrue(all(r["amount"] and r["operator"] and r["at"] for r in shard))
        adj = next(r for r in shard if r["id"].startswith("adj-"))
        self.assertEqual(adj["operator"], "张老板")
        self.assertIn("补碎片", adj["content"])
        self.assertFalse(adj["content"].startswith("20"))

        only_shard = L.member_ledger_page(sess, uid, "shard", 1, 200)["items"]
        self.assertTrue(only_shard and all(r["kind"] == "shard" for r in only_shard))
        last_page = (len(all_rows) + 1) // 2
        pages = [L.member_ledger_page(sess, uid, "all", p, 2) for p in range(1, last_page + 1)]
        self.assertTrue(all(pg["total"] == len(all_rows) for pg in pages))
        self.assertEqual([r["id"] for pg in pages for r in pg["items"]], [r["id"] for r in all_rows])
        self.assertEqual(L.member_ledger_page(sess, uid, "all", 999, 2)["page"], last_page)
        self.assertTrue(game)

        with self.assertRaises(ValueError):
            L.member_ledger_page(sess, 7, "all", 1, 10)

    def test_game_detail_lists_players_cards_and_void_info(self, _lock):
        sess = make_session()
        game = L.submit_game(
            sess, STAFF, 1, 1,
            [{"uid": 9, "pts": 300, "sh": 2, "cards": [{"tpl": 3, "qty": 2}]}, {"uid": 10, "pts": 100, "sh": 1}],
            [9], "周赛", "第3局",
        )
        gid = game["id"]
        sess.flush()

        d = L.game_detail(sess, gid)
        self.assertEqual((d["pname"], d["table"], d["round"], d["op"]), ("德州扑克", "A1", "第3局", "店员小李"))
        self.assertEqual((d["totalPts"], d["totalSh"], d["totalCards"], d["winners"]), (400, 3, 2, 1))
        p9, p10 = d["players"]
        self.assertEqual((p9["nick"], p9["no"], p9["win"], p9["event"]), ("天才儿童", "000009", True, "周赛"))
        self.assertEqual([c["statusText"] for c in p9["cards"]], ["未使用", "未使用"])
        self.assertTrue(all(c["no"] and c["name"] == "桌游卡" for c in p9["cards"]))
        self.assertFalse(p10["win"])
        self.assertEqual(p10["cards"], [])
        self.assertNotIn("void", d)

        L.void_game(sess, gid, "玩家身份录错", False, BOSS)
        sess.flush()
        d = L.game_detail(sess, gid)
        self.assertEqual(d["status"], "VOID")
        self.assertEqual(d["void"]["op"], "张老板")
        self.assertEqual(d["void"]["reason"], "玩家身份录错")
        self.assertEqual([c["statusText"] for c in d["players"][0]["cards"]], ["已作废", "已作废"])

        with self.assertRaises(ValueError):
            L.game_detail(sess, 99999)

    def test_manual_coin_adjust_is_bonus_and_deducts_bonus_first(self, _lock):
        sess = make_session()
        w = sess.get(Wallet, 9)
        L.member_adjust_coin(sess, 9, 100, "活动奖励", BOSS)
        self.assertEqual((w.coin_p, w.coin_b), (500, 100))
        L.member_adjust_coin(sess, 9, -150, "加错了", BOSS)
        self.assertEqual((w.coin_p, w.coin_b), (450, 0))
        with self.assertRaises(ValueError):
            L.member_adjust_coin(sess, 9, -451, "超额", BOSS)

        L.member_adjust_coin(sess, 9, 30, "申请加币", MANAGER)
        L.member_adjust_coin(sess, 9, -40, "申请扣币", MANAGER)
        adjusts = sorted(sess.query(L.CoinAdjust).all(), key=lambda a: a.id)
        self.assertEqual([a.type for a in adjusts], ["BONUS", "BONUS"])
        L.approve_coin_adjust(sess, adjusts[0].id, "approve", BOSS)
        self.assertEqual((w.coin_p, w.coin_b), (450, 30))
        L.approve_coin_adjust(sess, adjusts[1].id, "approve", BOSS)
        self.assertEqual((w.coin_p, w.coin_b), (440, 0))

    def test_reclassify_manual_coin_moves_net_manual_adds_to_bonus_once(self, _lock):
        sess = make_session()
        w9, w10 = sess.get(Wallet, 9), sess.get(Wallet, 10)
        w9.coin_p, w9.coin_b = 1501, 220
        for ref, delta in (("cdir-1", 222), ("cdir-2", 666)):
            sess.add(AssetFlow(uid=9, asset="COIN", ref=ref, typ="adjust", title="店员调整金币",
                               amount=f"+{delta}", delta=delta, at="2026-10-04 18:16", sort_at="2026-10-04 18:16"))
        sess.add(AssetFlow(uid=10, asset="COIN", ref="cdir-3", typ="adjust", title="店员调整金币",
                           amount="−452", delta=-452, at="2026-10-01 21:23", sort_at="2026-10-01 21:23"))
        sess.flush()

        first = L.reclassify_manual_coin_to_bonus(sess)
        second = L.reclassify_manual_coin_to_bonus(sess)
        self.assertEqual((w9.coin_p, w9.coin_b), (613, 1108))
        self.assertEqual((w10.coin_p, w10.coin_b), (300, 0))
        self.assertEqual([(m["uid"], m["amount"]) for m in first["moved"]], [(9, 888)])
        self.assertTrue(second["skipped"])
        self.assertEqual((w9.coin_p, w9.coin_b), (613, 1108))

    def test_games_page_filters_by_member_project_date_and_status(self, _lock):
        sess = make_session()
        sess.add(Project(id=2, name="狼人杀"))
        sess.flush()
        g1 = L.submit_game(sess, STAFF, 1, 1, [{"uid": 9, "pts": 10}], [], "", "", "2026-09-20 20:00")["id"]
        g2 = L.submit_game(sess, STAFF, 2, 1, [{"uid": 10, "pts": 10}], [], "", "", "2026-09-25 20:00")["id"]
        g3 = L.submit_game(sess, STAFF, 1, 1, [{"uid": 9, "pts": 0}, {"uid": 10, "pts": 0}], [], "", "",
                           "2026-09-26 21:00")["id"]
        L.void_game(sess, g3, "录错了", False, BOSS)
        sess.flush()

        def ids(**kw):
            return [g["id"] for g in L.games_page(sess, page_size=50, **kw)["items"]]

        self.assertEqual(ids(), [g3, g2, g1])
        self.assertEqual(ids(kw="天才"), [g3, g1])
        self.assertEqual(ids(kw="000010"), [g3, g2])
        self.assertEqual(ids(kw="1234"), [g3, g2])
        self.assertEqual(ids(pid=2), [g2])
        self.assertEqual(ids(status="VOID"), [g3])
        self.assertEqual(ids(status="LIVE"), [g2, g1])
        self.assertEqual(ids(preset="custom", date_from="2026-09-25", date_to="2026-09-26"), [g3, g2])
        self.assertEqual(ids(kw="天才", pid=1, status="LIVE"), [g1])
        page = L.games_page(sess, kw="天才", page=1, page_size=1)
        self.assertEqual((page["total"], page["totalAll"], len(page["items"])), (2, 3, 1))
        self.assertEqual({p["name"] for p in page["projects"]}, {"德州扑克", "狼人杀"})


if __name__ == "__main__":
    unittest.main()
