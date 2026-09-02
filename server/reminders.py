from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket

import cache


CHANNEL = "wanka:staff-reminders"
_connections: dict[int, set[WebSocket]] = defaultdict(set)
_listen_task: asyncio.Task | None = None


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


def publish(event: str, item_id: int = 0) -> None:
    payload = {"type": "todo.changed", "event": event, "id": int(item_id or 0)}
    try:
        cache.r.publish(CHANNEL, json.dumps(payload, ensure_ascii=False))
    except Exception:
        # Redis is required in production. Local API tests may run without it;
        # the clients will then fall back to summary polling.
        pass


async def _listen() -> None:
    while True:
        pubsub = None
        try:
            pubsub = cache.r.pubsub(ignore_subscribe_messages=True)
            await asyncio.to_thread(pubsub.subscribe, CHANNEL)
            while True:
                item = await asyncio.to_thread(pubsub.get_message, True, 1.0)
                if item and item.get("data"):
                    await _broadcast(json.loads(item["data"]))
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            if pubsub:
                await asyncio.to_thread(pubsub.close)
            raise
        except Exception:
            if pubsub:
                try:
                    await asyncio.to_thread(pubsub.close)
                except Exception:
                    pass
            await asyncio.sleep(2)


def start_listener() -> None:
    global _listen_task
    if _listen_task is None or _listen_task.done():
        _listen_task = asyncio.create_task(_listen())


async def stop_listener() -> None:
    global _listen_task
    if not _listen_task:
        return
    _listen_task.cancel()
    try:
        await _listen_task
    except asyncio.CancelledError:
        pass
    _listen_task = None
