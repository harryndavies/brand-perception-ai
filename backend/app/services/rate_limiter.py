"""Reusable Redis-backed rate limiting."""

from fastapi import HTTPException, status

from app.core.progress import _get_redis


def check_rate_limit(key: str, window: int, max_count: int) -> None:
    """Increment a rate-limit counter and raise 429 if the limit is exceeded.

    Uses a Redis pipeline to make the incr + expire atomic, avoiding
    the race condition where a key is incremented but never expires.

    Args:
        key: Redis key for this rate-limit bucket (e.g. "ratelimit:create:<user_id>").
        window: TTL in seconds for the sliding window.
        max_count: Maximum allowed requests within the window.
    """
    r = _get_redis()
    pipe = r.pipeline(transaction=True)
    pipe.incr(key)
    pipe.expire(key, window)
    count, _ = pipe.execute()

    if count > max_count:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
