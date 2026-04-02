"""Tests for SSE streaming endpoint and progress broadcasting."""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.services.analysis import stream_progress


def _make_redis_store(initial_state: dict | None = None):
    """Create a dict-backed mock Redis."""
    store = {}
    if initial_state:
        for k, v in initial_state.items():
            store[k] = json.dumps(v) if isinstance(v, dict) else v

    mock_r = MagicMock()
    mock_r.get.side_effect = lambda k: store.get(k)
    mock_r.set.side_effect = lambda k, v, **kw: store.__setitem__(k, v)
    mock_r.publish.return_value = 0
    return mock_r, store


@pytest.mark.asyncio
@patch("app.services.analysis.progress")
async def test_stream_progress_sends_initial_state(mock_progress):
    """SSE stream should emit the initial job state."""
    state = {
        "status": "processing",
        "jobs": {"analysis": {"id": "analysis", "status": "pending", "progress": 0, "data": None}},
    }

    call_count = 0

    def get_state_sequence(report_id):
        nonlocal call_count
        call_count += 1
        if call_count <= 1:
            return state
        # Return complete on second call to end the stream
        return {**state, "status": "complete"}

    mock_progress.get_state.side_effect = get_state_sequence

    events = []
    with patch("app.services.analysis.sync_redis") as mock_redis_mod:
        mock_r = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.get_message.return_value = None
        mock_r.pubsub.return_value = mock_pubsub
        mock_redis_mod.from_url.return_value = mock_r

        async for event in stream_progress("test-report"):
            events.append(event)

    assert len(events) >= 2
    assert "event: progress" in events[0]
    assert "event: complete" in events[-1]


@pytest.mark.asyncio
@patch("app.services.analysis.progress")
async def test_stream_progress_missing_report(mock_progress):
    """SSE stream should send error when report not found in Redis."""
    mock_progress.get_state.return_value = None

    events = []
    with patch("app.services.analysis.sync_redis") as mock_redis_mod:
        mock_r = MagicMock()
        mock_r.pubsub.return_value = MagicMock()
        mock_redis_mod.from_url.return_value = mock_r

        async for event in stream_progress("missing-report"):
            events.append(event)

    assert len(events) == 1
    assert "event: error" in events[0]
    assert "Report not found" in events[0]


@pytest.mark.asyncio
@patch("app.services.analysis.progress")
async def test_stream_progress_handles_failure(mock_progress):
    """SSE stream should emit error when analysis fails."""
    mock_progress.get_state.return_value = {
        "status": "failed",
        "jobs": {"analysis": {"id": "analysis", "status": "running", "progress": 50, "data": None}},
    }

    events = []
    with patch("app.services.analysis.sync_redis") as mock_redis_mod:
        mock_r = MagicMock()
        mock_r.pubsub.return_value = MagicMock()
        mock_redis_mod.from_url.return_value = mock_r

        async for event in stream_progress("failed-report"):
            events.append(event)

    assert any("Analysis failed" in e for e in events)


@pytest.mark.asyncio
@patch("app.services.analysis.progress")
async def test_stream_progress_deduplicates(mock_progress):
    """SSE stream should not send duplicate progress events."""
    state = {
        "status": "processing",
        "jobs": {"analysis": {"id": "analysis", "status": "running", "progress": 50, "data": None}},
    }

    call_count = 0

    def get_state_advancing(report_id):
        nonlocal call_count
        call_count += 1
        if call_count <= 3:
            return state  # same state 3 times
        return {**state, "status": "complete"}

    mock_progress.get_state.side_effect = get_state_advancing

    events = []
    with patch("app.services.analysis.sync_redis") as mock_redis_mod:
        mock_r = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.get_message.return_value = {"type": "message", "data": "update"}
        mock_r.pubsub.return_value = mock_pubsub
        mock_redis_mod.from_url.return_value = mock_r

        async for event in stream_progress("dedup-report"):
            events.append(event)

    progress_events = [e for e in events if "event: progress" in e]
    # Should only emit once for the same state, not 3 times
    assert len(progress_events) == 1
