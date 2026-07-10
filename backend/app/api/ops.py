"""Operations dashboard API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_role
from app.database import (
    add_audit_log,
    get_all_ops_actions,
    get_audit_logs,
    get_pending_ops_actions,
    update_ops_action_status,
)
from app.models import OpsAction, OpsActionStatus, User, UserRole
from app.agents.ops_commander import OpsCommanderAgent
from app.agents.sustainability import SustainabilityAgent

router = APIRouter(prefix="/ops", tags=["operations"])


@router.get("/actions", response_model=list[OpsAction])
async def list_actions(
    user: User = Depends(require_role(UserRole.ORGANIZER, UserRole.VOLUNTEER)),
) -> list[OpsAction]:
    """List pending operational actions.

    Args:
        user: The authenticated user.

    Returns:
        list[OpsAction]: Prioritized operational actions.
    """
    from app.main import ops_commander
    if ops_commander:
        return await ops_commander.aggregate_and_prioritize()
    return await get_pending_ops_actions()


@router.post("/actions/{action_id}/approve", response_model=OpsAction)
async def approve_action(
    action_id: int,
    user: User = Depends(require_role(UserRole.ORGANIZER)),
) -> OpsAction:
    """Approve a pending operational action.

    Args:
        action_id: The ID of the action.
        user: The authenticated user.

    Returns:
        OpsAction: The updated action.
    """
    from app.main import ops_commander
    if not ops_commander:
        raise HTTPException(status_code=503, detail="OpsCommander not ready")
    action = await ops_commander.approve_action(action_id, user.id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


class RejectRequest(BaseModel):
    reason: str = ""

@router.post("/actions/{action_id}/reject", response_model=OpsAction)
async def reject_action(
    action_id: int,
    req: RejectRequest,
    user: User = Depends(require_role(UserRole.ORGANIZER)),
) -> OpsAction:
    """Reject a pending operational action.

    Args:
        action_id: The ID of the action.
        req: The reject request body.
        user: The authenticated user.

    Returns:
        OpsAction: The updated action.
    """
    from app.main import ops_commander
    if not ops_commander:
        raise HTTPException(status_code=503, detail="OpsCommander not ready")
    action = await ops_commander.reject_action(action_id, user.id, req.reason)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.get("/alerts")
async def get_alerts(
    user: User = Depends(require_role(UserRole.ORGANIZER, UserRole.VOLUNTEER)),
) -> list[dict]:
    """Get active crowd alerts.

    Args:
        user: The authenticated user.

    Returns:
        list[dict]: A list of active alerts.
    """
    # In a real system, query alert queue. Here we return a stub.
    return []


@router.get("/audit")
async def get_audit(
    user: User = Depends(require_role(UserRole.ORGANIZER)),
) -> list[dict]:
    """Get the audit log of all system actions.

    Args:
        user: The authenticated user.

    Returns:
        list[dict]: The audit logs.
    """
    return await get_audit_logs(limit=200)


@router.get("/efficiency")
async def get_efficiency(
    user: User = Depends(require_role(UserRole.ORGANIZER)),
) -> dict:
    """Get system efficiency and LLM usage metrics.

    Args:
        user: The authenticated user.

    Returns:
        dict: Efficiency metrics payload.
    """
    from app.main import llm_router

    if not llm_router:
        raise HTTPException(status_code=503, detail="LLM router not ready")
    return llm_router.get_efficiency_summary()
