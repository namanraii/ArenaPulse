"""Base agent class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

from app.database import add_audit_log
from app.graph.neo4j_client import Neo4jClient
from app.utils.llm_router import LLMRouter

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Abstract base for all ArenaPulse agents."""

    name: str = "BaseAgent"

    def __init__(self, llm_router: LLMRouter, neo4j: Neo4jClient) -> None:
        self.llm = llm_router
        self.neo4j = neo4j
        self.logger = logger.bind(agent=self.name)

    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Process input and return output. Must be implemented by subclasses."""
        raise NotImplementedError

    async def log_action(self, action_type: str, details: dict[str, Any]) -> None:
        await add_audit_log(user_id=None, action_type=f"{self.name}:{action_type}", details=details)
        self.logger.info("agent_action", action_type=action_type, details=details)
