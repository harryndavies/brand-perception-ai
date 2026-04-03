"""Analysis service -- SSE streaming and legacy helpers.

The actual AI analysis work now runs in Celery tasks (app.tasks).
This module provides the SSE streaming interface that reads progress from Redis.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator

import redis as sync_redis

from app.core import progress
from app.core.config import settings
from app.core.enums import ReportStatus

logger = logging.getLogger(__name__)


def get_job_state(report_id: str) -> dict | None:
    """Read job progress from Redis."""
    return progress.get_state(report_id)


async def stream_progress(report_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE events for a running analysis using Redis pub/sub."""
    r = sync_redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    pubsub.subscribe(f"progress:channel:{report_id}")

    prev_state = ""
    deadline = asyncio.get_event_loop().time() + 120  # 2 min timeout

    try:
        while asyncio.get_event_loop().time() < deadline:
            state = progress.get_state(report_id)
            if not state:
                yield f"event: error\ndata: {{\"message\": \"Report not found\"}}\n\n"
                return

            current = json.dumps(state["jobs"])
            if current != prev_state:
                yield f"event: progress\ndata: {current}\n\n"
                prev_state = current

            if state["status"] == ReportStatus.COMPLETE:
                yield f"event: complete\ndata: {{\"report_id\": \"{report_id}\"}}\n\n"
                return

            if state["status"] == ReportStatus.FAILED:
                yield f"event: error\ndata: {{\"message\": \"Analysis failed\"}}\n\n"
                return

            # Wait for pub/sub notification instead of blind polling
            await asyncio.to_thread(pubsub.get_message, ignore_subscribe_messages=True, timeout=2.0)
    finally:
        pubsub.unsubscribe()
        pubsub.close()
        r.close()
