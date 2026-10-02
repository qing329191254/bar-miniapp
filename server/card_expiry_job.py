"""Daily card expiry: recompute days left for open cards and expire overdue ones (Asia/Shanghai day).

Runs in its own transaction so a failing request can never roll the sweep back.
"""
from __future__ import annotations

import threading
import time

import logic as L
from database import session_scope

_done_day: str | None = None


def tick_card_expiry() -> int | None:
    """Sweep once per business day; returns expired count, or None when already done today."""
    global _done_day
    day = L.today_str()
    if _done_day == day:
        return None
    with session_scope() as db:
        expired = L.sweep_card_expiry(db)
    _done_day = day
    if expired:
        print(f"[card-expiry] {day}: expired={expired}")
    return expired


def card_expiry_scheduler_loop():
    while True:
        try:
            tick_card_expiry()
        except Exception as exc:
            print(f"[card-expiry] scheduler error: {exc}")
        time.sleep(60)


def start_card_expiry_scheduler():
    threading.Thread(
        target=card_expiry_scheduler_loop, name="card-expiry-scheduler", daemon=True
    ).start()
