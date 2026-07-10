"""Navigation API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import NavigationRequest, NavigationResponse
from app.utils.security import public_limiter

router = APIRouter(prefix="/navigate", tags=["navigation"])


@router.post("", response_model=NavigationResponse)
async def navigate(request: NavigationRequest) -> NavigationResponse:
    """Request a route from the NavigatorAgent.

    Args:
        request: The navigation request object.

    Returns:
        NavigationResponse: The path and instructions.
    """
    # Rate limit check
    allowed = await public_limiter.is_allowed("navigate")
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")

    from app.main import navigator_agent
    if not navigator_agent:
        raise HTTPException(status_code=503, detail="Navigator not ready")
    return await navigator_agent.navigate(request)


@router.get("/zones")
async def list_zones() -> list[dict]:
    """List all available zones from Neo4j.

    Returns:
        list[dict]: Zone data.
    """
    from app.main import neo4j_client
    if not neo4j_client:
        raise HTTPException(status_code=503, detail="Database not ready")
    return await neo4j_client.get_all_zones()
