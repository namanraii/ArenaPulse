"""Operations dashboard API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import dependencies as deps
from app.auth import require_role
from app.database import get_audit_logs, get_pending_ops_actions
from app.models import OpsAction, User, UserRole

router = APIRouter(prefix="/ops", tags=["operations"])


@router.get("/actions", response_model=list[OpsAction])
async def list_actions(
    user: User = Depends(require_role(UserRole.ORGANIZER, UserRole.VOLUNTEER)),
) -> list[OpsAction]:
    """List pending operational actions."""
    if deps.ops_commander:
        return await deps.ops_commander.aggregate_and_prioritize()
    return await get_pending_ops_actions()


@router.post("/actions/{action_id}/approve", response_model=OpsAction)
async def approve_action(
    action_id: int,
    user: User = Depends(require_role(UserRole.ORGANIZER)),
) -> OpsAction:
    """Approve a pending operational action."""
    if not deps.ops_commander:
        raise HTTPException(status_code=503, detail="OpsCommander not ready")
    action = await deps.ops_commander.approve_action(action_id, user.id)
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
    """Reject a pending operational action."""
    if not deps.ops_commander:
        raise HTTPException(status_code=503, detail="OpsCommander not ready")
    action = await deps.ops_commander.reject_action(action_id, user.id, req.reason)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.get("/alerts")
async def get_alerts(
    user: User = Depends(require_role(UserRole.ORGANIZER, UserRole.VOLUNTEER)),
) -> list[dict]:
    """Get active crowd alerts from CrowdSentinelAgent."""
    if deps.crowd_sentinel:
        alerts = deps.crowd_sentinel.get_active_alerts()
        return [
            {
                "id": a.id,
                "zone": a.zone,
                "severity": a.severity.value,
                "message": a.message,
                "density": a.density,
                "predicted_crossing_time_min": a.predicted_crossing_time_min,
                "suggested_mitigation": a.suggested_mitigation,
                "affected_population": a.affected_population,
                "detected_at": a.detected_at.isoformat(),
            }
            for a in alerts
        ]
    return []


@router.get("/audit")
async def get_audit(
    user: User = Depends(require_role(UserRole.ORGANIZER)),
) -> list[dict]:
    """Get the audit log of all system actions."""
    return await get_audit_logs(limit=200)


@router.get("/efficiency")
async def get_efficiency(
    user: User = Depends(require_role(UserRole.ORGANIZER)),
) -> dict:
    """Get system efficiency and LLM usage metrics."""
    if not deps.llm_router:
        raise HTTPException(status_code=503, detail="LLM router not ready")
    return deps.llm_router.get_efficiency_summary()
