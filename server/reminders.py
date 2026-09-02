from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket

_connections: dict[int, set[WebSocket]] = defaultdict(set)
_event_loop: asyncio.AbstractEventLoop | None = None
_waiters: list[asyncio.Future] = []


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
    payload = {"type": "todo.changed", "event": event, "id": int(item_id or 0)}
    # API endpoints execute in worker threads. Hand coroutines back to FastAPI's
    # event loop; the deployment intentionally uses one application instance.
    if _event_loop and _event_loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast(payload), _event_loop)
        asyncio.run_coroutine_threadsafe(_notify_waiters(payload), _event_loop)


def start_listener() -> None:
    global _event_loop
    _event_loop = asyncio.get_running_loop()


async def stop_listener() -> None:
    global _event_loop
    for fut in list(_waiters):
        if not fut.done():
            fut.cancel()
    _waiters.clear()
    _event_loop = None
