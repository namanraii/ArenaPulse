"""Crowd simulator generating realistic match-day crowd dynamics."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

from app.graph.neo4j_client import Neo4jClient
from app.models import TransitMode, ZoneDensity

logger = structlog.get_logger()

ZONE_LABELS = {
    "Zone_1": "North Plaza",
    "Zone_2": "East Concourse",
    "Zone_3": "South Ramp",
    "Zone_4": "West Gate Queue",
    "Zone_5": "Transit Bridge",
    "Zone_6": "Accessible Services",
    "Zone_7": "Club Level",
    "Zone_8": "South Exit Corridor",
}


@dataclass
class MatchSchedule:
    match_start: datetime
    halftime_start: datetime
    halftime_end: datetime
    match_end: datetime


class CrowdSimulator:
    """Simulates realistic crowd density dynamics around match events."""

    def __init__(self, neo4j: Neo4jClient | None = None) -> None:
        self.neo4j = neo4j
        self.zones: list[str] = [f"Zone_{i}" for i in range(1, 9)]
        self.running = False
        self.task: asyncio.Task | None = None
        self._densities: dict[str, float] = {z: 0.45 + (i * 0.02) for i, z in enumerate(self.zones)}
        self._history: dict[str, list[float]] = {z: [] for z in self.zones}
        self._on_tick_callbacks: list = []
        self._density_timeline: list[dict] = []
        self._transit_split: dict[str, float] = {
            TransitMode.METRO.value: 0.35,
            TransitMode.BUS.value: 0.20,
            TransitMode.RIDESHARE.value: 0.25,
            TransitMode.WALK.value: 0.15,
            TransitMode.SHUTTLE.value: 0.05,
        }
        self._waste_bins: dict[str, float] = {
            "Bin_A1": 0.2,
            "Bin_A2": 0.3,
            "Bin_B1": 0.15,
            "Bin_B2": 0.4,
            "Bin_C1": 0.25,
            "Bin_C2": 0.1,
            "Bin_D1": 0.35,
            "Bin_D2": 0.2,
        }
        self._water_refills = 0
        self.schedule: MatchSchedule | None = None

    def set_schedule(self, schedule: MatchSchedule) -> None:
        self.schedule = schedule
        logger.info("simulator_schedule_set", schedule=schedule)

    def on_tick(self, callback) -> None:
        """Register async callback invoked after each simulation tick."""
        self._on_tick_callbacks.append(callback)

    async def start(self) -> None:
        """Start the crowd simulator loop."""
        self.running = True
        self.task = asyncio.create_task(self._loop())
        logger.info("simulator_started")

    async def stop(self) -> None:
        """Stop the crowd simulator loop and cancel the running task."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("simulator_stopped")

    async def _loop(self) -> None:
        """The main asynchronous simulation loop."""
        while self.running:
            self._tick()
            await self._push_to_graph()
            state = self.get_current_state()
            for callback in self._on_tick_callbacks:
                try:
                    await callback(state)
                except Exception as exc:
                    logger.warning("simulator_callback_failed", error=str(exc))
            await asyncio.sleep(5)

    def _tick(self) -> None:
        """Perform a single simulation tick to update crowd densities, transit splits, and waste bins."""
        now = datetime.now(timezone.utc)
        if self.schedule is None:
            phase = "generic"
            phase_factor = 0.5
        else:
            phase, phase_factor = self._match_phase(now)

        for zone in self.zones:
            current = self._densities[zone]
            # Base noise
            noise = random.gauss(0, 0.02)
            # Match-phase driven trend
            trend = self._phase_trend(phase, zone) * 0.05
            # Apply
            new_density = current + trend + noise
            # Bounds
            new_density = max(0.0, min(1.0, new_density))
            # Occasional spike in specific zones
            if phase in ("halftime", "post_match") and random.random() < 0.1:
                if zone in ("Zone_3", "Zone_4", "Zone_7"):
                    new_density = min(1.0, new_density + 0.15)

            self._densities[zone] = new_density
            self._history[zone].append(new_density)
            if len(self._history[zone]) > 20:
                self._history[zone].pop(0)

        # Slowly shift transit split
        if random.random() < 0.2:
            mode = random.choice(list(self._transit_split.keys()))
            shift = random.uniform(-0.03, 0.03)
            self._transit_split[mode] = max(0.05, min(0.60, self._transit_split[mode] + shift))
            # Normalize
            total = sum(self._transit_split.values())
            self._transit_split = {k: v / total for k, v in self._transit_split.items()}

        # Waste bins fill up during match
        if phase in ("first_half", "halftime", "second_half"):
            for b in self._waste_bins:
                self._waste_bins[b] = min(1.0, self._waste_bins[b] + random.uniform(0.0, 0.02))

        self._water_refills += random.randint(0, 5)

        avg_density = sum(self._densities.values()) / len(self._densities)
        self._density_timeline.append(
            {
                "time": datetime.now(timezone.utc).strftime("%H:%M"),
                "density": round(avg_density * 100),
            }
        )
        if len(self._density_timeline) > 60:
            self._density_timeline.pop(0)

    def _match_phase(self, now: datetime) -> tuple[str, float]:
        """Determine the current match phase based on the schedule.

        Args:
            now: The current datetime.

        Returns:
            tuple[str, float]: The match phase string and a base factor.
        """
        s = self.schedule
        if s is None:
            return "pre_match", 0.3
        if now < s.match_start:
            return "pre_match", 0.3
        if now < s.halftime_start:
            return "first_half", 0.6
        if now < s.halftime_end:
            return "halftime", 0.9
        if now < s.match_end:
            return "second_half", 0.6
        return "post_match", 0.85

    def _phase_trend(self, phase: str, zone: str) -> float:
        """Return a drift factor based on match phase and zone."""
        if phase == "pre_match":
            return 0.5  # filling up
        if phase == "first_half":
            return -0.1 if zone in ("Zone_1", "Zone_5") else 0.1
        if phase == "halftime":
            return 0.8 if zone in ("Zone_3", "Zone_4", "Zone_7") else 0.3
        if phase == "second_half":
            return -0.1
        if phase == "post_match":
            return -0.8 if zone in ("Zone_1", "Zone_5") else -0.5
        return 0.0

    async def _push_to_graph(self) -> None:
        if self.neo4j is None:
            return
        for zone, density in self._densities.items():
            try:
                await self.neo4j.update_zone_density(zone, density)
            except Exception as exc:
                logger.debug("graph_push_skipped", zone=zone, error=str(exc))

    def get_current_state(self) -> list[ZoneDensity]:
        """Get the current crowd density state for all zones.

        Returns:
            list[ZoneDensity]: A list of ZoneDensity objects representing the current state.
        """
        capacities = {
            "Zone_1": 12000,
            "Zone_2": 11500,
            "Zone_3": 11800,
            "Zone_4": 12200,
            "Zone_5": 11000,
            "Zone_6": 11300,
            "Zone_7": 11600,
            "Zone_8": 11567,
        }
        result = []
        for zone in self.zones:
            dens = self._densities[zone]
            cap = capacities[zone]
            hist = self._history.get(zone, [])
            trend = 0.0
            if len(hist) >= 2:
                trend = (hist[-1] - hist[-2]) * 12  # per minute (5s intervals -> 12 per min)
            result.append(
                ZoneDensity(
                    zone=zone,
                    density=round(dens, 3),
                    capacity=cap,
                    current_occupancy=int(dens * cap),
                    trend=round(trend, 3),
                )
            )
        return result

    def get_zones_for_frontend(self) -> list[dict]:
        """Return zone payloads enriched with labels for the UI heatmap."""
        return [
            {
                "name": z.zone,
                "label": ZONE_LABELS.get(z.zone, z.zone),
                "capacity": z.capacity,
                "density": z.density,
                "current_occupancy": z.current_occupancy,
                "trend": z.trend,
            }
            for z in self.get_current_state()
        ]

    def get_transit_state(self) -> dict[str, float]:
        """Get the current transit mode split.

        Returns:
            dict[str, float]: A dictionary mapping transit modes to their current proportions.
        """
        return dict(self._transit_split)

    def get_waste_state(self) -> dict[str, float]:
        """Get the current fill levels of all waste bins.

        Returns:
            dict[str, float]: A dictionary mapping bin IDs to their fill levels (0.0 to 1.0).
        """
        return dict(self._waste_bins)

    def get_density_timeline(self) -> list[dict]:
        """Return rolling average stadium density samples for charting."""
        return list(self._density_timeline)

    def get_water_refills(self) -> int:
        """Get the cumulative count of water bottle refills.

        Returns:
            int: The number of refills.
        """
        return self._water_refills
