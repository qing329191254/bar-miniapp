"""Monthly points clear: available points wipe on the 1st at 12:00 Asia/Shanghai.

Frozen withdrawal points (point_fz) are kept. Monthly gain (point_mg) resets with the clear.
"""
from __future__ import annotations

import threading
import time

import cache
import logic as L
from database import session_scope
from models import Wallet


def _clear_period_key(clear_at) -> str:
    return clear_at.strftime("%Y-%m-%d")


def due_clear_period(now=None) -> str | None:
    """If now is past this month's 1st 12:00, return that period key; else None."""
    now = now or L.business_now()
    clear_at = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)
    if now < clear_at:
        return None
    return _clear_period_key(clear_at)


def run_monthly_point_clear(db, *, trigger: str = "auto") -> dict:
    period = due_clear_period()
    if not period:
        return {"ok": True, "skipped": True, "reason": "not_due"}

    if not cache.idem_begin(db, f"point-clear:{period}", ttl=24 * 3600):
        return {"ok": True, "skipped": True, "reason": "busy_or_done", "period": period}

    last = L.setting(db, "pointClearLast") or {}
    if last.get("period") == period:
        return {"ok": True, "skipped": True, "reason": "already", "period": period}

    total_cleared = 0
    touched = 0
    for w in db.query(Wallet).with_for_update().all():
        av = int(w.point_av or 0)
        pd = int(w.point_pd or 0)
        mg = int(w.point_mg or 0)
        if av == 0 and pd == 0 and mg == 0:
            continue
        if av > 0:
            total_cleared += av
        w.point_av = 0
        w.point_pd = 0
        w.point_mg = 0
        touched += 1

    ledger = dict(L.setting(db, "ledger") or {})
    ledger["ptCleared"] = int(ledger.get("ptCleared") or 0) + total_cleared
    # Available points do not carry across months; opening for the new period is 0.
    ledger["ptOpening"] = 0
    L.save_setting(db, "ledger", ledger)
    L.save_setting(
        db,
        "pointClearLast",
        {
            "period": period,
            "at": L.fmt_hm(),
            "cleared": total_cleared,
            "wallets": touched,
            "trigger": trigger,
        },
    )
    L.log(
        db,
        "POINT_MONTH_CLEAR",
        f"积分月清零 {period} 12:00 · 清零可用 {total_cleared} · 钱包 {touched} · {trigger}",
        None,
        {"nick": "系统自动", "role": "BOSS"},
    )
    return {
        "ok": True,
        "skipped": False,
        "period": period,
        "cleared": total_cleared,
        "wallets": touched,
        "trigger": trigger,
    }


def tick_point_clear(db) -> dict | None:
    result = run_monthly_point_clear(db, trigger="auto")
    if result.get("ok") and not result.get("skipped"):
        print(
            f"[point-clear] {result.get('period')}: cleared={result.get('cleared')} "
            f"wallets={result.get('wallets')}"
        )
    return result


def point_clear_scheduler_loop():
    time.sleep(20)
    while True:
        try:
            with session_scope() as db:
                tick_point_clear(db)
        except Exception as exc:
            print(f"[point-clear] scheduler error: {exc}")
        time.sleep(60)


def start_point_clear_scheduler():
    threading.Thread(
        target=point_clear_scheduler_loop, name="point-clear-scheduler", daemon=True
    ).start()
