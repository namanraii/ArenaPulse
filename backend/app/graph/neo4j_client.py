"""Async Neo4j client for stadium knowledge graph operations."""

from __future__ import annotations

import neo4j
import structlog

from app.config import settings

logger = structlog.get_logger()

_driver: neo4j.AsyncDriver | None = None

ALLOWED_ENTITY_TYPES = frozenset(
    {"Zone", "Gate", "Exit", "MedicalPoint", "RestRoom", "Section", "TransitStop"}
)


async def init_driver() -> None:
    """Initialize the global Neo4j driver connection."""
    global _driver
    _driver = neo4j.AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    await _driver.verify_connectivity()
    logger.info("neo4j_connected", uri=settings.neo4j_uri)


async def close_driver() -> None:
    """Close the global Neo4j driver connection."""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


def get_driver() -> neo4j.AsyncDriver:
    """Get the active Neo4j driver instance.

    Returns:
        neo4j.AsyncDriver: The active driver.

    Raises:
        RuntimeError: If the driver has not been initialized.
    """
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialized")
    return _driver


class Neo4jClient:
    """High-level client for stadium topology queries."""

    def __init__(self) -> None:
        self.driver = get_driver()

    async def find_step_free_path(
        self,
        start_zone: str,
        end_zone: str,
        avoid_density_threshold: float = 0.85,
    ) -> list[dict]:
        """Find the shortest path between two zones, avoiding high-density zones and optionally preferring step-free routes.

        Args:
            start_zone: Name of the starting zone.
            end_zone: Name of the destination zone.
            avoid_density_threshold: The density threshold to avoid (default: 0.85).

        Returns:
            list[dict]: A list of nodes and relationships forming the path.
        """
        # First try strict step-free
        query = """
        MATCH path = shortestPath(
            (start:Zone {name: $start})-[:CONNECTS_TO*]-(end:Zone {name: $end})
        )
        WHERE ALL(r IN relationships(path) WHERE r.step_free = true)
          AND ALL(n IN nodes(path) WHERE n.current_density IS NULL OR n.current_density < $threshold)
        RETURN [n in nodes(path) | {name: n.name, type: labels(n)[0]}] AS nodes,
               [r in relationships(path) | {distance: r.distance_m, step_free: r.step_free, time: r.avg_walk_time_s}] AS rels
        LIMIT 1
        """
        result = await self.driver.execute_query(
            query, start=start_zone, end=end_zone, threshold=avoid_density_threshold
        )
        if result.records:
            return self._normalize_path(result.records[0]["nodes"], result.records[0]["rels"])

        # Fallback: any path avoiding high density
        query2 = """
        MATCH path = shortestPath(
            (start:Zone {name: $start})-[:CONNECTS_TO*]-(end:Zone {name: $end})
        )
        WHERE ALL(n IN nodes(path) WHERE n.current_density IS NULL OR n.current_density < $threshold)
        RETURN [n in nodes(path) | {name: n.name, type: labels(n)[0]}] AS nodes,
               [r in relationships(path) | {distance: r.distance_m, step_free: r.step_free, time: r.avg_walk_time_s}] AS rels
        LIMIT 1
        """
        result2 = await self.driver.execute_query(
            query2, start=start_zone, end=end_zone, threshold=avoid_density_threshold
        )
        if result2.records:
            return self._normalize_path(result2.records[0]["nodes"], result2.records[0]["rels"])
        return []

    async def find_nearest_exit(self, zone: str, step_free: bool = False) -> dict | None:
        """Find the nearest exit from a given zone.

        Args:
            zone: The starting zone name.
            step_free: Whether a step-free route to the exit is required.

        Returns:
            dict | None: Information about the nearest exit, or None if not found.
        """
        query = """
        MATCH (z:Zone {name: $zone})-[:CONNECTS_TO*0..3]-(e:Exit)
        WITH e, min(length(shortestPath((z)-[:CONNECTS_TO*]-(e)))) AS dist
        RETURN e.name AS name, e.step_free AS step_free
        ORDER BY dist
        LIMIT 1
        """
        # Simplified: use explicit NEAREST_EXIT relationship
        query = """
        MATCH (z:Zone {name: $zone})-[:NEAREST_EXIT]->(e:Exit)
        RETURN e.name AS name, e.step_free AS step_free
        """
        result = await self.driver.execute_query(query, zone=zone)
        if result.records:
            return dict(result.records[0])
        return None

    async def find_nearest_medical(self, zone: str) -> dict | None:
        """Find the nearest medical point to a given zone.

        Args:
            zone: The starting zone name.

        Returns:
            dict | None: Information about the nearest medical point, or None if not found.
        """
        query = """
        MATCH (z:Zone {name: $zone})-[:NEAREST_MEDICAL]->(m:MedicalPoint)
        RETURN m.name AS name
        """
        result = await self.driver.execute_query(query, zone=zone)
        if result.records:
            return dict(result.records[0])
        return None

    async def find_nearest_restroom(self, zone: str, accessible: bool = False) -> dict | None:
        """Find the nearest restroom to a given zone.

        Args:
            zone: The starting zone name.
            accessible: Whether an accessible restroom is required.

        Returns:
            dict | None: Information about the nearest restroom, or None if not found.
        """
        query = """
        MATCH (z:Zone {name: $zone})-[:NEAREST_RESTROOM]->(r:RestRoom)
        WHERE $accessible = false OR r.accessible = true
        RETURN r.name AS name, r.accessible AS accessible
        LIMIT 1
        """
        result = await self.driver.execute_query(query, zone=zone, accessible=accessible)
        if result.records:
            return dict(result.records[0])
        return None

    async def get_zone_density(self, zone: str) -> float:
        """Get the current crowd density of a zone.

        Args:
            zone: The zone name.

        Returns:
            float: The density value (0.0 to 1.0).
        """
        query = "MATCH (z:Zone {name: $name}) RETURN z.current_density AS density"
        result = await self.driver.execute_query(query, name=zone)
        if result.records:
            return result.records[0]["density"] or 0.0
        return 0.0

    async def update_zone_density(self, zone: str, density: float) -> None:
        """Update the crowd density of a zone.

        Args:
            zone: The zone name.
            density: The new density value.
        """
        query = """
        MATCH (z:Zone {name: $name})
        SET z.current_density = $density, z.updated_at = datetime()
        """
        await self.driver.execute_query(query, name=zone, density=density)

    async def get_all_zones(self) -> list[dict]:
        """Retrieve all zones and their capacities/densities.

        Returns:
            list[dict]: A list of zone information dictionaries.
        """
        query = """
        MATCH (z:Zone)
        RETURN z.name AS name, z.capacity AS capacity, z.current_density AS density
        ORDER BY z.name
        """
        result = await self.driver.execute_query(query)
        return [dict(r) for r in result.records]

    async def get_stadium_facts(self, entity_type: str, name: str) -> list[dict]:
        """Retrieve properties for a specific entity in the stadium graph.

        Args:
            entity_type: The node label (e.g., 'Zone', 'Gate').
            name: The name of the entity.

        Returns:
            list[dict]: A list of property dictionaries for matching nodes.
        """
        if entity_type not in ALLOWED_ENTITY_TYPES:
            return []
        query = f"""
        MATCH (n:{entity_type} {{name: $name}})
        RETURN properties(n) AS props
        """
        result = await self.driver.execute_query(query, name=name)
        return [dict(r["props"]) for r in result.records]

    async def find_zone_for_section(self, section: str) -> str | None:
        """Find the zone containing a specific seating section.

        Args:
            section: The section name.

        Returns:
            str | None: The containing zone name, or None if not found.
        """
        query = """
        MATCH (s:Section {name: $section})-[:LOCATED_IN]->(z:Zone)
        RETURN z.name AS zone
        """
        result = await self.driver.execute_query(query, section=section)
        if result.records:
            return result.records[0]["zone"]
        return None

    async def find_transit_for_gate(self, gate: str) -> list[dict]:
        """Find transit options available near a specific gate.

        Args:
            gate: The gate name.

        Returns:
            list[dict]: A list of transit options.
        """
        query = """
        MATCH (g:Gate {name: $gate})-[:NEAREST_TRANSIT]->(t:TransitStop)
        RETURN t.name AS name, t.mode AS mode, t.avg_wait_min AS wait
        """
        result = await self.driver.execute_query(query, gate=gate)
        return [dict(r) for r in result.records]

    def _normalize_path(self, nodes: list, rels: list) -> list[dict]:
        path = []
        for i, node in enumerate(nodes):
            entry = {"name": node["name"], "type": node["type"]}
            if i < len(rels):
                entry["distance_m"] = rels[i].get("distance", 0)
                entry["step_free"] = rels[i].get("step_free", True)
                entry["estimated_time_s"] = rels[i].get("time", 0)
            path.append(entry)
        return path
