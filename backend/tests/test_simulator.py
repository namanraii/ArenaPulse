"""Tests for crowd simulator dynamics."""

from datetime import datetime, timedelta, timezone

from app.simulator.crowd_simulator import CrowdSimulator, MatchSchedule


def test_simulator_produces_bounded_densities() -> None:
    sim = CrowdSimulator(neo4j=None)
    sim._tick()
    state = sim.get_current_state()
    assert len(state) == 8
    for zone in state:
        assert 0.0 <= zone.density <= 1.0
        assert zone.capacity > 0


def test_simulator_match_phases() -> None:
    sim = CrowdSimulator(neo4j=None)
    now = datetime.now(timezone.utc)
    sim.set_schedule(
        MatchSchedule(
            match_start=now - timedelta(minutes=50),
            halftime_start=now - timedelta(minutes=5),
            halftime_end=now + timedelta(minutes=10),
            match_end=now + timedelta(minutes=55),
        )
    )
    phase, factor = sim._match_phase(now)
    assert phase == "halftime"
    assert factor == 0.9


def test_simulator_frontend_payload_includes_labels() -> None:
    sim = CrowdSimulator(neo4j=None)
    sim._tick()
    zones = sim.get_zones_for_frontend()
    assert zones[0]["label"]
    assert "density" in zones[0]
