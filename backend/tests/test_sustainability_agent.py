"""Unit tests for SustainabilityAgent summary, tips parsing, and transit nudges."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.models import TransitMode


@pytest.mark.asyncio
async def test_summary_uses_default_split_when_simulator_not_synced(sustainability):
    summary = await sustainability.get_summary()

    # Default split: 0.35*0.04 + 0.20*0.07 + 0.25*0.18 + 0.15*0 + 0.05*0.08 = 0.077 kg/fan
    assert summary.estimated_co2_kg == pytest.approx(77.0)
    # Green ratio 0.75 -> 75, minus avg waste 0.2 * 30 = 6
    assert summary.sustainability_score == 69
    assert summary.water_refill_usage == 0
    assert len(summary.waste_bin_fill_pct) == 8
    assert set(summary.transit_split) == set(TransitMode)


@pytest.mark.asyncio
async def test_update_from_simulator_drives_summary_and_copies_inputs(sustainability):
    transit = {"metro": 1.0}
    waste = {"Bin_1": 0.0}
    sustainability.update_from_simulator(transit, waste, water=42)

    # Later mutation of the simulator's dicts must not leak into the agent
    transit["rideshare"] = 1.0
    waste["Bin_1"] = 1.0

    summary = await sustainability.get_summary()
    assert summary.transit_split == {TransitMode.METRO: 1.0}
    assert summary.estimated_co2_kg == pytest.approx(40.0)
    assert summary.sustainability_score == 100
    assert summary.water_refill_usage == 42


def test_score_is_clamped_to_zero(sustainability):
    assert sustainability._calculate_score({"rideshare": 1.0}, {"b": 1.0}) == 0


def test_score_assumes_half_full_bins_when_no_waste_data(sustainability):
    # Green ratio 1.0 -> 100, minus default avg waste 0.5 * 30 = 15
    assert sustainability._calculate_score({"walk": 1.0}, {}) == 85


@pytest.mark.asyncio
async def test_tips_are_split_stripped_and_capped_at_three(sustainability, mock_llm):
    mock_llm.call_cached = AsyncMock(
        return_value="- Take the metro\n• Refill bottles\n\nRecycle\nExtra"
    )
    tips = await sustainability._generate_tips({}, 0.0)
    assert tips == ["Take the metro", "Refill bottles", "Recycle"]


@pytest.mark.asyncio
async def test_tips_fall_back_when_llm_returns_nothing(sustainability, mock_llm):
    mock_llm.call_cached = AsyncMock(return_value="  \n\n")
    tips = await sustainability._generate_tips({}, 0.0)
    assert len(tips) == 3
    assert "public transit" in tips[0]


@pytest.mark.asyncio
async def test_transit_recommendation_without_data_returns_error(sustainability, mock_neo4j):
    mock_neo4j.find_transit_for_gate = AsyncMock(return_value=[])
    result = await sustainability.get_transit_recommendation("Gate_A", "Downtown")
    assert result == {"error": "No transit data for gate"}


@pytest.mark.asyncio
async def test_transit_recommendation_picks_shortest_wait(sustainability, mock_neo4j, mock_llm):
    mock_neo4j.find_transit_for_gate = AsyncMock(
        return_value=[
            {"mode": "rideshare", "wait": 15},
            {"mode": "metro", "wait": 3},
            {"mode": "bus", "wait": 8},
        ]
    )
    result = await sustainability.get_transit_recommendation("Gate_A", "Downtown", "es")

    assert result["best_mode"] == "metro"
    assert result["best_wait_min"] == 3
    # (rideshare 0.18 - metro 0.04) kg/km * 5 km
    assert result["co2_saved_kg"] == pytest.approx(0.7)
    assert result["nudge"] == "Cached response"
    assert mock_llm.call_cached.await_args.args[0] == "transit_nudge:Gate_A:es"
