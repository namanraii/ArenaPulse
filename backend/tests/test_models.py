from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models import ChatRequest, NavigationRequest, OpsAction, OpsActionPriority, OpsActionStatus


def test_ops_action_validation():
    action = OpsAction(
        id=1,
        title="Test Action",
        description="A test",
        reasoning="Testing",
        priority=OpsActionPriority.HIGH,
        status=OpsActionStatus.PENDING,
        recommended_by="Tester",
        created_at=datetime.now(timezone.utc),
        affected_zones=["Zone_1"],
        affected_population=100,
    )

    assert action.title == "Test Action"
    assert action.priority == OpsActionPriority.HIGH

    # Missing required field
    with pytest.raises(ValidationError):
        OpsAction(
            title="Test Action",
            description="A test",
            # missing reasoning, priority, etc
        )


def test_chat_request_validation():
    req = ChatRequest(message="Hello", language="fr")
    assert req.message == "Hello"
    assert req.language == "fr"


def test_navigation_request_validation():
    req = NavigationRequest(start_location="Zone_1", destination_intent="Gate A", step_free=True)
    assert req.start_location == "Zone_1"
    assert req.destination_intent == "Gate A"
    assert req.step_free is True
