from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict

from fastapi import WebSocket

from database import SessionLocal
from models import StaffEvent

_connections: dict[int, set[WebSocket]] = defaultdict(set)
_event_loop: asyncio.AbstractEventLoop | None = None
_waiters: list[asyncio.Future] = []
_poll_task: asyncio.Task | None = None
_last_seen_id = 0


async def connect(uid: int, websocket: WebSocket) -> None:
    await websocket.accept()
    _connections[uid].add(websocket)


def disconnect(uid: int, websocket: WebSocket) -> None:
    peers = _connections.get(uid)
    if not peers:
        return
    peers.discard(websocket)
    if not peers:
        _connections.pop(uid, None)


async def _broadcast(payload: dict) -> None:
    message = json.dumps(payload, ensure_ascii=False)
    stale: list[tuple[int, WebSocket]] = []
    for uid, peers in list(_connections.items()):
        for websocket in list(peers):
            try:
                await websocket.send_text(message)
            except Exception:
                stale.append((uid, websocket))
    for uid, websocket in stale:
        disconnect(uid, websocket)


async def _notify_waiters(payload: dict) -> None:
    for fut in list(_waiters):
        if not fut.done():
            fut.set_result(dict(payload))
    _waiters.clear()


async def wait_for_change(timeout: float) -> dict:
    loop = asyncio.get_running_loop()
    fut: asyncio.Future = loop.create_future()
    _waiters.append(fut)
    try:
        return await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError:
        return {"type": "timeout"}
    finally:
        if fut in _waiters:
            _waiters.remove(fut)


def publish(event: str, item_id: int = 0) -> None:
    """Persist event so every API instance can fan out to its local sockets / long-polls."""
    payload = {"type": "todo.changed", "event": event, "id": int(item_id or 0)}
    try:
        with SessionLocal() as db:
            db.add(StaffEvent(event=event, item_id=int(item_id or 0), created_at=time.time()))
            # Keep table small
            oldest = (
                db.query(StaffEvent.id)
                .order_by(StaffEvent.id.desc())
                .offset(500)
                .limit(1)
                .scalar()
            )
            if oldest:
                db.query(StaffEvent).filter(StaffEvent.id <= oldest).delete(synchronize_session=False)
            db.commit()
    except Exception as e:
        print(f"[reminders] persist failed: {e}")
        # Still try same-instance notify if DB write fails
        if _event_loop and _event_loop.is_running():
            asyncio.run_coroutine_threadsafe(_broadcast(payload), _event_loop)
            asyncio.run_coroutine_threadsafe(_notify_waiters(payload), _event_loop)


async def _poll_bus() -> None:
    global _last_seen_id
    while True:
        try:
            with SessionLocal() as db:
                if _last_seen_id <= 0:
                    latest = db.query(StaffEvent.id).order_by(StaffEvent.id.desc()).limit(1).scalar()
                    _last_seen_id = int(latest or 0)
                else:
                    rows = (
                        db.query(StaffEvent)
                        .filter(StaffEvent.id > _last_seen_id)
                        .order_by(StaffEvent.id.asc())
                        .limit(50)
                        .all()
                    )
                    for row in rows:
                        _last_seen_id = int(row.id)
                        payload = {
                            "type": "todo.changed",
                            "event": row.event,
                            "id": int(row.item_id or 0),
                        }
                        await _broadcast(payload)
                        await _notify_waiters(payload)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[reminders] poll: {e}")
        await asyncio.sleep(0.4)


def start_listener() -> None:
    global _event_loop, _poll_task, _last_seen_id
    _event_loop = asyncio.get_running_loop()
    _last_seen_id = 0
    if _poll_task and not _poll_task.done():
        _poll_task.cancel()
    _poll_task = _event_loop.create_task(_poll_bus())


async def stop_listener() -> None:
    global _event_loop, _poll_task
    if _poll_task and not _poll_task.done():
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass
    _poll_task = None
    for fut in list(_waiters):
        if not fut.done():
            fut.cancel()
    _waiters.clear()
    _event_loop = None
