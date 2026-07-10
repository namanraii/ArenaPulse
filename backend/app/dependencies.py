"""Shared application state and dependency injection for FastAPI routes."""

from __future__ import annotations

from app.agents.concierge import ConciergeAgent
from app.agents.crowd_sentinel import CrowdSentinelAgent
from app.agents.navigator import NavigatorAgent
from app.agents.ops_commander import OpsCommanderAgent
from app.agents.sustainability import SustainabilityAgent
from app.graph.neo4j_client import Neo4jClient
from app.simulator.crowd_simulator import CrowdSimulator
from app.utils.llm_router import LLMRouter

llm_router: LLMRouter | None = None
neo4j_client: Neo4jClient | None = None
navigator_agent: NavigatorAgent | None = None
concierge_agent: ConciergeAgent | None = None
crowd_sentinel: CrowdSentinelAgent | None = None
ops_commander: OpsCommanderAgent | None = None
sustainability_agent: SustainabilityAgent | None = None
simulator: CrowdSimulator | None = None
demo_mode: bool = True
