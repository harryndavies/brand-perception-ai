"""Redis-backed job progress tracking.

Replaces the in-memory _jobs dict so progress is shared across
the API server and Celery worker processes.
"""

import json

import redis

from app.core.config import settings
from app.core.enums import ReportStatus

_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _key(report_id: str) -> str:
    return f"progress:{report_id}"


def init(report_id: str, job_ids: list[str]):
    """Seed initial progress so SSE clients see 'pending' immediately."""
    r = _get_redis()
    state = {
        "status": ReportStatus.PROCESSING,
        "jobs": {
            jid: {"id": jid, "status": ReportStatus.PENDING, "progress": 0, "data": None}
            for jid in job_ids
        },
    }
    r.set(_key(report_id), json.dumps(state), ex=600)


def _channel(report_id: str) -> str:
    return f"progress:channel:{report_id}"


def emit(report_id: str, job_id: str, status: str, progress: float, data: dict | None = None):
    """Update a single job's progress in Redis and notify subscribers."""
    r = _get_redis()
    key = _key(report_id)

    state = get_state(report_id) or {"jobs": {}, "status": ReportStatus.PROCESSING}
    state["jobs"][job_id] = {
        "id": job_id,
        "status": status,
        "progress": progress,
        "data": data,
    }

    r.set(key, json.dumps(state), ex=600)
    r.publish(_channel(report_id), "update")


def set_status(report_id: str, status: str):
    """Set the overall report status (processing/complete/failed)."""
    r = _get_redis()
    key = _key(report_id)

    state = get_state(report_id) or {"jobs": {}, "status": ReportStatus.PROCESSING}
    state["status"] = status
    r.set(key, json.dumps(state), ex=600)
    r.publish(_channel(report_id), "update")


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
