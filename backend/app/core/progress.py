"""Redis-backed job progress tracking.

Replaces the in-memory _jobs dict so progress is shared across
the API server and Celery worker processes.
"""

import json
import os

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def _key(report_id: str) -> str:
    return f"progress:{report_id}"


def emit(report_id: str, job_id: str, status: str, progress: float, data: dict | None = None):
    """Update a single job's progress in Redis."""
    r = _get_redis()
    key = _key(report_id)

    state = get_state(report_id) or {"jobs": {}, "status": "processing"}
    state["jobs"][job_id] = {
        "id": job_id,
        "status": status,
        "progress": progress,
        "data": data,
    }

    r.set(key, json.dumps(state), ex=600)  # expire after 10 min


def set_status(report_id: str, status: str):
    """Set the overall report status (processing/complete/failed)."""
    r = _get_redis()
    key = _key(report_id)

    state = get_state(report_id) or {"jobs": {}, "status": "processing"}
    state["status"] = status
    r.set(key, json.dumps(state), ex=600)


def get_state(report_id: str) -> dict | None:
    """Read the full progress state for a report."""
    r = _get_redis()
    raw = r.get(_key(report_id))
    if raw is None:
        return None
    return json.loads(raw)


def publish_event(report_id: str, event_type: str, data: dict):
    """Publish an event to the report's Redis pub/sub channel."""
    r = _get_redis()
    r.publish(f"events:{report_id}", json.dumps({"type": event_type, **data}))
