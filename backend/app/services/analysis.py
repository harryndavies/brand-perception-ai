"""Analysis service — SSE streaming and legacy helpers.

The actual AI analysis work now runs in Celery tasks (app.tasks).
This module provides the SSE streaming interface that reads progress from Redis.
"""

import asyncio
import json
import logging
import re
from typing import AsyncGenerator

from app.core import progress

logger = logging.getLogger(__name__)


def _parse_json(raw: str) -> dict:
    """Parse JSON from API response, stripping markdown fences if present."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text.strip())


def get_job_state(report_id: str) -> dict | None:
    """Read job progress from Redis."""
    return progress.get_state(report_id)


async def stream_progress(report_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE events for a running analysis, reading from Redis."""
    prev_state = ""
    stale_count = 0

    while True:
        state = progress.get_state(report_id)
        if not state:
            yield f"event: error\ndata: {{\"message\": \"Report not found\"}}\n\n"
            return

        current = json.dumps(state["jobs"])
        if current != prev_state:
            yield f"event: progress\ndata: {current}\n\n"
            prev_state = current
            stale_count = 0
        else:
            stale_count += 1

        if state["status"] == "complete":
            yield f"event: complete\ndata: {{\"report_id\": \"{report_id}\"}}\n\n"
            return

        if state["status"] == "failed":
            yield f"event: error\ndata: {{\"message\": \"Analysis failed\"}}\n\n"
            return

        if stale_count > 120:  # 60s timeout
            yield f"event: error\ndata: {{\"message\": \"Timeout\"}}\n\n"
            return

        await asyncio.sleep(0.5)
