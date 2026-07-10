"""FastAPI entrypoint for ArenaPulse."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import dependencies as deps
from app.agents.concierge import ConciergeAgent
from app.agents.crowd_sentinel import CrowdSentinelAgent
from app.agents.navigator import NavigatorAgent
from app.agents.ops_commander import OpsCommanderAgent
from app.agents.sustainability import SustainabilityAgent
from app.api import auth, concierge, demo, navigation, ops, sustainability, websocket
from app.config import settings
from app.database import close_db, init_db
from app.graph.neo4j_client import Neo4jClient, close_driver, init_driver
from app.models import ZoneDensity
from app.simulator.crowd_simulator import CrowdSimulator, MatchSchedule
from app.utils.llm_router import LLMRouter
from app.utils.security import close_redis

logger = structlog.get_logger()


async def _on_simulator_tick(zones: list[ZoneDensity]) -> None:
    """Process each simulator tick through crowd + sustainability agents."""
    if deps.crowd_sentinel:
        await deps.crowd_sentinel.process_density_batch(zones)
    if deps.sustainability_agent and deps.simulator:
        deps.sustainability_agent.update_from_simulator(
            deps.simulator.get_transit_state(),
            deps.simulator.get_waste_state(),
            deps.simulator.get_water_refills(),
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize dependencies and start simulator."""
    deps.llm_router = LLMRouter()

    try:
        await init_db()
    except Exception as exc:
        logger.warning("postgres_init_failed", error=str(exc))

    deps.simulator = CrowdSimulator(neo4j=None)
    match_start = datetime.now(timezone.utc) + timedelta(minutes=5)
    deps.simulator.set_schedule(
        MatchSchedule(
            match_start=match_start,
            halftime_start=match_start + timedelta(minutes=45),
            halftime_end=match_start + timedelta(minutes=60),
            match_end=match_start + timedelta(minutes=105),
        )
    )
    deps.simulator.on_tick(_on_simulator_tick)

    try:
        await init_driver()
        deps.neo4j_client = Neo4jClient()
        deps.navigator_agent = NavigatorAgent(deps.llm_router, deps.neo4j_client)
        deps.concierge_agent = ConciergeAgent(deps.llm_router, deps.neo4j_client)
        deps.crowd_sentinel = CrowdSentinelAgent(deps.llm_router, deps.neo4j_client)
        deps.ops_commander = OpsCommanderAgent(deps.llm_router, deps.neo4j_client)
        deps.sustainability_agent = SustainabilityAgent(deps.llm_router, deps.neo4j_client)

        deps.simulator.neo4j = deps.neo4j_client
        deps.demo_mode = False
        logger.info("arenapulse_started", mode="production")
    except Exception as exc:
        deps.demo_mode = True
        logger.warning("arenapulse_started_in_demo_mode", reason=str(exc))

    await deps.simulator.start()

    yield

    if deps.simulator:
        await deps.simulator.stop()
    if deps.llm_router:
        await deps.llm_router.close()
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
app.include_router(sustainability.router, prefix="/api/v1")
app.include_router(demo.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")


@app.api_route("/api/v1/healthz", methods=["GET", "HEAD"])
async def healthz() -> dict:
    """Return health status of the API and its dependent agents."""
    return {
        "status": "ok",
        "mode": "demo" if deps.demo_mode else "production",
        "venue": "AT&T Stadium / Dallas Stadium",
        "tournament": "FIFA World Cup 2026",
        "agents": {
            "navigator": deps.navigator_agent is not None,
            "concierge": deps.concierge_agent is not None,
            "crowd_sentinel": deps.crowd_sentinel is not None,
            "ops_commander": deps.ops_commander is not None,
            "sustainability": deps.sustainability_agent is not None,
        },
    }
