"""Additional unit tests to maximize code coverage for ArenaPulse backend modules.

Exercises untested paths in database, llm_router, auth, agents, and api.
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

import app.database as db
from app.auth import require_role
from app.models import (
    NavigationRequest,
    OpsActionPriority,
    OpsActionStatus,
    User,
    UserRole,
)
from app.utils.llm_router import LLMRouter


def restore_db_pool():
    """Ensure database._pool is not None (in case integration test teardown cleared it)."""
    if db._pool is None:
        pool = MagicMock()
        pool.close = AsyncMock()

        # A mock row that can satisfy User, OpsAction, AuditLog, etc.
        mock_row = {
            "id": 1,
            "username": "admin",
            "email": "admin@arena.com",
            "hashed_password": "hash",
            "role": "organizer",
            "created_at": datetime.datetime.now(datetime.timezone.utc),
            "title": "Open Gate",
            "description": "desc",
            "reasoning": "reasoning explanation here",
            "priority": "critical",
            "status": "pending",
            "recommended_by": "sentinel",
            "affected_zones": ["Zone_A"],
            "affected_population": 500,
            "time_to_impact_min": 10.0,
            "approved_by": None,
            "approved_at": None,
            "action_type": "ops_action_approved",
            "target_id": "42",
            "details": "{}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
        }

        pool.acquire.return_value.__aenter__.return_value = MagicMock(
            execute=AsyncMock(),
            fetch=AsyncMock(return_value=[mock_row]),
            fetchrow=AsyncMock(return_value=mock_row),
            fetchval=AsyncMock(return_value=1),
        )
        db._pool = pool
    return db._pool


# ---------------------------------------------------------------------------
# 1. LLMRouter Coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_router_local_fallbacks():
    router = LLMRouter()

    # Test different text prompt routing in local fallback mode
    assert "critical" in router._local_response({"prompt": "crowd alert here"}).lower()
    assert "recycle" in router._local_response({"prompt": "sustainability co2 nudge"}).lower()
    assert "ruta" in router._local_response({"prompt": "espanol please"}).lower()
    assert "ruta" in router._local_response({"prompt": "spanish please"}).lower()
    assert "denses" in router._local_response({"prompt": "french prompt"}).lower()
    assert "steward" in router._local_response({"prompt": "other normal prompt"}).lower()


@pytest.mark.asyncio
async def test_llm_router_calls_and_caching(mock_llm):
    router = LLMRouter()

    # Test call_flash and call_pro metrics increments
    await router.call_flash("Hello Flash")
    await router.call_pro("Hello Pro")
    assert router.metrics["flash_calls"] == 1
    assert router.metrics["pro_calls"] == 1

    summary = router.get_efficiency_summary()
    assert summary["flash_calls"] == 1
    assert summary["pro_calls"] == 1
    assert summary["cache_hit_rate_pct"] == 0.0

    # Test call_cached with hit and miss
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Cache miss

    with patch("app.utils.llm_router.get_redis", return_value=mock_redis):
        res = await router.call_cached("key1", "prompt1")
        assert res is not None
        assert router.metrics["cache_misses"] == 1

        # Test cache hit
        mock_redis.get.return_value = "Cached result string"
        res_hit = await router.call_cached("key1", "prompt1")
        assert res_hit == "Cached result string"
        assert router.metrics["cache_hits"] == 1


# ---------------------------------------------------------------------------
# 2. Database Mocks and Helper Coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_database_user_helpers():
    restore_db_pool()

    user = await db.create_user("dbuser", "db@user.com", "hash", UserRole.VOLUNTEER)
    assert user.id == 1
    assert user.role == UserRole.ORGANIZER  # returned by mock row

    # Test get_user_by_id
    user_by_id = await db.get_user_by_id(1)
    assert user_by_id is not None

    # Test get_user_by_username
    user_by_name = await db.get_user_by_username("dbuser")
    assert user_by_name is not None

    # Test audit logging helpers
    await db.add_audit_log(user_id=1, action_type="test_action", details={"meta": "info"})


@pytest.mark.asyncio
async def test_database_ops_actions_helpers():
    restore_db_pool()

    action = await db.create_ops_action(
        title="Open Gate North",
        description="desc",
        reasoning="reason",
        priority=OpsActionPriority.CRITICAL,
        recommended_by="sentinel",
        affected_zones=["Zone_A"],
        affected_population=5000,
        time_to_impact_min=10.0,
    )
    assert action.id == 1

    pending = await db.get_pending_ops_actions()
    assert len(pending) == 1

    all_actions = await db.get_all_ops_actions(limit=5)
    assert len(all_actions) == 1

    # Test status update
    await db.update_ops_action_status(42, OpsActionStatus.APPROVED, approved_by=1)


# ---------------------------------------------------------------------------
# 3. Auth Guard / RBAC Failures
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_role_raises_on_invalid_role():
    guard = require_role(UserRole.ORGANIZER)

    volunteer_user = User(
        id=2,
        username="vol",
        email="vol@arena.com",
        role=UserRole.VOLUNTEER,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )

    with pytest.raises(HTTPException) as exc:
        await guard(user=volunteer_user)
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# 4. Agents Edge Cases Coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sustainability_nudges(sustainability):
    recommendation = await sustainability.get_transit_recommendation(
        from_gate="Gate_A", to_destination="Metro_North"
    )
    assert recommendation is not None
    assert isinstance(recommendation, dict)


@pytest.mark.asyncio
async def test_ops_commander_mitigation(ops_commander):
    restore_db_pool()
    # Test prioritize aggregate reasoning and actions approval
    top_actions = await ops_commander.aggregate_and_prioritize()
    assert isinstance(top_actions, list)

    approved = await ops_commander.approve_action(action_id=42, user_id=1)
    assert approved is not None


@pytest.mark.asyncio
async def test_navigator_path_step_free(navigator):
    restore_db_pool()
    req = NavigationRequest(
        start_location="Section_101",
        destination_intent="medical",
        step_free=True,
        language="en",
    )
    resp = await navigator.navigate(req)
    assert resp.step_free is True
