import pytest
from unittest.mock import patch, MagicMock

from app.tasks import _parse_json, _build_trend


def test_parse_json_plain():
    result = _parse_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_json_with_fences():
    raw = '```json\n{"key": "value"}\n```'
    result = _parse_json(raw)
    assert result == {"key": "value"}


def test_parse_json_with_bare_fences():
    raw = '```\n{"key": "value"}\n```'
    result = _parse_json(raw)
    assert result == {"key": "value"}


@patch("app.tasks.get_sync_db")
def test_build_trend_first_analysis(mock_db):
    """First analysis for a brand returns a single data point."""
    mock_collection = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.limit.return_value = []
    mock_collection.find.return_value = mock_cursor
    mock_db.return_value = MagicMock(reports=mock_collection)

    data = _build_trend("TestBrand", 0.75)
    assert len(data) == 1
    assert data[0]["sentiment"] == 0.75


@patch("app.tasks.get_sync_db")
def test_build_trend_with_history(mock_db):
    """Trend should include past analyses and the current one."""
    from datetime import datetime, timezone

    past_docs = [
        {"sentiment_score": 0.5, "completed_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
        {"sentiment_score": 0.6, "completed_at": datetime(2026, 2, 1, tzinfo=timezone.utc)},
    ]
    mock_collection = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.limit.return_value = iter(past_docs)
    mock_collection.find.return_value = mock_cursor
    mock_db.return_value = MagicMock(reports=mock_collection)

    data = _build_trend("TestBrand", 0.7)
    assert len(data) == 3
    assert data[0]["sentiment"] == 0.5
    assert data[1]["sentiment"] == 0.6
    assert data[2]["sentiment"] == 0.7


@patch("app.core.progress._get_redis")
def test_emit_and_get_state(mock_redis):
    """Test Redis-backed progress tracking."""
    store = {}
    mock_r = MagicMock()
    mock_r.get.side_effect = lambda k: store.get(k)
    mock_r.set.side_effect = lambda k, v, **kw: store.__setitem__(k, v)
    mock_redis.return_value = mock_r

    from app.core.progress import emit, get_state

    emit("r1", "job1", "running", 50)
    state = get_state("r1")
    assert state is not None
    assert state["jobs"]["job1"]["status"] == "running"
    assert state["jobs"]["job1"]["progress"] == 50


@patch("app.core.progress._get_redis")
def test_emit_multiple_jobs(mock_redis):
    store = {}
    mock_r = MagicMock()
    mock_r.get.side_effect = lambda k: store.get(k)
    mock_r.set.side_effect = lambda k, v, **kw: store.__setitem__(k, v)
    mock_redis.return_value = mock_r

    from app.core.progress import emit, get_state

    emit("r2", "job1", "running", 30)
    emit("r2", "job2", "complete", 100, {"result": "ok"})

    state = get_state("r2")
    assert len(state["jobs"]) == 2
    assert state["jobs"]["job2"]["data"] == {"result": "ok"}


@patch("app.core.progress._get_redis")
def test_get_state_missing(mock_redis):
    mock_r = MagicMock()
    mock_r.get.return_value = None
    mock_redis.return_value = mock_r

    from app.core.progress import get_state
    assert get_state("nonexistent-id") is None


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["message"] == "Perception AI backend is running"
