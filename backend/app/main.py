"""FastAPI entrypoint for ArenaPulse."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from app.agents.concierge import ConciergeAgent
from app.agents.crowd_sentinel import CrowdSentinelAgent
from app.agents.navigator import NavigatorAgent
from app.agents.ops_commander import OpsCommanderAgent
from app.agents.sustainability import SustainabilityAgent
from app.api import auth, concierge, navigation, ops, websocket
from app.config import settings
from app.database import close_db, init_db
from app.demo_data import STADIUM_ZONES, demo_chat, demo_navigation, demo_ops_actions
from app.graph.neo4j_client import Neo4jClient, close_driver, init_driver
from app.models import ChatRequest, ChatResponse, NavigationRequest, NavigationResponse, OpsAction, OpsActionStatus, ZoneDensity
from app.simulator.crowd_simulator import CrowdSimulator, MatchSchedule
from app.utils.llm_router import LLMRouter
from app.utils.security import close_redis

class RejectRequest(BaseModel):
    reason: str = ""


logger = structlog.get_logger()

# Global agent references (set during lifespan)
llm_router: LLMRouter | None = None
neo4j_client: Neo4jClient | None = None
navigator_agent: NavigatorAgent | None = None
concierge_agent: ConciergeAgent | None = None
crowd_sentinel: CrowdSentinelAgent | None = None
ops_commander: OpsCommanderAgent | None = None
sustainability_agent: SustainabilityAgent | None = None
simulator: CrowdSimulator | None = None
demo_mode = True


async def _on_simulator_tick(zones: list[ZoneDensity]) -> None:
    """Process each simulator tick through crowd + sustainability agents."""
    global crowd_sentinel, sustainability_agent, simulator
    if crowd_sentinel:
        await crowd_sentinel.process_density_batch(zones)
    if sustainability_agent and simulator:
        sustainability_agent.update_from_simulator(
            simulator.get_transit_state(),
            simulator.get_waste_state(),
            simulator.get_water_refills(),
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize dependencies and start simulator."""
    global llm_router, neo4j_client, navigator_agent, concierge_agent
    global crowd_sentinel, ops_commander, sustainability_agent, simulator, demo_mode

    llm_router = LLMRouter()

    try:
        await init_db()
    except Exception as exc:
        logger.warning("postgres_init_failed", error=str(exc))

    simulator = CrowdSimulator(neo4j=None)
    match_start = datetime.now(timezone.utc) + timedelta(minutes=5)
    simulator.set_schedule(
        MatchSchedule(
            match_start=match_start,
            halftime_start=match_start + timedelta(minutes=45),
            halftime_end=match_start + timedelta(minutes=60),
            match_end=match_start + timedelta(minutes=105),
        )
    )
    simulator.on_tick(_on_simulator_tick)

    try:
        await init_driver()
        neo4j_client = Neo4jClient()
        navigator_agent = NavigatorAgent(llm_router, neo4j_client)
        concierge_agent = ConciergeAgent(llm_router, neo4j_client)
        crowd_sentinel = CrowdSentinelAgent(llm_router, neo4j_client)
        ops_commander = OpsCommanderAgent(llm_router, neo4j_client)
        sustainability_agent = SustainabilityAgent(llm_router, neo4j_client)

        simulator.neo4j = neo4j_client
        demo_mode = False
        logger.info("arenapulse_started", mode="production")
    except Exception as exc:
        demo_mode = True
        logger.warning("arenapulse_started_in_demo_mode", reason=str(exc))

    await simulator.start()

    yield

    if simulator:
        await simulator.stop()
    if llm_router:
        await llm_router.close()
    await close_redis()
    await close_db()
    await close_driver()


app = FastAPI(
    title="ArenaPulse API",
    version="0.1.0",
    description="GenAI-enabled stadium operations and fan copilot for FIFA World Cup 2026.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(navigation.router, prefix="/api/v1")
app.include_router(concierge.router, prefix="/api/v1")
app.include_router(ops.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")


@app.api_route("/api/v1/healthz", methods=["GET", "HEAD"])
async def healthz() -> dict:
    """Return health status of the API and its dependent agents.

    Returns:
        dict: Health check payload.
    """
    return {
        "status": "ok",
        "mode": "demo" if demo_mode else "production",
        "venue": "AT&T Stadium / Dallas Stadium",
        "tournament": "FIFA World Cup 2026",
        "agents": {
            "navigator": navigator_agent is not None,
            "concierge": concierge_agent is not None,
            "crowd_sentinel": crowd_sentinel is not None,
            "ops_commander": ops_commander is not None,
            "sustainability": sustainability_agent is not None,
        },
    }


@app.get("/api/v1/sustainability/summary")
async def sustainability_summary() -> dict:
    """Get the latest sustainability summary from the agent.

    Returns:
        dict: A summary containing eco-scores and transit metrics.
    """
    if sustainability_agent:
        summary = await sustainability_agent.get_summary()
        data = summary.model_dump()
        data["estimated_co2_kg_per_1000_fans"] = data.get("estimated_co2_kg", 0)
        return data
    return {
        "transit_split": {"metro": 0.35, "bus": 0.2, "rideshare": 0.25, "walk": 0.15, "shuttle": 0.05},
        "estimated_co2_kg": 82.5,
        "estimated_co2_kg_per_1000_fans": 82.5,
        "sustainability_score": 63,
        "eco_tips": [
            "Promote Gate D rail shuttle while rideshare queues are saturated.",
            "Send refill-station reminders to sections with high bottled-water purchases.",
            "Dispatch waste volunteers to bins above 80% before the final whistle surge.",
        ],
        "waste_bin_fill_pct": {f"Bin_{i}": 0.3 for i in range(1, 9)},
        "water_refill_usage": 120,
    }


@app.get("/api/v1/ops/efficiency")
async def efficiency_metrics() -> dict:
    """Get efficiency metrics from the LLM router (e.g., cache hits/misses).

    Returns:
        dict: Efficiency metrics payload.
    """
    if not llm_router:
        return {"status": "unavailable"}
    return llm_router.get_efficiency_summary()


# Demo fallback endpoints (work even without Neo4j/LLM)
@app.get("/api/v1/demo/zones")
async def demo_zones() -> list[dict]:
    """Retrieve demo crowd zone data for the frontend heat map.

    Returns:
        list[dict]: A list of simulated zone densities.
    """
    if simulator:
        return simulator.get_zones_for_frontend()
    return STADIUM_ZONES


@app.post("/api/v1/demo/navigate", response_model=NavigationResponse)
async def demo_navigate(request: NavigationRequest) -> NavigationResponse:
    """Provide a demo navigation route (fallback).

    Args:
        request: The navigation request.

    Returns:
        NavigationResponse: A simulated navigation route.
    """
    if navigator_agent and not demo_mode:
        return await navigator_agent.navigate(request)
    return demo_navigation(request)


@app.post("/api/v1/demo/concierge/chat", response_model=ChatResponse)
async def demo_concierge_chat(request: ChatRequest) -> ChatResponse:
    """Provide a demo concierge response (fallback).

    Args:
        request: The chat request.

    Returns:
        ChatResponse: A simulated chat response.
    """
    if concierge_agent and not demo_mode:
        return await concierge_agent.chat(request)
    return demo_chat(request.message, request.language)


@app.get("/api/v1/demo/ops/actions", response_model=list[OpsAction])
async def demo_actions() -> list[OpsAction]:
    """Retrieve demo operational actions for the dashboard.

    Returns:
        list[OpsAction]: A list of simulated operational actions.
    """
    if ops_commander and not demo_mode:
        return await ops_commander.aggregate_and_prioritize()
    return demo_ops_actions()


@app.post("/api/v1/demo/ops/actions/{action_id}/approve", response_model=OpsAction)
async def demo_approve_action(action_id: int) -> OpsAction:
    """Approve a demo operational action.

    Args:
        action_id: The ID of the action to approve.

    Returns:
        OpsAction: The updated operational action.
    """
    actions = demo_ops_actions()
    for action in actions:
        if action.id == action_id:
            return action.model_copy(update={"status": OpsActionStatus.APPROVED})
    raise HTTPException(status_code=404, detail="Action not found")


@app.post("/api/v1/demo/ops/actions/{action_id}/reject", response_model=OpsAction)
async def demo_reject_action(action_id: int, req: RejectRequest) -> OpsAction:
    """Reject a demo operational action.

    Args:
        action_id: The ID of the action to reject.
        req: Reject request body containing the reason.

    Returns:
        OpsAction: The updated operational action.
    """
    actions = demo_ops_actions()
    for action in actions:
        if action.id == action_id:
            return action.model_copy(update={"status": OpsActionStatus.REJECTED})
    raise HTTPException(status_code=404, detail="Action not found")


@app.get("/api/v1/demo/sustainability")
async def demo_sustainability() -> dict:
    """Retrieve demo sustainability metrics (fallback).

    Returns:
        dict: A simulated sustainability summary.
    """
    return await sustainability_summary()
