"""NavigatorAgent — graph-constrained routing with GenAI explanations."""

from __future__ import annotations

import structlog

from app.agents.base import BaseAgent
from app.constants import LANGUAGE_NAMES
from app.graph.neo4j_client import Neo4jClient
from app.models import NavigationRequest, NavigationResponse, PathNode
from app.utils.llm_router import LLMRouter

logger = structlog.get_logger()


class NavigatorAgent(BaseAgent):
    """Routes fans through the stadium using graph pathfinding + LLM explanations."""

    name = "NavigatorAgent"

    def __init__(self, llm_router: LLMRouter, neo4j: Neo4jClient) -> None:
        super().__init__(llm_router, neo4j)

    async def process(self, input_data: NavigationRequest) -> NavigationResponse:
        """Process a navigation request (implements BaseAgent)."""
        return await self.navigate(input_data)

    async def navigate(self, request: NavigationRequest) -> NavigationResponse:
        """Calculate a route and generate natural-language directions.

        Args:
            request: The navigation request parameters.

        Returns:
            NavigationResponse: The path and instructions.
        """
        start_zone = request.start_location
        if start_zone.startswith("Section_"):
            zone = await self.neo4j.find_zone_for_section(start_zone)
            if zone:
                start_zone = zone
            else:
                start_zone = "Zone_1"

        # Resolve destination intent to a target zone/node
        target_zone, target_type, target_name = await self._resolve_intent(
            start_zone, request.destination_intent, request.step_free
        )

        if not target_zone:
            return NavigationResponse(
                path=[PathNode(name=start_zone, type="Zone")],
                total_distance_m=0,
                total_time_s=0,
                step_free=request.step_free,
                explanation="Unable to determine destination. Please ask the concierge for assistance.",
            )

        # Graph pathfinding (deterministic — NOT LLM)
        path = await self.neo4j.find_step_free_path(
            start_zone, target_zone, avoid_density_threshold=0.85
        )

        if not path:
            # Fallback without density avoidance
            path = await self.neo4j.find_step_free_path(
                start_zone, target_zone, avoid_density_threshold=1.0
            )

        if not path:
            return NavigationResponse(
                path=[PathNode(name=start_zone, type="Zone")],
                total_distance_m=0,
                total_time_s=0,
                step_free=request.step_free,
                explanation="No accessible route found. Please contact a steward.",
            )

        total_dist = sum((p.get("distance_m") or 0) for p in path[1:])
        total_time = sum((p.get("estimated_time_s") or 0) for p in path[1:])
        step_free = all(p.get("step_free", True) for p in path[1:])

        path_nodes = [PathNode(**p) for p in path]
        avoid = None
        for p in path:
            if p.get("density", 0) > 0.85:
                avoid = p["name"]

        # LLM explanation (language generation — the GenAI value-add)
        explanation = await self._generate_explanation(
            path_nodes, request.language, request.step_free, avoid
        )

        await self.log_action(
            "navigation",
            {
                "from": request.start_location,
                "to": request.destination_intent,
                "language": request.language,
                "step_free": request.step_free,
            },
        )

        return NavigationResponse(
            path=path_nodes,
            total_distance_m=total_dist,
            total_time_s=total_time,
            step_free=step_free,
            explanation=explanation,
            avoid_reason=f"Avoided {avoid} due to congestion" if avoid else None,
        )

    async def _resolve_intent(
        self, start_zone: str, intent: str, step_free: bool
    ) -> tuple[str | None, str, str]:
        """Resolve a natural language intent to a specific graph node.

        Args:
            start_zone: The starting location.
            intent: The natural language destination query.
            step_free: Whether a step-free route is required.

        Returns:
            tuple: (target_node_name, target_node_type, display_name)
        """
        intent_lower = intent.lower().replace(" ", "_")
        if intent_lower in ("nearest_exit", "exit", "closest_exit"):
            exit_info = await self.neo4j.find_nearest_exit(start_zone, step_free)
            if exit_info:
                return start_zone, "Exit", exit_info["name"]
            return start_zone, "Exit", "Exit_North"
        if intent_lower in ("nearest_restroom", "restroom", "bathroom", "toilet"):
            rr = await self.neo4j.find_nearest_restroom(start_zone, accessible=step_free)
            if rr:
                return start_zone, "RestRoom", rr["name"]
            return start_zone, "RestRoom", "RR_1A"
        if intent_lower in ("medical", "first_aid", "nearest_medical", "emergency"):
            med = await self.neo4j.find_nearest_medical(start_zone)
            if med:
                return start_zone, "MedicalPoint", med["name"]
            return start_zone, "MedicalPoint", "Medical_North"
        if intent_lower in ("transit", "metro", "bus", "transport"):
            exit_info = await self.neo4j.find_nearest_exit(start_zone, step_free)
            if exit_info:
                transit_options = await self.neo4j.find_transit_for_gate(exit_info["name"])
                if transit_options:
                    return exit_info["name"], "TransitStop", transit_options[0]["name"]
                return exit_info["name"], "TransitStop", "TransitStop"
            return start_zone, "Transit", "TransitStop"
        if intent_lower.startswith("gate_"):
            return intent_lower.replace("gate_", "Gate_"), "Gate", intent_lower
        if intent_lower.startswith("zone_"):
            return intent_lower.replace("zone_", "Zone_"), "Zone", intent_lower
        # Default: assume it's a zone or gate name
        if intent_lower.startswith("section_"):
            zone = await self.neo4j.find_zone_for_section(
                intent_lower.replace("section_", "Section_")
            )
            return zone or start_zone, "Zone", intent_lower
        return start_zone, "Zone", intent_lower

    async def _generate_explanation(
        self,
        path: list[PathNode],
        language: str,
        step_free: bool,
        avoid: str | None,
    ) -> str:
        """Generate a natural-language explanation of the route using GenAI.

        Args:
            path: The calculated path nodes.
            language: The requested language code.
            step_free: Whether step-free routing was used.
            avoid: Optional zone that was avoided due to congestion.

        Returns:
            str: The generated explanation.
        """
        lang_name = LANGUAGE_NAMES.get(language, "English")
        path_str = " -> ".join(p.name for p in path)
        step_free_str = "step-free" if step_free else ""
        avoid_str = f"avoiding congested zone {avoid}" if avoid else ""
        prompt = f"""You are a friendly stadium guide for FIFA World Cup 2026 at AT&T Stadium.
Speak in {lang_name}.
The fan needs to travel this path: {path_str}.
{'The route must be ' + step_free_str + '.' if step_free_str else ''}
{avoid_str}
Write a short, clear, encouraging natural-language instruction (2-3 sentences) for a fan walking through the stadium. Include landmarks and approximate time."""

        cache_key = f"nav_explain:{language}:{path_str}:{step_free}:{avoid}"
        return await self.llm.call_cached(cache_key, prompt, ttl_seconds=300)
