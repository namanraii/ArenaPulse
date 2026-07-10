"""OpsCommanderAgent — aggregates, prioritizes, and explains operational actions."""

from __future__ import annotations

import structlog

from app.agents.base import BaseAgent
from app.database import (
    add_audit_log,
    get_pending_ops_actions,
    update_ops_action_status,
)
from app.graph.neo4j_client import Neo4jClient
from app.models import OpsAction, OpsActionPriority, OpsActionStatus
from app.utils.llm_router import LLMRouter

logger = structlog.get_logger()


class OpsCommanderAgent(BaseAgent):
    """Aggregates agent outputs, scores by severity × population × time, produces ranked actions with reasoning traces."""

    name = "OpsCommanderAgent"

    def __init__(self, llm_router: LLMRouter, neo4j: Neo4jClient) -> None:
        super().__init__(llm_router, neo4j)

    async def process(self, input_data: dict) -> list[OpsAction]:
        """Process an input dictionary (implements BaseAgent)."""
        return await self.aggregate_and_prioritize()

    async def aggregate_and_prioritize(self) -> list[OpsAction]:
        """Aggregate pending actions, score them, and generate LLM reasoning.

        Returns:
            list[OpsAction]: The top prioritized actions.
        """
        pending = await get_pending_ops_actions()
        # Also pull any recent alerts from memory (in real system, this would query an alert queue)
        # Score and rank
        scored = []
        for action in pending:
            score = self._score_action(action)
            scored.append((score, action))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_actions = [a for _, a in scored[:10]]

        # Generate reasoning for each
        for action in top_actions:
            if not action.reasoning or len(action.reasoning) < 20:
                action.reasoning = await self._generate_reasoning(action)

        await self.log_action("prioritized", {"count": len(top_actions)})
        return top_actions

    async def approve_action(self, action_id: int, user_id: int) -> OpsAction | None:
        """Approve an operational action.

        Args:
            action_id: The ID of the action to approve.
            user_id: The ID of the user approving it.

        Returns:
            OpsAction | None: The updated action or None if not found.
        """
        action = await update_ops_action_status(action_id, OpsActionStatus.APPROVED, user_id)
        if action:
            await add_audit_log(
                user_id=user_id,
                action_type="ops_action_approved",
                target_id=str(action_id),
                details={"title": action.title, "reasoning": action.reasoning},
            )
            self.logger.info("action_approved", action_id=action_id, user_id=user_id)
        return action

    async def reject_action(self, action_id: int, user_id: int, reason: str) -> OpsAction | None:
        """Reject an operational action.

        Args:
            action_id: The ID of the action to reject.
            user_id: The ID of the user rejecting it.
            reason: The reason for rejection.

        Returns:
            OpsAction | None: The updated action or None if not found.
        """
        action = await update_ops_action_status(action_id, OpsActionStatus.REJECTED, user_id)
        if action:
            await add_audit_log(
                user_id=user_id,
                action_type="ops_action_rejected",
                target_id=str(action_id),
                details={"title": action.title, "reason": reason},
            )
            self.logger.info("action_rejected", action_id=action_id, user_id=user_id, reason=reason)
        return action

    def _score_action(self, action: OpsAction) -> float:
        """Score an action based on severity, population, and time to impact.

        Args:
            action: The OpsAction to score.

        Returns:
            float: The calculated priority score.
        """
        severity_map = {
            OpsActionPriority.CRITICAL: 4.0,
            OpsActionPriority.HIGH: 3.0,
            OpsActionPriority.MEDIUM: 2.0,
            OpsActionPriority.LOW: 1.0,
        }
        severity_score = severity_map.get(action.priority, 1.0)
        population_factor = min(action.affected_population / 1000, 10.0)
        time_factor = 1.0
        if action.time_to_impact_min and action.time_to_impact_min > 0:
            time_factor = max(1.0, 10.0 / action.time_to_impact_min)
        return severity_score * population_factor * time_factor

    async def _generate_reasoning(self, action: OpsAction) -> str:
        """Generate a reasoning trace for an action using the LLM.

        Args:
            action: The OpsAction to explain.

        Returns:
            str: The generated reasoning string.
        """
        prompt = f"""You are an operations AI recommending a stadium action to control-room staff.
Action: {action.title}
Description: {action.description}
Affected zones: {action.affected_zones}
Affected population: {action.affected_population}
Time to impact: {action.time_to_impact_min or 'N/A'} minutes
Write a single explicit reasoning sentence (max 30 words) explaining WHY this action is recommended and what happens if ignored."""
        return await self.llm.call_pro(prompt, temperature=0.2)
