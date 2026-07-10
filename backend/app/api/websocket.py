"""WebSocket routes for real-time streaming."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.demo_data import STADIUM_ZONES

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/crowd-feed")
async def crowd_feed(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            from app.main import simulator

            if simulator:
                payload = simulator.get_zones_for_frontend()
                await websocket.send_json({"type": "crowd_update", "zones": payload})
            else:
                await websocket.send_json({"type": "crowd_update", "zones": STADIUM_ZONES})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
