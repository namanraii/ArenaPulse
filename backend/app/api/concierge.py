"""Concierge API routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models import ChatRequest, ChatResponse
from app.utils.security import chat_limiter

router = APIRouter(prefix="/concierge", tags=["concierge"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the ConciergeAgent and get a response.

    Args:
        request: The chat request object.

    Returns:
        ChatResponse: The agent's response.
    """
    allowed = await chat_limiter.is_allowed(request.session_id or "anon")
    if not allowed:
        raise HTTPException(status_code=429, detail="Chat rate limit exceeded")

    from app import dependencies as deps

    if not deps.concierge_agent:
        raise HTTPException(status_code=503, detail="Concierge not ready")
    return await deps.concierge_agent.chat(request)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream a message from the ConciergeAgent (SSE).

    Args:
        request: The chat request object.

    Returns:
        StreamingResponse: An SSE stream of words.
    """
    allowed = await chat_limiter.is_allowed(request.session_id or "anon")
    if not allowed:
        raise HTTPException(status_code=429, detail="Chat rate limit exceeded")

    from app import dependencies as deps

    if not deps.concierge_agent:
        raise HTTPException(status_code=503, detail="Concierge not ready")

    response = await deps.concierge_agent.chat(request)

    async def event_generator():
        words = response.response.split()
        for i, word in enumerate(words):
            space = " " if i < len(words) - 1 else ""
            yield f"data: {word}{space}\n\n"
            await asyncio.sleep(0.03)
        yield "data: [END]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/facts")
async def list_facts() -> list[dict]:
    """Retrieve available factual categories for grounding.

    Returns:
        list[dict]: A list of fact types.
    """
    return [
        {"type": "zone", "description": "Stadium zones with live density"},
        {"type": "gate", "description": "Entry gates with nearest transit"},
        {"type": "exit", "description": "Emergency and general exits"},
        {"type": "medical", "description": "First aid and medical points"},
    ]
