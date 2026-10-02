"""Week/month rank periods start at 12:00; MONTH shards are this month, not all-time."""
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
import settlement_job as SJ  # noqa: E402
from models import AssetFlow, Base, Card, CardTpl, Champ, GameRecord, SettleLog, Team, User, Wallet  # noqa: E402


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sess = sessionmaker(bind=engine)()
    sess.add_all([
        User(id=1, no="000001", nick="甲", role="CUSTOMER", status="ACTIVE", team_id=10),
        User(id=2, no="000002", nick="乙", role="CUSTOMER", status="ACTIVE", team_id=10),
        Wallet(user_id=1, shard_w=99, shard_t=200, point_av=0),
        Wallet(user_id=2, shard_w=1, shard_t=50, point_av=0),
        Team(id=10, name="飞行家", status="ACTIVE"),
        CardTpl(id=8, name="战队奖励卡", cat="OTHER", days=7),
        CardTpl(id=5, name="黄金奖励卡", cat="OTHER", days=7),
    ])
    L.save_setting(sess, "cfg", {
        "rankDim": "WEEK", "rankRange": 3, "teamReward": True, "teamCard": "8",
        "stack": True, "reqShard": True, "settleCap": 20,
        "prizeMap": {"1": "5"},
    })
    sess.flush()
    return sess


def add_shard(sess, uid, at, delta, typ="game", ref=None):
    sess.add(AssetFlow(
        uid=uid, asset="SHARD", ref=ref or f"{typ}-{uid}-{at}", typ=typ,
        title="碎片", amount=str(delta), delta=delta, at=at, sort_at=at,
    ))


def at(dt: datetime):
    return patch.object(L, "business_now", return_value=dt)


class PeriodStartTests(unittest.TestCase):
    def test_week_flips_monday_noon_not_midnight(self):
        monday_am = datetime(2026, 10, 5, 11, 0)
        monday_pm = datetime(2026, 10, 5, 12, 0)
        self.assertEqual(L.period_start("WEEK", monday_am), datetime(2026, 9, 28, 12, 0))
        self.assertEqual(L.period_start("WEEK", monday_pm), datetime(2026, 10, 5, 12, 0))
        self.assertEqual(L.previous_period_start("WEEK", monday_pm), datetime(2026, 9, 28, 12, 0))

    def test_month_flips_first_noon(self):
        first_am = datetime(2026, 10, 1, 11, 0)
        first_pm = datetime(2026, 10, 1, 12, 0)
        self.assertEqual(L.period_start("MONTH", first_am), datetime(2026, 9, 1, 12, 0))
        self.assertEqual(L.period_start("MONTH", first_pm), datetime(2026, 10, 1, 12, 0))
        self.assertEqual(L.previous_period_start("MONTH", first_pm), datetime(2026, 9, 1, 12, 0))


class ShardBoardPeriodTests(unittest.TestCase):
    def test_week_month_and_all_use_different_totals(self):
        sess = make_session()
        add_shard(sess, 1, "2026-09-10 15:00", 80, ref="old-1")
        add_shard(sess, 1, "2026-09-29 15:00", 10, ref="week-1")
        add_shard(sess, 1, "2026-10-02 15:00", 3, ref="month-1")
        add_shard(sess, 2, "2026-10-02 15:00", 20, ref="month-2")
        add_shard(sess, 1, "2026-10-05 13:00", -10, typ="weekly", ref="reset-1")
        sess.flush()

        with at(datetime(2026, 10, 6, 15, 0)):
            week = L.rank_rows(sess, "SHARD", "WEEK", "USER")
            month = L.rank_rows(sess, "SHARD", "MONTH", "USER")
            total = L.rank_rows(sess, "SHARD", "ALL", "USER")
            mine = L.shard_of(sess, 1)

        # WEEK 跟店员页一样看钱包本周；MONTH 才按本月流水
        self.assertEqual([(r["user"]["id"], r["v"]) for r in week], [(1, 99), (2, 1)])
        self.assertEqual([(r["user"]["id"], r["v"]) for r in month], [(2, 20), (1, 3)])
        self.assertEqual([(r["user"]["id"], r["v"]) for r in total], [(1, 200), (2, 50)])
        self.assertEqual(mine["w"], 99)
        self.assertEqual(mine["t"], 200)
        self.assertEqual(mine["dim"], "WEEK")

    def test_customer_rank_month_stays_historical(self):
        sess = make_session()
        self.assertEqual(L.customer_rank_dim(sess, "WEEK"), "WEEK")
        self.assertEqual(L.customer_rank_dim(sess, "MONTH"), "ALL")
        self.assertEqual(L.customer_rank_dim(sess, "ALL"), "ALL")
        L.save_setting(sess, "cfg", {**(L.setting(sess, "cfg") or {}), "rankDim": "MONTH"})
        self.assertEqual(L.customer_rank_dim(sess, "WEEK"), "MONTH")
        self.assertEqual(L.customer_rank_dim(sess, "MONTH"), "ALL")


class ChampPeriodTests(unittest.TestCase):
    def test_champion_week_uses_game_time_noon_boundary(self):
        sess = make_session()
        sess.add(GameRecord(id=1, pname="桌游", time="2026-10-05 11:00", players=[]))
        sess.add(GameRecord(id=2, pname="桌游", time="2026-10-05 13:00", players=[]))
        sess.add(Champ(uid=1, event="e", date="2026-10-05", n=2, team_id=10, team_name="飞行家", game_id=1))
        sess.add(Champ(uid=1, event="e", date="2026-10-05", n=2, team_id=10, team_name="飞行家", game_id=2))
        sess.flush()
        with at(datetime(2026, 10, 6, 15, 0)):
            week = L.rank_rows(sess, "CHAMPION", "WEEK", "USER")
        self.assertEqual(len(week), 1)
        self.assertEqual(week[0]["v"], 1)


class MonthSettlementTests(unittest.TestCase):
    def test_month_plan_ranks_month_shards_not_history(self):
        sess = make_session()
        L.save_setting(sess, "cfg", {
            "rankDim": "MONTH", "rankRange": 3, "teamReward": True, "teamCard": "8",
            "stack": True, "reqShard": True, "settleCap": 20, "prizeMap": {"1": "5"},
        })
        add_shard(sess, 1, "2026-08-01 15:00", 200, ref="old")
        add_shard(sess, 2, "2026-10-02 15:00", 15, ref="now")
        sess.flush()
        with at(datetime(2026, 10, 15, 15, 0)):
            plan = SJ.settlement_plan(sess)
        personal = [x for x in plan if x["type"].startswith("PERSONAL")]
        self.assertEqual(personal[0]["uid"], 2)
        self.assertEqual(personal[0]["sh"], 15)

    def test_auto_settle_month_uses_closed_period(self):
        sess = make_session()
        L.save_setting(sess, "cfg", {
            "rankDim": "MONTH", "rankRange": 3, "teamReward": True, "teamCard": "8",
            "stack": True, "reqShard": True, "settleCap": 20, "prizeMap": {"1": "5"},
        })
        add_shard(sess, 1, "2026-09-10 15:00", 12, ref="last-month")
        add_shard(sess, 2, "2026-10-02 13:00", 9, ref="this-month")
        sess.flush()
        with at(datetime(2026, 10, 1, 12, 5)):
            live = SJ.settlement_plan(sess, closed=False)
            closed = SJ.settlement_plan(sess, closed=True)
        live_p = [x for x in live if x["type"].startswith("PERSONAL")]
        closed_p = [x for x in closed if x["type"].startswith("PERSONAL")]
        self.assertEqual(live_p[0]["uid"], 2)
        self.assertEqual(closed_p[0]["uid"], 1)


class AutoWindowTests(unittest.TestCase):
    def test_week_auto_only_monday_noon(self):
        self.assertIsNone(SJ.pending_auto_week(datetime(2026, 10, 2, 15, 0)))
        self.assertIsNone(SJ.pending_auto_week(datetime(2026, 10, 5, 11, 0)))
        week = SJ.pending_auto_week(datetime(2026, 10, 5, 12, 0))
        self.assertEqual(SJ.week_key(week), "09-28~10-04")

    def test_month_auto_only_first_noon(self):
        self.assertIsNone(SJ.pending_auto_month(datetime(2026, 10, 2, 9, 0)))
        self.assertIsNone(SJ.pending_auto_month(datetime(2026, 10, 1, 11, 0)))
        month = SJ.pending_auto_month(datetime(2026, 10, 1, 12, 0))
        self.assertEqual(SJ.month_key(month), "2026-09")

    def test_ensure_settle_week_does_not_wipe_live_shards(self):
        sess = make_session()
        L.save_setting(sess, "settleWeek", {"start": "09-21", "end": "09-27"})
        sess.add(SettleLog(
            id=1, uid=1, week="09-21~09-27", type="PERSONAL_RANK1", sub="5",
            target="个人榜", nick="甲", sh=10, status="GRANTED",
        ))
        sess.flush()
        with at(datetime(2026, 10, 2, 15, 0)):
            SJ.ensure_settle_week_current(sess)
        self.assertEqual(sess.get(Wallet, 1).shard_w, 99)
        self.assertEqual(SJ.week_key(L.setting(sess, "settleWeek")), "09-28~10-04")

    def test_restore_friday_wipe_puts_week_shards_back_without_touching_total(self):
        sess = make_session()
        sess.get(Wallet, 1).shard_w = 0
        sess.get(Wallet, 1).shard_t = 2
        sess.get(Wallet, 2).shard_w = 0
        sess.add(SettleLog(
            id=1, uid=1, week="09-21~09-27", type="TEAM_CHAMPION", sub="8",
            target="飞行家战队", nick="甲", sh=2, status="GRANTED",
        ))
        add_shard(sess, 2, "2026-10-02 09:13", -15, typ="weekly", ref="shardw-2026-10-02")
        sess.flush()
        first = SJ.restore_false_friday_week_shards(sess)
        second = SJ.restore_false_friday_week_shards(sess)
        w1, w2 = sess.get(Wallet, 1), sess.get(Wallet, 2)
        self.assertEqual(w1.shard_w, 2)
        self.assertEqual(w1.shard_t, 2)
        self.assertEqual(w2.shard_w, 15)
        self.assertEqual(w2.shard_t, 50)
        self.assertFalse(first["skipped"])
        self.assertTrue(second["skipped"])
        self.assertEqual(len(first["restored"]), 2)

    def test_delete_friday_ghost_cards_removes_unused_pack_rows(self):
        sess = make_session()
        sess.add(Card(
            id=50, uid=1, tpl=7, no="KQTEST", src="SETTLE_REWARD",
            src_desc="09-21~09-27 · 个人榜", status="UNUSED",
        ))
        sess.add(SettleLog(
            id=9, uid=1, week="09-21~09-27", type="PERSONAL_RANK3", sub="7",
            target="个人榜", nick="甲", sh=15, status="GRANTED", card_id=50, desc="青铜奖励卡",
        ))
        sess.add(AssetFlow(
            uid=1, asset="CARD", ref="card-in-50", typ="card_in",
            title="卡券新增 · 青铜奖励卡", amount="+1 张", delta=1, at="2026-10-02 09:13",
        ))
        sess.flush()
        first = SJ.delete_false_friday_reward_cards(sess)
        second = SJ.delete_false_friday_reward_cards(sess)
        self.assertFalse(first["skipped"])
        self.assertTrue(second["skipped"])
        self.assertEqual(len(first["deleted"]), 1)
        self.assertIsNone(sess.get(Card, 50))
        self.assertEqual(sess.query(AssetFlow).filter_by(ref="card-in-50").count(), 0)
        self.assertEqual(sess.get(SettleLog, 9).status, "REVOKED")
        self.assertIsNone(sess.get(SettleLog, 9).card_id)


if __name__ == "__main__":
    unittest.main()
