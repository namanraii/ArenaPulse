"""Sustainability and transportation API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app import dependencies as deps

router = APIRouter(prefix="/sustainability", tags=["sustainability"])


@router.get("/summary")
async def sustainability_summary() -> dict:
    """Get the latest sustainability summary from the agent."""
    if deps.sustainability_agent:
        summary = await deps.sustainability_agent.get_summary()
        data = summary.model_dump()
        data["estimated_co2_kg_per_1000_fans"] = data.get("estimated_co2_kg", 0)
        return data
    return {
        "transit_split": {
            "metro": 0.35,
            "bus": 0.2,
            "rideshare": 0.25,
            "walk": 0.15,
            "shuttle": 0.05,
        },
        "estimated_co2_kg": 82.5,
        "estimated_co2_kg_per_1000_fans": 82.5,
        "sustainability_score": 63,
        "eco_tips": [
            "Promote Gate D rail shuttle while rideshare queues are saturated.",
            "Send refill-station reminders to sections with high bottled-water purchases.",
            "Dispatch waste volunteers to bins above 80% before the final whistle surge.",
        ],
        "waste_bin_fill_pct": {f"Bin_{i}": 0.3 for i in range(1, 9)},
        "water_refill_usage": 120,
    }


@router.get("/transit")
async def transit_recommendation(
    gate: str = Query(..., description="Departure gate, e.g. Gate_D"),
    destination: str = Query("downtown", description="Final destination"),
    language: str = Query("en", description="ISO language code for eco-nudge"),
) -> dict:
    """Get a CO₂-aware transit recommendation with GenAI eco-nudge."""
    if deps.sustainability_agent and not deps.demo_mode:
        return await deps.sustainability_agent.get_transit_recommendation(
            gate, destination, language
        )
    # Demo fallback with deterministic data
    return {
        "best_mode": "metro",
        "best_wait_min": 5,
        "co2_saved_kg": 0.65,
        "nudge": (
            "Take the Metro Blue Line from Gate D — 65% less CO₂ than rideshare "
            "and only a 5-minute wait."
            if language == "en"
            else "Toma el Metro Blue Line desde Gate D — 65% menos CO₂ que rideshare."
        ),
        "alternatives": [
            {"mode": "metro", "wait_min": 5, "co2_kg_per_5km": 0.2},
            {"mode": "shuttle", "wait_min": 8, "co2_kg_per_5km": 0.4},
            {"mode": "rideshare", "wait_min": 15, "co2_kg_per_5km": 0.9},
        ],
    }


@router.get("/waste-bins")
async def waste_bins() -> dict:
    """Get current waste bin fill levels across the venue."""
    if deps.sustainability_agent:
        summary = await deps.sustainability_agent.get_summary()
        return {
            "bins": summary.waste_bin_fill_pct,
            "water_refill_usage": summary.water_refill_usage,
        }
    return {
        "bins": {f"Bin_{i}": 0.3 + (i % 3) * 0.15 for i in range(1, 9)},
        "water_refill_usage": 120,
    }
