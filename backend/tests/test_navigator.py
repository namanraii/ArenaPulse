from unittest.mock import AsyncMock, patch

import pytest

from app.agents.navigator import NavigatorAgent
from app.models import NavigationRequest


@pytest.mark.asyncio
async def test_navigator_path_building():
    mock_llm = AsyncMock()
    mock_llm.call_cached.return_value = "Head north towards the gate."
    mock_neo4j = AsyncMock()

    # Mock finding destination zone
    mock_neo4j.find_zone_for_section.return_value = "Zone_2"
    # Mock path finding
    mock_neo4j.find_step_free_path.return_value = [
        {
            "name": "Zone_1",
            "type": "Zone",
            "distance_m": 50,
            "step_free": True,
            "estimated_time_s": 60,
        },
        {"name": "Zone_2", "type": "Zone"},
    ]

    agent = NavigatorAgent(llm_router=mock_llm, neo4j=mock_neo4j)

    req = NavigationRequest(
        start_location="Zone_1", destination_intent="Section 101", step_free=True, language="en"
    )

    with patch.object(agent, "log_action", new_callable=AsyncMock):
        response = await agent.navigate(req)

        assert len(response.path) == 2
        assert response.total_distance_m == 0
        assert response.total_time_s == 0
        assert response.step_free is True
        mock_llm.call_cached.assert_called_once()
