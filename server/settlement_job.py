"""Weekly settlement: plan, execute, auto-schedule, and week rollover."""
from __future__ import annotations

import threading
import time
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

import logic as L
from database import session_scope
from models import CardTpl, SettleLog, Team, User


def week_period(d: date) -> dict:
    """Monday–Sunday week containing date d (MM-DD labels)."""
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return {"start": monday.strftime("%m-%d"), "end": sunday.strftime("%m-%d")}


def week_key(period: dict) -> str:
    start, end = str(period.get("start") or ""), str(period.get("end") or "")
    return f"{start}~{end}" if start and end else ""


def parse_week_key(key: str) -> dict:
    if "~" not in key:
        return {}
    start, end = key.split("~", 1)
    return {"start": start, "end": end}


def period_end_date(period: dict, ref: date | None = None) -> date:
    ref = ref or L.business_today()
    m, d = map(int, str(period.get("end") or "01-01").split("-"))
    end = date(ref.year, m, d)
    if end > ref + timedelta(days=120):
        end = end.replace(year=end.year - 1)
    return end


def next_week_period(period: dict) -> dict:
    ref = period_end_date(period)
    return week_period(ref + timedelta(days=1))


def settlement_week(db: Session) -> str:
    period = L.setting(db, "settleWeek") or {}
    return week_key(period)


def resolve_display_week(db: Session) -> str:
    wk = settlement_week(db)
    if wk:
        return wk
    weeks = sorted({x.week for x in db.query(SettleLog).all() if x.week}, reverse=True)
    return weeks[0] if weeks else ""


def settlement_meta(db: Session, week: str) -> dict:
    return dict((L.setting(db, "settleMeta") or {}).get(week) or {})


def record_settle_meta(db: Session, week: str, executed_at: str, trigger: str, *, granted: int = 0, blocked: bool = False):
    meta = dict(L.setting(db, "settleMeta") or {})
    meta[week] = {"executedAt": executed_at, "trigger": trigger, "granted": granted, "blocked": blocked}
    L.save_setting(db, "settleMeta", meta)


def advance_settle_week_after_run(db: Session):
    L.save_setting(db, "settleWeek", week_period(L.business_today()))


def ensure_settle_week_current(db: Session):
    """After a settled week ends, roll settleWeek forward to the current calendar week."""
    period = L.setting(db, "settleWeek") or {}
    if not period.get("start"):
        L.save_setting(db, "settleWeek", week_period(L.business_today()))
        return
    wk = week_key(period)
    if not wk:
        return
    if db.query(SettleLog).filter(SettleLog.week == wk).count() and period_end_date(period) < L.business_today():
        advance_settle_week_after_run(db)


def pending_auto_week(now: datetime | None = None) -> dict | None:
    """Last complete Mon–Sun week ready for automatic settlement."""
    now = now or L.business_now()
    if now.weekday() == 6:
        return None
    if now.weekday() == 0 and now.hour < 4:
        return None
    last_sunday = now.date() - timedelta(days=1 if now.weekday() == 0 else now.weekday() + 1)
    return week_period(last_sunday)


def settlement_plan(db: Session) -> list[dict]:
    cfg = L.setting(db, "cfg") or {}
    dim = "MONTH" if cfg.get("rankDim") == "MONTH" else "WEEK"
    rank_range = max(1, int(cfg.get("rankRange") or 3))
    prize_map = cfg.get("prizeMap") or {}
    templates = {x.sub: x for x in db.query(CardTpl).filter(CardTpl.cat == "OTHER").all() if x.sub}
    rows: list[dict] = []
    seen: set[int] = set()

    if cfg.get("teamReward"):
        teams = L.rank_rows(db, "SHARD", dim, "TEAM")
        if teams:
            winner = teams[0]
            team = db.get(Team, int(winner["team"]["id"]))
            tm = templates.get(str(cfg.get("teamCard") or ""))
            if team and tm:
                members = db.query(User).filter(User.role == "CUSTOMER", User.status == "ACTIVE", User.team_id == team.id).all()
                for user in members:
                    shard = L.shard_of(db, user.id)["w" if dim == "WEEK" else "t"]
                    allowed = not cfg.get("reqShard") or shard > 0
                    rows.append({
                        "uid": user.id, "target": team.name, "nick": user.nick, "type": "TEAM_CHAMPION",
                        "sub": tm.sub, "desc": tm.name, "sh": shard, "eligible": allowed,
                        "reason": "" if allowed else "本周期无碎片",
                    })
                    if allowed:
                        seen.add(user.id)

    for ranked in L.rank_rows(db, "SHARD", dim, "USER"):
        rank = int(ranked.get("rank") or 0)
        if rank > rank_range:
            continue
        user_data = ranked.get("user") or {}
        uid = int(user_data.get("id") or 0)
        tm = templates.get(str(prize_map.get(str(rank)) or ""))
        if not uid or not tm:
            continue
        allowed = bool(cfg.get("stack", True)) or uid not in seen
        rows.append({
            "uid": uid, "target": "个人榜", "nick": user_data.get("nick") or "",
            "type": f"PERSONAL_RANK{rank}", "sub": tm.sub, "desc": tm.name,
            "sh": int(ranked.get("v") or 0), "rank": rank, "eligible": allowed,
            "reason": "" if allowed else "规则不允许叠加",
        })
        if allowed:
            seen.add(uid)
    return rows


def run_settlement(db: Session, week: str | None = None, admin: dict | None = None, trigger: str = "manual") -> dict:
    week = week or settlement_week(db)
    if not week:
        return {"ok": False, "message": "未配置结算周期"}

    existing = db.query(SettleLog).filter(SettleLog.week == week).count()
    if existing:
        L.log(db, "SETTLE_RERUN", f"重跑 {week} · 幂等跳过，未重复发放", None, admin)
        meta = settlement_meta(db, week)
        return {
            "ok": True, "skipped": True, "week": week,
            "message": "该周期已执行，本次幂等跳过，未重复发放",
            "executedAt": meta.get("executedAt"), "trigger": meta.get("trigger"),
        }

    plan = settlement_plan(db)
    eligible = [x for x in plan if x["eligible"]]
    cap = int((L.setting(db, "cfg") or {}).get("settleCap") or 20)
    executed_at = L.business_now().strftime("%m-%d %H:%M")

    if len(eligible) > cap:
        for item in plan:
            db.add(SettleLog(
                id=L.next_seq(db, "settle"), uid=item["uid"], week=week, type=item["type"], sub=item["sub"],
                target=item["target"], nick=item["nick"], sh=item["sh"],
                status="BLOCKED" if item["eligible"] else "SKIPPED", card_id=None,
                desc=item["desc"] if item["eligible"] else item["reason"],
            ))
        L.log(db, "SETTLE_BLOCKED", f"{week} · 计划 {len(eligible)} 张超过单次上限 {cap} 张 · 整批拦截", None, admin)
        record_settle_meta(db, week, executed_at, trigger, granted=0, blocked=True)
        return {
            "ok": True, "blocked": True, "week": week, "executedAt": executed_at, "trigger": trigger,
            "message": f"计划发放 {len(eligible)} 张超过单次上限 {cap} 张，已整批拦截，一张未发",
        }

    granted = 0
    for item in plan:
        card_id = None
        status = "SKIPPED"
        desc = item["reason"] or item["desc"]
        if item["eligible"]:
            tm = db.query(CardTpl).filter(CardTpl.sub == item["sub"]).first()
            if tm:
                card = L.issue_card(db, item["uid"], tm, "SETTLE_REWARD", f"{week} · {item['target']}")
                card_id, status, desc = card.id, "GRANTED", tm.name
                granted += 1
        db.add(SettleLog(
            id=L.next_seq(db, "settle"), uid=item["uid"], week=week, type=item["type"], sub=item["sub"],
            target=item["target"], nick=item["nick"], sh=item["sh"], status=status,
            card_id=card_id, desc=desc,
        ))

    op = admin or {"role": "BOSS", "nick": "系统自动"}
    L.log(db, "SETTLE_RUN", f"执行 {week} · 发放 {granted} 张 · {trigger}", None, op)
    record_settle_meta(db, week, executed_at, trigger, granted=granted, blocked=False)
    return {
        "ok": True, "skipped": False, "week": week, "executedAt": executed_at, "trigger": trigger,
        "message": f"结算完成，共发放 {granted} 张奖励",
    }


def tick_settlement(db: Session):
    ensure_settle_week_current(db)
    target = pending_auto_week()
    if not target:
        return
    week = week_key(target)
    auto_last = L.setting(db, "settleAutoLast") or {}
    if auto_last.get("week") == week:
        return
    result = run_settlement(db, week=week, admin=None, trigger="auto")
    if result.get("ok"):
        L.save_setting(db, "settleAutoLast", {"week": week, "date": L.today_str()})
        advance_settle_week_after_run(db)
        print(f"[settlement] auto {week}: {result.get('message')}")


def settlement_scheduler_loop():
    time.sleep(15)
    while True:
        try:
            with session_scope() as db:
                tick_settlement(db)
        except Exception as exc:
            print(f"[settlement] scheduler error: {exc}")
        time.sleep(60)


def start_settlement_scheduler():
    threading.Thread(target=settlement_scheduler_loop, name="settlement-scheduler", daemon=True).start()


def bootstrap_settlement(db: Session):
    ensure_settle_week_current(db)
    tick_settlement(db)
