"""Rank settlement: plan, execute, auto-schedule, and week rollover.

Auto schedule (Asia/Shanghai):
- WEEK rankDim: Monday 12:00 — settle the period that just ended (previous Mon 12:00–this Mon 12:00), then reset week counters
- MONTH rankDim: 1st 12:00 — settle previous month (1st 12:00–this 1st 12:00)
Point clear runs separately at 1st 13:00 (see point_clear_job).
"""
from __future__ import annotations

import threading
import time
from datetime import date, datetime, timedelta

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

import logic as L
import cache
from database import session_scope
from models import AssetFlow, Card, CardTpl, OpLog, SettleLog, Team, User, Wallet


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
    """Prefer configured week when it has records; otherwise show the latest settled week."""
    configured = settlement_week(db)
    if configured and db.query(SettleLog).filter(SettleLog.week == configured).count():
        return configured
    weeks = sorted({x.week for x in db.query(SettleLog).all() if x.week}, reverse=True)
    if weeks:
        return weeks[0]
    return configured or ""


def settlement_meta(db: Session, week: str) -> dict:
    return dict((L.setting(db, "settleMeta") or {}).get(week) or {})


def record_settle_meta(db: Session, week: str, executed_at: str, trigger: str, *, granted: int = 0, blocked: bool = False):
    meta = dict(L.setting(db, "settleMeta") or {})
    meta[week] = {"executedAt": executed_at, "trigger": trigger, "granted": granted, "blocked": blocked}
    L.save_setting(db, "settleMeta", meta)


def advance_settle_week_after_run(db: Session):
    reset_weekly_rank_counters(db)
    L.save_setting(db, "settleWeek", week_period(L.business_today()))


def reset_weekly_rank_counters(db: Session) -> None:
    """Zero week shard/point counters after settlement so 本周榜 starts fresh."""
    day = L.business_today().isoformat()
    for w in db.query(Wallet).all():
        if int(w.shard_w or 0) > 0:
            L.flow_shard(
                db, w.user_id, f"shardw-{day}", typ="weekly", title="周榜结算 · 当周碎片清零",
                delta=-int(w.shard_w), op="系统", remark="历史累计不变", history=False,
            )
        w.shard_w = 0
        w.point_wg = 0


def ensure_settle_week_current(db: Session):
    """After a settled week ends, roll the display week forward. Do not touch live counters."""
    period = L.setting(db, "settleWeek") or {}
    if not period.get("start"):
        L.save_setting(db, "settleWeek", week_period(L.business_today()))
        return
    wk = week_key(period)
    if not wk:
        return
    if db.query(SettleLog).filter(SettleLog.week == wk).count() and period_end_date(period) < L.business_today():
        L.save_setting(db, "settleWeek", week_period(L.business_today()))


def pending_auto_week(now: datetime | None = None) -> dict | None:
    """Last complete Mon–Sun week, only on Monday at/after 12:00 Asia/Shanghai."""
    now = now or L.business_now()
    if now.weekday() != 0 or now.hour < L.SETTLE_HOUR:
        return None
    last_sunday = now.date() - timedelta(days=1)
    return week_period(last_sunday)


def month_period(d: date) -> dict:
    """Calendar month containing date d (MM-DD labels + year/month)."""
    first = d.replace(day=1)
    if first.month == 12:
        last = date(first.year, 12, 31)
    else:
        last = date(first.year, first.month + 1, 1) - timedelta(days=1)
    return {
        "start": first.strftime("%m-%d"),
        "end": last.strftime("%m-%d"),
        "year": first.year,
        "month": first.month,
    }


def month_key(period: dict) -> str:
    y, m = period.get("year"), period.get("month")
    if y and m:
        return f"{int(y)}-{int(m):02d}"
    start, end = str(period.get("start") or ""), str(period.get("end") or "")
    return f"{start}~{end}" if start and end else ""


def pending_auto_month(now: datetime | None = None) -> dict | None:
    """Previous calendar month, only on the 1st at/after 12:00 Asia/Shanghai."""
    now = now or L.business_now()
    if now.day != 1 or now.hour < L.SETTLE_HOUR:
        return None
    first_this = now.date().replace(day=1)
    last_prev = first_this - timedelta(days=1)
    return month_period(last_prev)


def settlement_plan(db: Session, *, closed: bool = False) -> list[dict]:
    cfg = L.normalize_settlement_cfg_refs(db, L.setting(db, "cfg") or {})
    dim = "MONTH" if cfg.get("rankDim") == "MONTH" else "WEEK"
    since = L.previous_period_start(dim) if closed else L.period_start(dim)
    if dim == "MONTH":
        period_shards = L.shard_gains_since(db, since)
    else:
        period_shards = {int(w.user_id): int(w.shard_w or 0) for w in db.query(Wallet).all()}
    rank_range = max(1, int(cfg.get("rankRange") or 3))
    prize_map = cfg.get("prizeMap") or {}
    rows: list[dict] = []
    seen: set[int] = set()

    if cfg.get("teamReward"):
        teams = L.rank_rows(db, "SHARD", dim, "TEAM", since=since)
        if teams:
            winner = teams[0]
            team = db.get(Team, int(winner["team"]["id"]))
            tm = L.resolve_reward_card_tpl(db, cfg.get("teamCard"))
            if team and tm:
                members = db.query(User).filter(User.role == "CUSTOMER", User.status == "ACTIVE", User.team_id == team.id).all()
                for user in members:
                    shard = int(period_shards.get(user.id, 0))
                    allowed = not cfg.get("reqShard") or shard > 0
                    rows.append({
                        "uid": user.id, "target": team.name, "nick": user.nick, "type": "TEAM_CHAMPION",
                        "tplId": tm.id, "sub": L.reward_tpl_ref(tm), "desc": tm.name, "sh": shard,
                        "eligible": allowed, "reason": "" if allowed else "本周期无碎片",
                    })
                    if allowed:
                        seen.add(user.id)

    for ranked in L.rank_rows(db, "SHARD", dim, "USER", since=since):
        rank = int(ranked.get("rank") or 0)
        if rank > rank_range:
            continue
        user_data = ranked.get("user") or {}
        uid = int(user_data.get("id") or 0)
        tm = L.resolve_reward_card_tpl(db, prize_map.get(str(rank)))
        if not uid or not tm:
            continue
        allowed = bool(cfg.get("stack", True)) or uid not in seen
        rows.append({
            "uid": uid, "target": "个人榜", "nick": user_data.get("nick") or "",
            "type": f"PERSONAL_RANK{rank}", "tplId": tm.id, "sub": L.reward_tpl_ref(tm), "desc": tm.name,
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

    # Cross-instance: claim week lock before counting / issuing cards.
    if not cache.idem_begin(db, f"settle:{week}", ttl=2 * 3600):
        return {
            "ok": True, "skipped": True, "week": week,
            "message": "结算正在执行或刚完成，本次跳过",
        }

    existing = db.query(SettleLog).filter(SettleLog.week == week).count()
    if existing:
        L.log(db, "SETTLE_RERUN", f"重跑 {week} · 幂等跳过，未重复发放", None, admin)
        meta = settlement_meta(db, week)
        return {
            "ok": True, "skipped": True, "week": week,
            "message": "该周期已执行，本次幂等跳过，未重复发放",
            "executedAt": meta.get("executedAt"), "trigger": meta.get("trigger"),
        }

    plan = settlement_plan(db, closed=trigger == "auto")
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
            tm = db.get(CardTpl, int(item["tplId"])) if item.get("tplId") else L.resolve_reward_card_tpl(db, item.get("sub"))
            if tm:
                card = L.issue_card(db, item["uid"], tm, "SETTLE_REWARD", f"{week} · {item['target']}", op="系统")
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
    cfg = L.setting(db, "cfg") or {}
    dim = "MONTH" if cfg.get("rankDim") == "MONTH" else "WEEK"
    if dim == "MONTH":
        target = pending_auto_month()
        if not target:
            return
        week = month_key(target)
    else:
        target = pending_auto_week()
        if not target:
            return
        week = week_key(target)
    if not week:
        return
    auto_last = L.setting(db, "settleAutoLast") or {}
    if auto_last.get("week") == week:
        return
    result = run_settlement(db, week=week, admin=None, trigger="auto")
    # Only advance after a real completed run (not lock-skip / already-done / blocked).
    if result.get("ok") and not result.get("skipped") and not result.get("blocked"):
        L.save_setting(db, "settleAutoLast", {"week": week, "date": L.today_str()})
        if dim == "WEEK":
            # Weekly counters reset after Monday noon settlement.
            advance_settle_week_after_run(db)
        print(f"[settlement] auto {week}: {result.get('message')}")
    elif result.get("ok"):
        print(f"[settlement] auto {week} not advanced: {result.get('message')}")


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


WEEK_SHARD_RESTORE_KEY = "wkFix1002"
WEEK_SHARD_RESTORE_DAY = "2026-10-02"
WEEK_SHARD_RESTORE_WEEK = "09-21~09-27"


def wiped_week_shard_amounts(db: Session) -> dict[int, int]:
    """Week counters cleared by the false Friday auto-settle on 2026-10-02."""
    amounts: dict[int, int] = {}
    flows = (
        db.query(AssetFlow)
        .filter(
            AssetFlow.asset == "SHARD",
            AssetFlow.typ == "weekly",
            AssetFlow.at.like(f"{WEEK_SHARD_RESTORE_DAY}%"),
        )
        .all()
    )
    for row in flows:
        delta = -int(row.delta or 0)
        if delta > 0:
            uid = int(row.uid)
            amounts[uid] = amounts.get(uid, 0) + delta
    for row in db.query(SettleLog).filter(SettleLog.week == WEEK_SHARD_RESTORE_WEEK).all():
        uid = int(row.uid)
        shard = int(row.sh or 0)
        if shard > 0:
            amounts[uid] = max(amounts.get(uid, 0), shard)
    return amounts


def restore_false_friday_week_shards(db: Session) -> dict:
    """Put this week's shard_w back without touching 累计. Idempotent."""
    prev = L.setting(db, WEEK_SHARD_RESTORE_KEY) or {}
    if prev.get("done"):
        return {"ok": True, "skipped": True, "restored": prev.get("restored") or []}
    restored: list[dict] = []
    admin = {"role": "BOSS", "nick": "系统"}
    for uid, amount in wiped_week_shard_amounts(db).items():
        if amount <= 0:
            continue
        ref = f"wkfix1002-{uid}"
        if db.query(AssetFlow).filter_by(uid=uid, asset="SHARD", ref=ref).first():
            continue
        wallet = L.wallet_of(db, uid)
        before = int(wallet.shard_w or 0)
        wallet.shard_w = before + amount
        user = db.get(User, uid)
        nick = user.nick if user else str(uid)
        L.flow_shard(
            db, uid, ref, typ="adjust", title="补回本周碎片",
            delta=amount, op="系统", remark="周五误清算，累计不变", history=False,
        )
        L.log(
            db, "SHARD_ADJUST",
            f"补回 {nick} 本周碎片 {before}→{wallet.shard_w} · 累计不变",
            uid, admin,
        )
        restored.append({"uid": uid, "nick": nick, "from": before, "to": int(wallet.shard_w)})
    L.save_setting(db, WEEK_SHARD_RESTORE_KEY, {"done": True, "restored": restored})
    return {"ok": True, "skipped": False, "restored": restored}


GHOST_CARD_DELETE_KEY = "ghostCardDel1002"
GHOST_SETTLE_WEEKS = ("2026-09", "09-21~09-27")


def delete_false_friday_reward_cards(db: Session) -> dict:
    """Remove unused reward cards from the Friday mis-issue. Keep settle rows as REVOKED."""
    prev = L.setting(db, GHOST_CARD_DELETE_KEY) or {}
    if prev.get("done"):
        return {
            "ok": True, "skipped": True,
            "deleted": prev.get("deleted") or [],
            "keptUsed": prev.get("keptUsed") or [],
        }
    deleted: list[dict] = []
    kept_used: list[dict] = []
    rows = (
        db.query(SettleLog)
        .filter(SettleLog.week.in_(GHOST_SETTLE_WEEKS), SettleLog.status == "GRANTED")
        .order_by(SettleLog.id)
        .all()
    )
    for row in rows:
        card = db.get(Card, int(row.card_id)) if row.card_id else None
        if card and card.status == "USED":
            kept_used.append({"id": int(card.id), "no": card.no, "nick": row.nick, "week": row.week})
            continue
        if card:
            db.query(AssetFlow).filter(
                AssetFlow.uid == card.uid,
                AssetFlow.asset == "CARD",
                AssetFlow.ref.in_([f"card-in-{card.id}", f"card-out-{card.id}"]),
            ).delete(synchronize_session=False)
            deleted.append({
                "uid": int(card.uid), "nick": row.nick, "no": card.no,
                "week": row.week, "desc": row.desc,
            })
            db.delete(card)
        row.card_id = None
        row.status = "REVOKED"
    L.log(
        db, "SETTLE_REVOKE",
        f"删除周五误发奖励卡 {len(deleted)} 张 · 已核销保留 {len(kept_used)} 张",
        None, {"role": "BOSS", "nick": "系统"},
    )
    payload = {"done": True, "deleted": deleted, "keptUsed": kept_used}
    L.save_setting(db, GHOST_CARD_DELETE_KEY, payload)
    db.flush()
    return {"ok": True, "skipped": False, **payload}


GHOST_SETTLE_PURGE_KEY = "ghostSettlePurge1002"


def purge_false_friday_settle_traces(db: Session) -> dict:
    """Drop every trace of the 2026-10-02 mis-settle once its cards are gone and shards restored.

    Shard flows are only removed in -N/+N pairs that net to zero, so balances never change.
    """
    prev = L.setting(db, GHOST_SETTLE_PURGE_KEY) or {}
    if prev.get("done"):
        return {"ok": True, "skipped": True, **{k: v for k, v in prev.items() if k != "done"}}
    if not (L.setting(db, GHOST_CARD_DELETE_KEY) or {}).get("done"):
        return {"ok": False, "skipped": True, "message": "奖励卡尚未删除"}

    settle_rows = db.query(SettleLog).filter(SettleLog.week.in_(GHOST_SETTLE_WEEKS))
    if settle_rows.filter(SettleLog.card_id.isnot(None)).count():
        return {"ok": False, "skipped": True, "message": "仍有关联奖励卡"}
    settle_n = settle_rows.delete(synchronize_session=False)

    meta = dict(L.setting(db, "settleMeta") or {})
    if any(meta.pop(w, None) is not None for w in list(GHOST_SETTLE_WEEKS)):
        L.save_setting(db, "settleMeta", meta)

    log_q = db.query(OpLog).filter(or_(
        *[and_(OpLog.action == "SETTLE_RUN", OpLog.detail.like(f"执行 {w} · %")) for w in GHOST_SETTLE_WEEKS],
        *[and_(OpLog.action == "SETTLE_RERUN", OpLog.detail.like(f"重跑 {w} · %")) for w in GHOST_SETTLE_WEEKS],
        and_(OpLog.action == "SETTLE_REVOKE", OpLog.detail.like("删除周五误发奖励卡%")),
        and_(OpLog.action == "SHARD_ADJUST", OpLog.op == "系统",
             OpLog.detail.like("补回 % 本周碎片 %→% · 累计不变")),
    ))
    log_n = log_q.delete(synchronize_session=False)

    wiped_ref = f"shardw-{WEEK_SHARD_RESTORE_DAY}"
    flow_n = 0
    wiped = db.query(AssetFlow).filter(AssetFlow.asset == "SHARD", AssetFlow.ref == wiped_ref).all()
    for row in wiped:
        back = db.query(AssetFlow).filter_by(uid=row.uid, asset="SHARD", ref=f"wkfix1002-{row.uid}").first()
        if not back or int(back.delta or 0) + int(row.delta or 0) != 0:
            continue
        db.delete(back)
        db.delete(row)
        flow_n += 2

    payload = {"done": True, "settleRows": settle_n, "logs": log_n, "shardFlows": flow_n}
    L.save_setting(db, GHOST_SETTLE_PURGE_KEY, payload)
    db.flush()
    return {"ok": True, "skipped": False, **{k: v for k, v in payload.items() if k != "done"}}


def bootstrap_settlement(db: Session):
    sync_demo_settle_settings(db)
    tick_settlement(db)
    restore_false_friday_week_shards(db)
    delete_false_friday_reward_cards(db)
    purge_false_friday_settle_traces(db)


def sync_demo_settle_settings(db: Session):
    """Keep demo settleWeek / settleMeta aligned with seed after restarts (local/demo only)."""
    from seed_db import SEED
    from settings import demo_starter_enabled

    if not demo_starter_enabled():
        if SEED.get("settleMeta") and not L.setting(db, "settleMeta"):
            L.save_setting(db, "settleMeta", SEED["settleMeta"])
        return

    seed_week = SEED.get("settleWeek") or {}
    if seed_week.get("start"):
        current = L.setting(db, "settleWeek") or {}
        seed_key = week_key(seed_week)
        current_key = week_key(current)
        has_seed_logs = bool(seed_key and db.query(SettleLog).filter(SettleLog.week == seed_key).count())
        # Restore demo display week when auto-rollover left an empty new week but seed logs exist.
        if has_seed_logs and current_key != seed_key and not db.query(SettleLog).filter(SettleLog.week == current_key).count():
            L.save_setting(db, "settleWeek", seed_week)
    if SEED.get("settleMeta") and not L.setting(db, "settleMeta"):
        L.save_setting(db, "settleMeta", SEED["settleMeta"])
