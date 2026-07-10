"""Tests for LLM router efficiency metrics."""

from app.utils.llm_router import LLMRouter


def test_efficiency_summary_defaults() -> None:
    router = LLMRouter()
    summary = router.get_efficiency_summary()
    assert summary["cache_hit_rate_pct"] == 0.0
    assert "routing_strategy" in summary


def test_cache_hit_increments_metrics() -> None:
    router = LLMRouter()
    router.metrics["cache_hits"] = 3
    router.metrics["cache_misses"] = 1
    summary = router.get_efficiency_summary()
    assert summary["cache_hit_rate_pct"] == 75.0
