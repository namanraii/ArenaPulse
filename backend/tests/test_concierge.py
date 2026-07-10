from unittest.mock import AsyncMock, patch

import pytest

from app.agents.concierge import ConciergeAgent
from app.models import ChatRequest


@pytest.mark.asyncio
async def test_concierge_intent_classification():
    agent = ConciergeAgent(llm_router=None, neo4j=None)  # type: ignore

    # Test intent classification
    assert agent._classify_intent("Where is the restroom?") == "navigation"
    assert agent._classify_intent("How do I get to Zone 4?") == "navigation"
    assert agent._classify_intent("What time does the match start?") == "schedule"
    assert agent._classify_intent("Can I bring a camera?") == "prohibited"
    assert agent._classify_intent("I need help, someone is injured") == "emergency"
    assert agent._classify_intent("Hello, who are you?") == "general"


@pytest.mark.asyncio
async def test_concierge_chat_flow():
    mock_llm = AsyncMock()
    mock_llm.call_cached.return_value = "This is a mock response from the LLM."
    mock_neo4j = AsyncMock()

    agent = ConciergeAgent(llm_router=mock_llm, neo4j=mock_neo4j)

    req = ChatRequest(message="Where is the bathroom?", language="en", session_id="test-session")

    # Needs to be mocked to avoid calling DB
    with patch.object(agent, "_retrieve_facts", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = [{"type": "facilities", "zones": []}]

        # Also mock log_action which might try to write to DB
        with patch.object(agent, "log_action", new_callable=AsyncMock) as mock_log:
            response = await agent.chat(req)

            assert response.detected_intent == "navigation"
            assert response.response == "This is a mock response from the LLM."
            assert len(response.sources) == 1
            mock_llm.call_cached.assert_called_once()
            mock_log.assert_called_once()
