"""Security utilities: input sanitization and rate limiting."""

from __future__ import annotations

import re
import time
import redis.asyncio as redis

from app.config import settings

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get or initialize the global Redis connection pool.

    Returns:
        redis.Redis: The Redis client instance.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def close_redis() -> None:
    """Close the global Redis connection pool if it exists."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


def sanitize_input(text: str, max_length: int = 2000) -> str:
    """Sanitize user input before it reaches LLM prompts.

    - Strips control characters
    - Limits length
    - Removes common prompt-injection markers
    """
    if not isinstance(text, str):
        return ""
    text = text[:max_length]
    # Strip control characters except common whitespace
    text = "".join(ch for ch in text if ord(ch) >= 32 or ch in "\t\n\r")
    # Remove known injection patterns
    text = re.sub(
        r"(?i)(ignore previous instructions|system prompt|you are now|DAN mode)", "", text
    )
    text = re.sub(r"[<>]", "", text)  # Basic XSS prevention
    return text.strip()


class RateLimiter:
    """Simple token-bucket rate limiter backed by Redis."""

    def __init__(self, key_prefix: str = "rl", capacity: int = 20, refill_rate: float = 1.0):
        self.key_prefix = key_prefix
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._memory_events: dict[str, list[float]] = {}

    async def is_allowed(self, identifier: str) -> bool:
        """Check if an action is allowed for the given identifier under the rate limit.

        Args:
            identifier: The unique identifier (e.g., IP address or user ID).

        Returns:
            bool: True if allowed, False if rate limited.
        """
        try:
            redis_conn = await get_redis()
            key = f"{self.key_prefix}:{identifier}"
            now = await redis_conn.time()
            # Redis TIME returns [seconds, microseconds]
            current_time = now[0] + now[1] / 1_000_000

            # Try a simple sliding window approach using sorted sets
            window_start = current_time - (self.capacity / self.refill_rate)
            await redis_conn.zremrangebyscore(key, 0, window_start)
            current = await redis_conn.zcard(key)
            if current >= self.capacity:
                return False
            await redis_conn.zadd(key, {str(current_time): current_time})
            await redis_conn.expire(key, int(self.capacity / self.refill_rate) + 1)
            return True
        except Exception:
            return self._is_allowed_in_memory(identifier)

    def _is_allowed_in_memory(self, identifier: str) -> bool:
        """Fallback in-memory rate limiting when Redis is unavailable.

        Args:
            identifier: The unique identifier.

        Returns:
            bool: True if allowed, False if rate limited.
        """
        current_time = time.time()
        window_seconds = self.capacity / self.refill_rate
        events = [
            event_time
            for event_time in self._memory_events.get(identifier, [])
            if event_time >= current_time - window_seconds
        ]
        if len(events) >= self.capacity:
            self._memory_events[identifier] = events
            return False
        events.append(current_time)
        self._memory_events[identifier] = events
        return True


# Global limiters
public_limiter = RateLimiter(key_prefix="rl:public", capacity=30, refill_rate=1.0)
chat_limiter = RateLimiter(key_prefix="rl:chat", capacity=15, refill_rate=0.5)
