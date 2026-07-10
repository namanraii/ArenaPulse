"""Seed AT&T Stadium topology into Neo4j."""

from __future__ import annotations

import asyncio
import structlog

from app.config import settings
from app.graph.neo4j_client import init_driver, close_driver, get_driver
from app.graph.neo4j_client import init_driver, close_driver, get_driver

logger = structlog.get_logger()

async def seed_stadium() -> None:
    await init_driver()
    driver = get_driver()

    # Clear existing
    await driver.execute_query("MATCH (n) DETACH DELETE n")

    # Stadium
    await driver.execute_query(
        """
        CREATE (s:Stadium {name: "AT&T Stadium", city: "Arlington", capacity: 92967, country: "USA"})
        """
    )

    # Gates
    gates = ["Gate_A", "Gate_B", "Gate_C", "Gate_D"]
    for g in gates:
        await driver.execute_query(
            "CREATE (g:Gate {name: $name, entry_type: 'general'})",
            name=g,
        )

    # Zones with capacities
    zones = [
        ("Zone_1", 12000, 0.0),
        ("Zone_2", 11500, 0.0),
        ("Zone_3", 11800, 0.0),
        ("Zone_4", 12200, 0.0),
        ("Zone_5", 11000, 0.0),
        ("Zone_6", 11300, 0.0),
        ("Zone_7", 11600, 0.0),
        ("Zone_8", 11567, 0.0),
    ]
    for name, cap, dens in zones:
        await driver.execute_query(
            "CREATE (z:Zone {name: $name, capacity: $capacity, current_density: $density})",
            name=name,
            capacity=cap,
            density=dens,
        )

    # Sections (2 per zone for simplicity)
    section_num = 100
    for z in range(1, 9):
        for _ in range(2):
            section_num += 1
            await driver.execute_query(
                """
                MATCH (zone:Zone {name: $zone})
                CREATE (s:Section {name: $sname})-[:LOCATED_IN]->(zone)
                """,
                zone=f"Zone_{z}",
                sname=f"Section_{section_num}",
            )

    # Exits
    exits = [
        ("Exit_North", True),
        ("Exit_South", True),
        ("Exit_East", False),
        ("Exit_West", True),
    ]
    for name, step_free in exits:
        await driver.execute_query(
            "CREATE (e:Exit {name: $name, step_free: $step_free})",
            name=name,
            step_free=step_free,
        )

    # Medical Points
    await driver.execute_query("CREATE (m:MedicalPoint {name: 'Medical_North', level: 'basic'})")
    await driver.execute_query("CREATE (m:MedicalPoint {name: 'Medical_South', level: 'advanced'})")

    # Transit Stops
    transit = [
        ("Metro_Blue_Line", "metro", 5),
        ("Bus_Central", "bus", 8),
        ("Rideshare_Zone_A", "rideshare", 12),
        ("Pedestrian_Walk", "walk", 0),
    ]
    for name, mode, wait in transit:
        await driver.execute_query(
            "CREATE (t:TransitStop {name: $name, mode: $mode, avg_wait_min: $wait})",
            name=name,
            mode=mode,
            wait=wait,
        )

    # Restrooms
    restrooms = [
        ("RR_1A", True), ("RR_1B", False),
        ("RR_2A", True), ("RR_2B", False),
        ("RR_3A", True), ("RR_3B", False),
        ("RR_4A", True), ("RR_4B", False),
    ]
    for name, accessible in restrooms:
        await driver.execute_query(
            "CREATE (r:RestRoom {name: $name, accessible: $accessible})",
            name=name,
            accessible=accessible,
        )

    # Gate -> Zone
    gate_zone = [
        ("Gate_A", "Zone_1"), ("Gate_A", "Zone_2"),
        ("Gate_B", "Zone_3"), ("Gate_B", "Zone_4"),
        ("Gate_C", "Zone_5"), ("Gate_C", "Zone_6"),
        ("Gate_D", "Zone_7"), ("Gate_D", "Zone_8"),
    ]
    for g, z in gate_zone:
        await driver.execute_query(
            "MATCH (gate:Gate {name: $g}), (zone:Zone {name: $z}) CREATE (gate)-[:LEADS_TO]->(zone)",
            g=g,
            z=z,
        )

    # Zone CONNECTS_TO (bidirectional concourse connections)
    connections = [
        ("Zone_1", "Zone_2", 120, True, 90),
        ("Zone_2", "Zone_3", 150, True, 110),
        ("Zone_3", "Zone_4", 100, True, 75),
        ("Zone_4", "Zone_5", 180, False, 140),
        ("Zone_5", "Zone_6", 130, True, 100),
        ("Zone_6", "Zone_7", 160, True, 120),
        ("Zone_7", "Zone_8", 110, True, 80),
        ("Zone_8", "Zone_1", 200, True, 150),
        ("Zone_1", "Zone_5", 250, True, 180),
        ("Zone_2", "Zone_6", 220, True, 160),
        ("Zone_3", "Zone_7", 210, True, 155),
        ("Zone_4", "Zone_8", 230, False, 170),
    ]
    for a, b, dist, step_free, time in connections:
        await driver.execute_query(
            """
            MATCH (za:Zone {name: $a}), (zb:Zone {name: $b})
            CREATE (za)-[:CONNECTS_TO {distance_m: $dist, step_free: $sf, avg_walk_time_s: $time}]->(zb)
            CREATE (zb)-[:CONNECTS_TO {distance_m: $dist, step_free: $sf, avg_walk_time_s: $time}]->(za)
            """,
            a=a,
            b=b,
            dist=dist,
            sf=step_free,
            time=time,
        )

    # Zone -> Nearest Exit
    zone_exit = [
        ("Zone_1", "Exit_North"), ("Zone_2", "Exit_North"),
        ("Zone_3", "Exit_East"), ("Zone_4", "Exit_East"),
        ("Zone_5", "Exit_South"), ("Zone_6", "Exit_South"),
        ("Zone_7", "Exit_West"), ("Zone_8", "Exit_West"),
    ]
    for z, e in zone_exit:
        await driver.execute_query(
            "MATCH (zone:Zone {name: $z}), (exit:Exit {name: $e}) CREATE (zone)-[:NEAREST_EXIT]->(exit)",
            z=z,
            e=e,
        )

    # Zone -> Nearest Medical
    zone_med = [
        ("Zone_1", "Medical_North"), ("Zone_2", "Medical_North"),
        ("Zone_3", "Medical_North"), ("Zone_4", "Medical_North"),
        ("Zone_5", "Medical_South"), ("Zone_6", "Medical_South"),
        ("Zone_7", "Medical_South"), ("Zone_8", "Medical_South"),
    ]
    for z, m in zone_med:
        await driver.execute_query(
            "MATCH (zone:Zone {name: $z}), (med:MedicalPoint {name: $m}) CREATE (zone)-[:NEAREST_MEDICAL]->(med)",
            z=z,
            m=m,
        )

    # Gate -> Nearest Transit
    gate_transit = [
        ("Gate_A", "Metro_Blue_Line"),
        ("Gate_B", "Bus_Central"),
        ("Gate_C", "Rideshare_Zone_A"),
        ("Gate_D", "Pedestrian_Walk"),
    ]
    for g, t in gate_transit:
        await driver.execute_query(
            "MATCH (gate:Gate {name: $g}), (tr:TransitStop {name: $t}) CREATE (gate)-[:NEAREST_TRANSIT]->(tr)",
            g=g,
            t=t,
        )

    # Zone -> Nearest Restroom (alternating)
    zone_rr = [
        ("Zone_1", "RR_1A"), ("Zone_2", "RR_1B"),
        ("Zone_3", "RR_2A"), ("Zone_4", "RR_2B"),
        ("Zone_5", "RR_3A"), ("Zone_6", "RR_3B"),
        ("Zone_7", "RR_4A"), ("Zone_8", "RR_4B"),
    ]
    for z, r in zone_rr:
        await driver.execute_query(
            "MATCH (zone:Zone {name: $z}), (rr:RestRoom {name: $r}) CREATE (zone)-[:NEAREST_RESTROOM]->(rr)",
            z=z,
            r=r,
        )

    logger.info("✅ AT&T Stadium seeded successfully with 8 zones, 4 gates, 16 sections, 4 exits, 2 medical points, 4 transit stops.")
    await close_driver()


if __name__ == "__main__":
    asyncio.run(seed_stadium())
