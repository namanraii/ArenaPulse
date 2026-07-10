"""Integration tests for ops dashboard endpoints: actions, approve, reject, audit."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.main import app
from app.models import (
    OpsAction,
    OpsActionPriority,
    OpsActionStatus,
    User,
    UserRole,
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _make_token(role: UserRole, user_id: int = 1, username: str = "testuser") -> str:
    return create_access_token(user_id=user_id, username=username, role=role)


def _make_user(role: UserRole, user_id: int = 1) -> User:
    return User(
        id=user_id,
        username="testuser",
        email="test@arena.com",
        role=role,
        created_at=datetime.utcnow(),
    )


def _sample_action(action_id: int = 101) -> OpsAction:
    return OpsAction(
        id=action_id,
        title="Open North Gate",
        description="Redirect 2,000 fans to reduce congestion.",
        reasoning="Zone_4 at 92% density — critical threshold breached.",
        priority=OpsActionPriority.CRITICAL,
        status=OpsActionStatus.PENDING,
        recommended_by="CrowdSentinelAgent",
        created_at=datetime.utcnow(),
        affected_zones=["Zone_4"],
        affected_population=2000,
        time_to_impact_min=5.0,
    )


# ---------------------------------------------------------------------------
# GET /ops/actions
# ---------------------------------------------------------------------------


def test_ops_actions_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/ops/actions")
    assert resp.status_code == 401


def test_ops_actions_fan_is_forbidden(client: TestClient) -> None:
    token = _make_token(UserRole.FAN)
    fan_user = _make_user(UserRole.FAN)
    with patch("app.auth.get_user_by_id", new=AsyncMock(return_value=fan_user)):
        resp = client.get(
            "/api/v1/ops/actions",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


def test_ops_actions_volunteer_can_read(client: TestClient) -> None:
    token = _make_token(UserRole.VOLUNTEER)
    vol_user = _make_user(UserRole.VOLUNTEER)
    sample = [_sample_action()]
    with (
        patch("app.auth.get_user_by_id", new=AsyncMock(return_value=vol_user)),
        patch("app.api.ops.deps") as mock_deps,
    ):
        mock_deps.ops_commander = None
        mock_ops = AsyncMock(return_value=sample)
        with patch("app.api.ops.get_pending_ops_actions", new=mock_ops):
            resp = client.get(
                "/api/v1/ops/actions",
                headers={"Authorization": f"Bearer {token}"},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# POST /ops/actions/{id}/approve
# ---------------------------------------------------------------------------


def test_approve_requires_organizer_role(client: TestClient) -> None:
    token = _make_token(UserRole.VOLUNTEER)
    vol_user = _make_user(UserRole.VOLUNTEER)
    with patch("app.auth.get_user_by_id", new=AsyncMock(return_value=vol_user)):
        resp = client.post(
            "/api/v1/ops/actions/1/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


def test_approve_returns_404_when_not_found(client: TestClient) -> None:
    token = _make_token(UserRole.ORGANIZER)
    org_user = _make_user(UserRole.ORGANIZER)
    mock_commander = AsyncMock()
    mock_commander.approve_action = AsyncMock(return_value=None)
    with (
        patch("app.auth.get_user_by_id", new=AsyncMock(return_value=org_user)),
        patch("app.api.ops.deps") as mock_deps,
    ):
        mock_deps.ops_commander = mock_commander
        resp = client.post(
            "/api/v1/ops/actions/9999/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code in (404, 503)


# ---------------------------------------------------------------------------
# POST /ops/actions/{id}/reject
# ---------------------------------------------------------------------------


def test_reject_requires_organizer_role(client: TestClient) -> None:
    token = _make_token(UserRole.VOLUNTEER)
    vol_user = _make_user(UserRole.VOLUNTEER)
    with patch("app.auth.get_user_by_id", new=AsyncMock(return_value=vol_user)):
        resp = client.post(
            "/api/v1/ops/actions/1/reject",
            json={"reason": "Not needed"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /ops/audit
# ---------------------------------------------------------------------------


def test_audit_requires_organizer(client: TestClient) -> None:
    token = _make_token(UserRole.VOLUNTEER)
    vol_user = _make_user(UserRole.VOLUNTEER)
    with patch("app.auth.get_user_by_id", new=AsyncMock(return_value=vol_user)):
        resp = client.get(
            "/api/v1/ops/audit",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


def test_audit_organizer_gets_list(client: TestClient) -> None:
    token = _make_token(UserRole.ORGANIZER)
    org_user = _make_user(UserRole.ORGANIZER)
    fake_logs: list[dict] = [
        {
            "id": 1,
            "user_id": 1,
            "username": "testuser",
            "action_type": "approve_action",
            "target_id": "42",
            "details": {"title": "Open gate"},
            "timestamp": datetime.utcnow().isoformat(),
        }
    ]
    with (
        patch("app.auth.get_user_by_id", new=AsyncMock(return_value=org_user)),
        patch("app.api.ops.get_audit_logs", new=AsyncMock(return_value=fake_logs)),
    ):
        resp = client.get(
            "/api/v1/ops/audit",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["action_type"] == "approve_action"


# ---------------------------------------------------------------------------
# Demo approve writes audit log
# ---------------------------------------------------------------------------


def test_demo_approve_writes_audit_log(client: TestClient) -> None:
    """Demo approve endpoint must call add_audit_log."""
    with patch("app.api.demo.add_audit_log", new=AsyncMock()) as mock_audit:
        resp = client.post("/api/v1/demo/ops/actions/1/approve")
        assert resp.status_code == 200
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        assert call_kwargs["action_type"] == "approve_action"


def test_demo_reject_writes_audit_log(client: TestClient) -> None:
    """Demo reject endpoint must call add_audit_log."""
    with patch("app.api.demo.add_audit_log", new=AsyncMock()) as mock_audit:
        resp = client.post(
            "/api/v1/demo/ops/actions/1/reject",
            json={"reason": "Not needed"},
        )
        assert resp.status_code == 200
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        assert call_kwargs["action_type"] == "reject_action"
