"""LLM router with caching, model selection, and cost tracking."""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from app.config import settings
from app.utils.security import get_redis

logger = structlog.get_logger()

DEFAULT_FLASH_TIMEOUT = 15.0
DEFAULT_PRO_TIMEOUT = 30.0


class LLMRouter:
    """Routes LLM calls to Gemini Flash (fast/cheap) or Pro (complex), with Redis caching."""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=60.0)
        self._flash_url = settings.gemini_flash_url
        self._pro_url = settings.gemini_pro_url
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "flash_calls": 0,
            "pro_calls": 0,
            "estimated_tokens_saved": 0,
        }

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()

    def _build_payload(self, prompt: str, system: str, temperature: float) -> dict[str, Any]:
        """Build the JSON payload for the Gemini API.

        Args:
            prompt: The user prompt.
            system: Optional system instructions.
            temperature: Generation temperature.

        Returns:
            dict[str, Any]: The payload dictionary.
        """
        parts: list[dict[str, Any]] = []
        if system:
            parts.append({"text": f"System: {system}\n\n{prompt}"})
        else:
            parts.append({"text": prompt})
        return {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048,
            },
        }

    async def _call_gemini(self, url: str, payload: dict[str, Any], timeout: float) -> str:
        """Make an HTTP POST request to the Gemini API.

        Args:
            url: The API endpoint URL.
            payload: The JSON request payload.
            timeout: Request timeout in seconds.

        Returns:
            str: The generated text response.
        """
        if not settings.gemini_api_key:
            return self._local_response(payload)
        headers = {"x-goog-api-key": settings.gemini_api_key}
        try:
            resp = await self.client.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return text.strip()
            return ""
        except httpx.HTTPStatusError as exc:
            logger.error("gemini_http_error", status=exc.response.status_code, body=exc.response.text)
            return "[Error: LLM service unavailable]"
        except Exception as exc:
            logger.error("gemini_exception", error=str(exc))
            return "[Error: Unexpected LLM failure]"

    async def call_flash(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        """Call the Gemini Flash model (fast and cost-effective).

        Args:
            prompt: The user prompt.
            system: Optional system instructions.
            temperature: Generation temperature (default 0.3).

        Returns:
            str: The generated text response.
        """
        self.metrics["flash_calls"] += 1
        payload = self._build_payload(prompt, system, temperature)
        return await self._call_gemini(self._flash_url, payload, DEFAULT_FLASH_TIMEOUT)

    async def call_pro(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.2,
    ) -> str:
        """Call the Gemini Pro model (for complex reasoning).

        Args:
            prompt: The user prompt.
            system: Optional system instructions.
            temperature: Generation temperature (default 0.2).

        Returns:
            str: The generated text response.
        """
        self.metrics["pro_calls"] += 1
        payload = self._build_payload(prompt, system, temperature)
        return await self._call_gemini(self._pro_url, payload, DEFAULT_PRO_TIMEOUT)

    async def call_cached(
        self,
        cache_key: str,
        prompt: str,
        system: str = "",
        model: str = "flash",
        ttl_seconds: int = 300,
    ) -> str:
        """Check Redis cache before calling LLM."""
        redis_conn = None
        try:
            redis_conn = await get_redis()
            cached = await redis_conn.get(cache_key)
            if cached:
                logger.info("llm_cache_hit", key=cache_key)
                self.metrics["cache_hits"] += 1
                self.metrics["estimated_tokens_saved"] += 500
                return cached
        except Exception as exc:
            logger.warning("llm_cache_unavailable", key=cache_key, error=str(exc))

        self.metrics["cache_misses"] += 1
        logger.info("llm_cache_miss", key=cache_key, model=model)
        if model == "pro":
            result = await self.call_pro(prompt, system)
        else:
            result = await self.call_flash(prompt, system)

        if redis_conn and result and not result.startswith("[Error"):
            try:
                await redis_conn.setex(cache_key, ttl_seconds, result)
            except Exception as exc:
                logger.warning("llm_cache_write_failed", key=cache_key, error=str(exc))
        return result

    def _local_response(self, payload: dict[str, Any]) -> str:
        """Small deterministic fallback for tests and offline demos."""
        text = json.dumps(payload).lower()
        if "crowd alert" in text or "control-room" in text:
            return "Crowding is trending toward critical levels; open the overflow route and deploy stewards before the next surge."
        if "sustainability" in text or "co2" in text:
            return "Use rail or shuttle where possible.\nRefill bottles at water stations.\nRecycle in the marked bins before exiting."
        if "spanish" in text or "espanol" in text:
            return "Sigue la ruta indicada por ArenaPulse; evita las zonas congestionadas y pide ayuda a un voluntario si la necesitas."
        if "french" in text:
            return "Suivez l'itineraire ArenaPulse, evitez les zones denses et demandez de l'aide a un steward si necessaire."
        return "Follow the ArenaPulse route, avoid congested areas, and ask the nearest steward if you need assistance."

    def get_efficiency_summary(self) -> dict:
        """Get a summary of LLM usage metrics, cost, and cache efficiency.

        Returns:
            dict: Summary metrics.
        """
        hits = self.metrics["cache_hits"]
        misses = self.metrics["cache_misses"]
        total = hits + misses
        hit_rate = round((hits / total) * 100, 1) if total else 0.0
        flash_cost = self.metrics["flash_calls"] * 0.0001
        pro_cost = self.metrics["pro_calls"] * 0.001
        return {
            **self.metrics,
            "cache_hit_rate_pct": hit_rate,
            "estimated_cost_usd": round(flash_cost + pro_cost, 4),
            "routing_strategy": "Flash for fan chat/navigation; Pro for ops reasoning",
        }
