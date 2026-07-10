"""WebSocket routes for real-time streaming."""

from __future__ import annotations

import asyncio

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app import dependencies as deps
from app.config import settings
from app.demo_data import STADIUM_ZONES

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/crowd-feed")
async def crowd_feed(
    websocket: WebSocket,
    token: str | None = Query(default=None, description="Optional JWT access token"),
) -> None:
    """Stream live crowd density updates every 2 seconds.

    Accepts an optional ``token`` query parameter for authenticated clients.
    Unauthenticated connections receive the same feed — the token is validated
    when present so that clients can prove identity without blocking anonymous
    read-only access.
    """
    # Validate token when provided (fail-open: reject only *invalid* tokens)
    if token is not None:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            if payload.get("type") != "access":
                await websocket.close(code=4001, reason="Not an access token")
                return
        except jwt.ExpiredSignatureError:
            await websocket.close(code=4001, reason="Token expired")
            return
        except jwt.InvalidTokenError:
            await websocket.close(code=4001, reason="Invalid token")
            return

    await websocket.accept()
    try:
        while True:
            if deps.simulator:
                payload_data = deps.simulator.get_zones_for_frontend()
                await websocket.send_json({"type": "crowd_update", "zones": payload_data})
            else:
                await websocket.send_json({"type": "crowd_update", "zones": STADIUM_ZONES})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
