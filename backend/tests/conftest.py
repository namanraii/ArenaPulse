"""Shared test fixtures for ArenaPulse backend tests.

Note: Agent fixtures use lazy imports to avoid pulling in asyncpg at collection
time on environments where it is not installed (e.g. Python 3.13 local dev).
The full agent suite requires a working asyncpg install.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_llm():
    """A fully mocked LLMRouter."""
    m = AsyncMock()
    m.call_flash = AsyncMock(return_value="Flash response")
    m.call_pro = AsyncMock(return_value="Pro response")
    m.call_cached = AsyncMock(return_value="Cached response")
    return m


@pytest.fixture
def mock_neo4j():
    """A fully mocked Neo4jClient."""
    m = AsyncMock()
    m.find_step_free_path = AsyncMock(
        return_value=[
            {
                "name": "Zone_1",
                "type": "Zone",
                "distance_m": 0,
                "step_free": True,
                "estimated_time_s": 0,
            },
            {
                "name": "Zone_2",
                "type": "Zone",
                "distance_m": 120,
                "step_free": True,
                "estimated_time_s": 90,
            },
        ]
    )
    m.get_zone_density = AsyncMock(return_value=0.5)
    m.update_zone_density = AsyncMock()
    m.get_all_zones = AsyncMock(
        return_value=[
            {"name": "Zone_1", "capacity": 10000, "density": 0.5},
        ]
    )
    m.find_nearest_exit = AsyncMock(return_value={"name": "Exit_North", "step_free": True})
    m.find_nearest_medical = AsyncMock(return_value={"name": "Medical_North"})
    m.find_nearest_restroom = AsyncMock(return_value={"name": "RR_1A", "accessible": True})
    m.find_zone_for_section = AsyncMock(return_value="Zone_1")
    m.find_transit_for_gate = AsyncMock(
        return_value=[{"name": "Metro_Blue_Line", "mode": "metro", "wait": 5}]
    )
    m.get_stadium_facts = AsyncMock(return_value=[{"capacity": 10000}])
    return m


@pytest.fixture
def navigator(mock_llm, mock_neo4j):
    from app.agents.navigator import NavigatorAgent

    return NavigatorAgent(mock_llm, mock_neo4j)


@pytest.fixture
def concierge(mock_llm, mock_neo4j):
    from app.agents.concierge import ConciergeAgent

    return ConciergeAgent(mock_llm, mock_neo4j)


@pytest.fixture
def crowd_sentinel(mock_llm, mock_neo4j):
    from app.agents.crowd_sentinel import CrowdSentinelAgent

    return CrowdSentinelAgent(mock_llm, mock_neo4j)


@pytest.fixture
def ops_commander(mock_llm, mock_neo4j):
    from app.agents.ops_commander import OpsCommanderAgent

    return OpsCommanderAgent(mock_llm, mock_neo4j)


@pytest.fixture
def sustainability(mock_llm, mock_neo4j):
    from app.agents.sustainability import SustainabilityAgent

    return SustainabilityAgent(mock_llm, mock_neo4j)
