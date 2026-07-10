"""CrowdSentinelAgent — classical anomaly detection + LLM summarization."""

from __future__ import annotations

import statistics
from datetime import datetime, timezone

import structlog

from app.agents.base import BaseAgent
from app.database import create_ops_action
from app.models import CrowdAlert, CrowdAlertSeverity, OpsActionPriority, ZoneDensity
from app.utils.llm_router import LLMRouter
from app.graph.neo4j_client import Neo4jClient

logger = structlog.get_logger()


class CrowdSentinelAgent(BaseAgent):
    """Detects crowd anomalies using classical stats; uses LLM for incident summaries."""

    name = "CrowdSentinelAgent"

    DENSITY_CRITICAL = 0.90
    DENSITY_HIGH = 0.85
    DENSITY_MEDIUM = 0.70
    Z_SCORE_THRESHOLD = 2.5
    PREDICTION_WINDOW_MIN = 10

    def __init__(self, llm_router: LLMRouter, neo4j: Neo4jClient) -> None:
        super().__init__(llm_router, neo4j)
        self._history: dict[str, list[float]] = {}
        self._last_alert_time: dict[str, float] = {}

    async def process(self, input_data: list[ZoneDensity]) -> list[CrowdAlert]:
        """Process a batch of zone densities (implements BaseAgent)."""
        return await self.process_density_batch(input_data)

    async def process_density_batch(self, zones: list[ZoneDensity]) -> list[CrowdAlert]:
        """Process a batch of zone densities and return any generated alerts.

        Args:
            zones: List of current zone densities.

        Returns:
            list[CrowdAlert]: Generated alerts.
        """
        alerts: list[CrowdAlert] = []
        for z in zones:
            self._history.setdefault(z.zone, []).append(z.density)
            if len(self._history[z.zone]) > 20:
                self._history[z.zone].pop(0)

            alert = self._check_zone(z)
            if alert:
                alerts.append(alert)

        now_ts = datetime.now(timezone.utc).timestamp()
        for alert in alerts:
            if alert.severity in (CrowdAlertSeverity.HIGH, CrowdAlertSeverity.CRITICAL):
                last_time = getattr(self, "_last_alert_time", {}).get(alert.zone, 0)
                if now_ts - last_time < 60:
                    continue
                self._last_alert_time[alert.zone] = now_ts
                summary = await self._generate_summary(alert)
                alert.message = summary
                # Push to ops_actions
                await create_ops_action(
                    title=f"Crowd Alert: {alert.zone}",
                    description=alert.message,
                    reasoning=alert.suggested_mitigation,
                    priority=OpsActionPriority.CRITICAL if alert.severity == CrowdAlertSeverity.CRITICAL else OpsActionPriority.HIGH,
                    recommended_by="CrowdSentinelAgent",
                    affected_zones=[alert.zone],
                    affected_population=alert.affected_population,
                    time_to_impact_min=alert.predicted_crossing_time_min,
                )

        if alerts:
            await self.log_action("crowd_alert_batch", {"count": len(alerts)})
        return alerts

    def _check_zone(self, z: ZoneDensity) -> CrowdAlert | None:
        """Check a single zone for anomalies.

        Args:
            z: The zone density to check.

        Returns:
            CrowdAlert | None: An alert if an anomaly is detected, else None.
        """
        hist = self._history.get(z.zone, [])
        severity: CrowdAlertSeverity | None = None
        predicted_cross: float | None = None

        # Absolute thresholds
        if z.density >= self.DENSITY_CRITICAL:
            severity = CrowdAlertSeverity.CRITICAL
        elif z.density >= self.DENSITY_HIGH:
            severity = CrowdAlertSeverity.HIGH

        # Statistical anomaly (z-score)
        if len(hist) >= 5 and severity is None:
            mean = statistics.mean(hist[-5:])
            try:
                stdev = statistics.stdev(hist[-5:])
            except statistics.StatisticsError:
                stdev = 0.0
            z_score = (z.density - mean) / stdev if stdev > 0 else 0.0
            if z_score > self.Z_SCORE_THRESHOLD:
                severity = CrowdAlertSeverity.MEDIUM

        # Predictive: trend crossing threshold
        if z.trend > 0 and z.density < self.DENSITY_CRITICAL:
            remaining = self.DENSITY_CRITICAL - z.density
            if z.trend > 0:
                minutes_to_cross = remaining / z.trend
                if minutes_to_cross <= self.PREDICTION_WINDOW_MIN:
                    severity = severity or CrowdAlertSeverity.HIGH
                    predicted_cross = round(minutes_to_cross, 1)

        if severity is None:
            return None

        # Determine mitigation suggestion based on severity and zone
        mitigation = self._suggest_mitigation(z, severity)
        affected = int(z.density * z.capacity)

        return CrowdAlert(
            id=f"alert-{z.zone}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            zone=z.zone,
            severity=severity,
            message=f"{z.zone} density at {z.density:.0%}",
            detected_at=datetime.now(timezone.utc),
            density=z.density,
            predicted_crossing_time_min=predicted_cross,
            suggested_mitigation=mitigation,
            affected_population=affected,
        )

    def _suggest_mitigation(self, z: ZoneDensity, severity: CrowdAlertSeverity) -> str:
        """Suggest a mitigation strategy based on severity.

        Args:
            z: The zone density object.
            severity: The alert severity.

        Returns:
            str: The suggested mitigation.
        """
        if severity == CrowdAlertSeverity.CRITICAL:
            return f"Open overflow exits for {z.zone}. Deploy stewards to redirect flow to adjacent lower-density zones."
        if severity == CrowdAlertSeverity.HIGH:
            return f"Prepare overflow routing. Announce nearby less-crowded exit via PA/digital boards."
        return f"Monitor {z.zone} closely. Increase concourse patrol frequency."

    async def _generate_summary(self, alert: CrowdAlert) -> str:
        """Generate a concise summary of the alert using the LLM.

        Args:
            alert: The generated crowd alert.

        Returns:
            str: A one-sentence summary.
        """
        prompt = f"""You are a stadium operations AI summarizing a crowd alert for control-room staff.
Zone: {alert.zone}
Current density: {alert.density:.0%} (if known from context)
Severity: {alert.severity.value}
Predicted time to critical threshold: {alert.predicted_crossing_time_min or 'N/A'} minutes
Suggested mitigation: {alert.suggested_mitigation}
Write a single concise sentence summarizing the situation and the recommended action."""
        cache_key = f"sentinel_alert:{alert.zone}:{alert.severity.value}:{alert.suggested_mitigation}"
        return await self.llm.call_cached(cache_key, prompt, ttl_seconds=300, temperature=0.2)
