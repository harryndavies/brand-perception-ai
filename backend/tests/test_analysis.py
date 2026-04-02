import pytest
from unittest.mock import patch, MagicMock

from app.tasks import _parse_json, _generate_trend


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


def test_generate_trend_length():
    data = _generate_trend(0.5)
    assert len(data) == 6
    for point in data:
        assert "date" in point
        assert "sentiment" in point
        assert "volume" in point
        assert -1 <= point["sentiment"] <= 1


def test_generate_trend_bounds():
    """Sentiment should stay within -1 to 1."""
    for _ in range(20):
        data = _generate_trend(0.95)
        for point in data:
            assert -1 <= point["sentiment"] <= 1


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
    assert response.json()["message"] == "Brand Intelligence backend is running"
