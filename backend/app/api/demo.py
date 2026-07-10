"""Demo fallback API routes (work without Neo4j/LLM)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import dependencies as deps
from app.database import add_audit_log
from app.demo_data import STADIUM_ZONES, demo_chat, demo_navigation, demo_ops_actions
from app.models import (
    ChatRequest,
    ChatResponse,
    NavigationRequest,
    NavigationResponse,
    OpsAction,
    OpsActionStatus,
)

router = APIRouter(prefix="/demo", tags=["demo"])


class RejectRequest(BaseModel):
    reason: str = ""


@router.get("/density-history")
async def density_history() -> list[dict]:
    """Return rolling average density timeline from the live simulator."""
    if deps.simulator:
        return deps.simulator.get_density_timeline()
    return []


@router.get("/zones")
async def demo_zones() -> list[dict]:
    """Retrieve crowd zone data for the frontend heat map."""
    if deps.simulator:
        return deps.simulator.get_zones_for_frontend()
    return STADIUM_ZONES


@router.post("/navigate", response_model=NavigationResponse)
async def demo_navigate(request: NavigationRequest) -> NavigationResponse:
    """Provide a navigation route (uses graph agent when available)."""
    if deps.navigator_agent and not deps.demo_mode:
        return await deps.navigator_agent.navigate(request)
    return demo_navigation(request)


@router.post("/concierge/chat", response_model=ChatResponse)
async def demo_concierge_chat(request: ChatRequest) -> ChatResponse:
    """Provide a concierge response (uses LLM agent when available)."""
    if deps.concierge_agent and not deps.demo_mode:
        return await deps.concierge_agent.chat(request)
    return demo_chat(request.message, request.language)


@router.get("/ops/actions", response_model=list[OpsAction])
async def demo_actions() -> list[OpsAction]:
    """Retrieve operational actions for the dashboard."""
    if deps.ops_commander and not deps.demo_mode:
        return await deps.ops_commander.aggregate_and_prioritize()
    return demo_ops_actions()


@router.post("/ops/actions/{action_id}/approve", response_model=OpsAction)
async def demo_approve_action(action_id: int) -> OpsAction:
    """Approve an operational action and record an audit log entry."""
    actions = demo_ops_actions()
    for action in actions:
        if action.id == action_id:
            updated = action.model_copy(update={"status": OpsActionStatus.APPROVED})
            await add_audit_log(
                user_id=None,
                action_type="approve_action",
                target_id=str(action_id),
                details={"title": action.title, "source": "demo"},
            )
            return updated
    raise HTTPException(status_code=404, detail="Action not found")


@router.post("/ops/actions/{action_id}/reject", response_model=OpsAction)
async def demo_reject_action(action_id: int, req: RejectRequest) -> OpsAction:
    """Reject an operational action and record an audit log entry."""
    actions = demo_ops_actions()
    for action in actions:
        if action.id == action_id:
            updated = action.model_copy(update={"status": OpsActionStatus.REJECTED})
            await add_audit_log(
                user_id=None,
                action_type="reject_action",
                target_id=str(action_id),
                details={"title": action.title, "reason": req.reason, "source": "demo"},
            )
            return updated
    raise HTTPException(status_code=404, detail="Action not found")


@router.get("/sustainability")
async def demo_sustainability() -> dict:
    """Retrieve sustainability metrics (fallback)."""
    from app.api.sustainability import sustainability_summary

    return await sustainability_summary()
