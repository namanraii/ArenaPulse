import pytest

from app.utils.security import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_in_memory():
    # Capacity 2, refill 1.0 (so window is 2 seconds)
    limiter = RateLimiter(key_prefix="test", capacity=2, refill_rate=1.0)

    # First request should pass
    assert limiter._is_allowed_in_memory("user1") is True
    # Second request should pass
    assert limiter._is_allowed_in_memory("user1") is True
    # Third request should fail (limit reached)
    assert limiter._is_allowed_in_memory("user1") is False

    # Different user should pass
    assert limiter._is_allowed_in_memory("user2") is True
