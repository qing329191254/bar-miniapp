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
from models import AssetFlow, Base, CardTpl, Champ, GameRecord, Team, User, Wallet  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
