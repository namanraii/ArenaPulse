"""SustainabilityAgent — eco-metrics and transit nudges."""

from __future__ import annotations

import structlog

from app.agents.base import BaseAgent
from app.graph.neo4j_client import Neo4jClient
from app.models import SustainabilitySummary, TransitMode
from app.utils.llm_router import LLMRouter

logger = structlog.get_logger()

TRANSIT_CO2 = {
    TransitMode.METRO.value: 0.04,
    TransitMode.BUS.value: 0.07,
    TransitMode.SHUTTLE.value: 0.08,
    TransitMode.WALK.value: 0.0,
    TransitMode.RIDESHARE.value: 0.18,
}

TRANSIT_SPEED_KMH = {
    TransitMode.METRO.value: 35,
    TransitMode.BUS.value: 20,
    TransitMode.SHUTTLE.value: 25,
    TransitMode.WALK.value: 5,
    TransitMode.RIDESHARE.value: 30,
}


class SustainabilityAgent(BaseAgent):
    """Tracks sustainability KPIs and generates eco-nudges."""

    name = "SustainabilityAgent"

    def __init__(self, llm_router: LLMRouter, neo4j: Neo4jClient) -> None:
        super().__init__(llm_router, neo4j)
        self._transit_split: dict[str, float] = {}
        self._waste_bins: dict[str, float] = {}
        self._water_refills = 0

    def update_from_simulator(
        self, transit: dict[str, float], waste: dict[str, float], water: int
    ) -> None:
        """Sync sustainability KPIs from the live crowd simulator."""
        self._transit_split = dict(transit)
        self._waste_bins = dict(waste)
        self._water_refills = water

    async def process(self, input_data: dict) -> SustainabilitySummary:
        """Process an input dictionary to get the summary (implements BaseAgent)."""
        return await self.get_summary()

    async def get_summary(self) -> SustainabilitySummary:
        """Get the current sustainability summary.

        Returns:
            SustainabilitySummary: Metrics and tips.
        """
        split = self._transit_split or {
            TransitMode.METRO.value: 0.35,
            TransitMode.BUS.value: 0.20,
            TransitMode.RIDESHARE.value: 0.25,
            TransitMode.WALK.value: 0.15,
            TransitMode.SHUTTLE.value: 0.05,
        }
        waste = self._waste_bins or {f"Bin_{i}": 0.2 for i in range(1, 9)}
        water = self._water_refills or 0

        total_co2 = sum(split.get(m.value, 0) * TRANSIT_CO2[m.value] * 1000 for m in TransitMode)
        score = self._calculate_score(split, waste)

        # Generate eco-tips via LLM
        tips = await self._generate_tips(split, total_co2)

        transit_split_enum = {TransitMode(k): v for k, v in split.items()}

        return SustainabilitySummary(
            transit_split=transit_split_enum,
            estimated_co2_kg=round(total_co2, 2),
            sustainability_score=score,
            eco_tips=tips,
            waste_bin_fill_pct=waste,
            water_refill_usage=water,
        )

    async def get_transit_recommendation(
        self, from_gate: str, to_destination: str, language: str = "en"
    ) -> dict:
        """Generate a transit recommendation and eco-nudge.

        Args:
            from_gate: The gate the fan is leaving from.
            to_destination: The final destination.
            language: The language for the nudge.

        Returns:
            dict: The best transit mode, wait time, CO2 saved, and nudge text.
        """
        transit = await self.neo4j.find_transit_for_gate(from_gate)
        if not transit:
            return {"error": "No transit data for gate"}

        best = min(transit, key=lambda t: t.get("wait", 99))
        worst = max(transit, key=lambda t: t.get("wait", 0))
        mode_best = best.get("mode", "metro")
        mode_worst = worst.get("mode", "rideshare")

        co2_saved = (TRANSIT_CO2.get(mode_worst, 0.15) - TRANSIT_CO2.get(mode_best, 0.05)) * 5
        prompt = f"""You are a sustainability advisor for stadium fans.
Language: {language}.
Best option: {mode_best} (wait {best.get('wait')} min).
Worst option: {mode_worst} (wait {worst.get('wait')} min).
CO2 saved by choosing best: ~{co2_saved:.1f} kg per 5km trip.
Write a short, punchy eco-nudge (1 sentence) encouraging fans to take the greener option."""

        nudge = await self.llm.call_cached(
            f"transit_nudge:{from_gate}:{language}", prompt, model="flash", ttl_seconds=60
        )
        return {
            "best_mode": mode_best,
            "best_wait_min": best.get("wait"),
            "co2_saved_kg": round(co2_saved, 2),
            "nudge": nudge,
        }

    def _calculate_score(self, split: dict[str, float], waste: dict[str, float]) -> int:
        """Calculate the overall sustainability score.

        Args:
            split: The transit mode split.
            waste: The waste bin fill percentages.

        Returns:
            int: A score from 0 to 100.
        """
        # Higher score for greener transit + lower waste
        green_ratio = (
            split.get(TransitMode.METRO.value, 0)
            + split.get(TransitMode.BUS.value, 0)
            + split.get(TransitMode.WALK.value, 0)
            + split.get(TransitMode.SHUTTLE.value, 0)
        )
        avg_waste = sum(waste.values()) / len(waste) if waste else 0.5
        raw = (green_ratio * 100) - (avg_waste * 30)
        return max(0, min(100, int(raw)))

    async def _generate_tips(self, split: dict[str, float], co2: float) -> list[str]:
        """Generate dynamic eco-tips using the LLM based on current metrics.

        Args:
            split: Transit mode split.
            co2: Estimated CO2 emissions.

        Returns:
            list[str]: Three concise eco-tips.
        """
        prompt = f"""Current transit split: {split}
Estimated CO2 per 1000 fans: {co2:.2f} kg.
Generate 3 short, actionable sustainability tips for stadium fans. One sentence each."""
        raw = await self.llm.call_cached("sustain_tips", prompt, model="flash", ttl_seconds=300)
        tips = [t.strip("-• ") for t in raw.split("\n") if t.strip()]
        return tips[:3] or [
            "Consider public transit to reduce emissions.",
            "Use refillable water bottles.",
            "Recycle at designated bins.",
        ]
