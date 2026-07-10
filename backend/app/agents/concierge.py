"""ConciergeAgent — multilingual, retrieval-grounded fan chat."""

from __future__ import annotations

import re
import uuid

import structlog

from app.agents.base import BaseAgent
from app.constants import LANGUAGE_NAMES
from app.graph.neo4j_client import Neo4jClient
from app.models import ChatRequest, ChatResponse
from app.utils.llm_router import LLMRouter
from app.utils.security import sanitize_input

logger = structlog.get_logger()

INTENT_PATTERNS = {
    "navigation": r"\b(how do i get to|where is|directions to|navigate to|find|way to)\b",
    "transit": r"\b(metro|bus|train|subway|ride share|uber|taxi|shuttle|transport|how to leave|get home)\b",
    "schedule": r"\b(when|what time|kickoff|schedule|match start|halftime|full time|who is playing)\b",
    "prohibited": r"\b(can i bring|prohibited|allowed|bag policy|food|drink|camera|flag|banner)\b",
    "weather": r"\b(weather|rain|temperature|hot|cold|forecast|umbrella)\b",
    "sustainability": r"\b(eco|green|recycle|co2|carbon|sustainable|environment|bus vs car)\b",
    "facilities": r"\b(restroom|bathroom|toilet|food|concession|water|medical|first aid|wifi|atm)\b",
    "emergency": r"\b(emergency|help|lost|stolen|injured|medical|police|security)\b",
}


class ConciergeAgent(BaseAgent):
    """Multilingual fan concierge with retrieval-grounded responses."""

    name = "ConciergeAgent"

    def __init__(self, llm_router: LLMRouter, neo4j: Neo4jClient) -> None:
        super().__init__(llm_router, neo4j)
        self._sessions: dict[str, list[dict]] = {}

    async def process(self, input_data: ChatRequest) -> ChatResponse:
        """Process a chat request (implements BaseAgent)."""
        return await self.chat(input_data)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Handle a chat interaction with a fan.

        Args:
            request: The chat request containing message and language.

        Returns:
            ChatResponse: The agent's response and detected intent.
        """
        safe_message = sanitize_input(request.message, max_length=2000)
        intent = self._classify_intent(safe_message)
        language = request.language or "en"

        # Retrieve grounding facts
        sources = await self._retrieve_facts(intent, safe_message)

        # Build system prompt with grounding
        context_block = self._build_context_block(sources)
        system_prompt = f"""You are ArenaPulse, a helpful stadium concierge for FIFA World Cup 2026 at AT&T Stadium.
You answer in {LANGUAGE_NAMES.get(language, 'English')}.
Rules:
- Only use facts from the provided context. If you don't know, say so and suggest asking a steward.
- Be concise, friendly, and inclusive.
- Never invent stadium facts, times, or capacities.
{context_block}"""

        user_prompt = f"Fan asks: {safe_message}\nIntent detected: {intent}\nAnswer:"

        cache_key = f"concierge:{language}:{intent}:{hash(safe_message) % 100000}"
        response_text = await self.llm.call_cached(
            cache_key, user_prompt, system=system_prompt, model="flash", ttl_seconds=120
        )

        # Store session history (ephemeral, no PII)
        sid = request.session_id or str(uuid.uuid4())
        self._sessions.setdefault(sid, []).append({"role": "user", "content": safe_message})
        self._sessions[sid].append({"role": "assistant", "content": response_text})
        if len(self._sessions[sid]) > 10:
            self._sessions[sid] = self._sessions[sid][-10:]

        await self.log_action("concierge_chat", {"intent": intent, "language": language})

        return ChatResponse(
            response=response_text,
            sources=sources,
            detected_intent=intent,
            language=language,
        )

    def _classify_intent(self, message: str) -> str:
        """Classify the user's intent using regex patterns.

        Args:
            message: The user's message.

        Returns:
            str: The detected intent category.
        """
        lower = message.lower()
        for intent, pattern in INTENT_PATTERNS.items():
            if re.search(pattern, lower):
                return intent
        return "general"

    async def _retrieve_facts(self, intent: str, message: str) -> list[dict]:
        """Retrieve grounding facts from Neo4j based on intent.

        Args:
            intent: The classified intent.
            message: The original user message.

        Returns:
            list[dict]: Retrieved facts and contexts.
        """
        sources = []
        if intent == "navigation":
            # Extract potential zone/section names
            zones = re.findall(r"\b(Zone|Section|Gate|Exit)_[A-Z0-9]+\b", message, re.IGNORECASE)
            for z in zones:
                z_formatted = (
                    z.replace("zone_", "Zone_")
                    .replace("section_", "Section_")
                    .replace("gate_", "Gate_")
                )
                facts = await self.neo4j.get_stadium_facts("Zone", z_formatted)
                if facts:
                    sources.append({"type": "zone", "name": z_formatted, "facts": facts[0]})
        if intent == "transit":
            for gate in ["Gate_A", "Gate_B", "Gate_C", "Gate_D"]:
                transit = await self.neo4j.find_transit_for_gate(gate)
                if transit:
                    sources.append({"type": "transit", "gate": gate, "options": transit})
        if intent == "facilities":
            # Return restroom/medical info for all zones
            zones = await self.neo4j.get_all_zones()
            sources.append({"type": "facilities", "zones": zones})
        return sources

    def _build_context_block(self, sources: list[dict]) -> str:
        """Format the retrieved sources into a system prompt block.

        Args:
            sources: List of retrieved facts.

        Returns:
            str: Formatted context block.
        """
        if not sources:
            return ""
        lines = ["Context:"]
        for s in sources:
            lines.append(f"- {s}")
        return "\n".join(lines)
