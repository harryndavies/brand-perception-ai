"""Tests for the Celery analysis task and its error paths."""

import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


# ── Helpers ──────────────────────────────────────────────────────────────────

MOCK_API_RESPONSE = {
    "brand_perception": {
        "summary": "Test brand is well-perceived.",
        "sentiment": 0.7,
        "key_themes": ["quality", "innovation"],
    },
    "news_sentiment": {
        "summary": "Positive media coverage.",
        "sentiment": 0.6,
        "key_themes": ["growth", "expansion"],
    },
    "competitor_analysis": {
        "summary": "Strong competitive position.",
        "sentiment": 0.5,
        "key_themes": ["market leader"],
        "competitor_positions": [
            {"brand": "TestBrand", "premium_score": 0.8, "lifestyle_score": 0.6},
            {"brand": "Rival", "premium_score": 0.5, "lifestyle_score": 0.4},
        ],
    },
    "pillars": [
        {
            "name": "Quality",
            "description": "Known for quality.",
            "confidence": 0.9,
            "sources": ["Claude"],
        },
    ],
}


def _mock_message(content: str):
    """Create a mock Anthropic message response."""
    msg = MagicMock()
    block = MagicMock()
    block.text = content
    msg.content = [block]
    return msg


def _make_redis_store():
    """Create a dict-backed mock Redis for progress tracking."""
    store = {}
    mock_r = MagicMock()
    mock_r.get.side_effect = lambda k: store.get(k)
    mock_r.set.side_effect = lambda k, v, **kw: store.__setitem__(k, v)
    mock_r.publish.return_value = 0
    return mock_r, store


# ── Task tests ───────────────────────────────────────────────────────────────

@patch("app.core.progress._get_redis")
@patch("app.tasks._anthropic_client")
@patch("app.tasks.get_sync_db")
def test_run_analysis_success(mock_db, mock_client, mock_redis):
    """Full happy-path: API returns valid JSON, DB is updated, progress is set."""
    mock_r, store = _make_redis_store()
    mock_redis.return_value = mock_r

    mock_client.messages.create.return_value = _mock_message(json.dumps(MOCK_API_RESPONSE))

    mock_collection = MagicMock()
    mock_db.return_value = MagicMock(reports=mock_collection)

    from app.tasks import run_analysis
    run_analysis("report-123", "TestBrand", ["Rival"])

    # Verify DB was updated with complete status
    mock_collection.update_one.assert_called_once()
    call_args = mock_collection.update_one.call_args
    assert call_args[0][0] == {"_id": "report-123"}
    update = call_args[0][1]["$set"]
    assert update["status"] == "complete"
    assert update["sentiment_score"] == 0.6  # avg of 0.7, 0.6, 0.5
    assert len(update["pillars"]) == 1
    assert len(update["model_perceptions"]) == 3
    assert len(update["competitor_positions"]) == 2
    assert update["trend_data"] is not None

    # Verify progress was set to complete
    state = json.loads(store.get("progress:report-123", "{}"))
    assert state["status"] == "complete"


@patch("app.core.progress._get_redis")
@patch("app.tasks._anthropic_client")
@patch("app.tasks.get_sync_db")
def test_run_analysis_builds_model_perceptions(mock_db, mock_client, mock_redis):
    """Model perceptions should map to the three analysis sections."""
    mock_r, store = _make_redis_store()
    mock_redis.return_value = mock_r

    mock_client.messages.create.return_value = _mock_message(json.dumps(MOCK_API_RESPONSE))
    mock_db.return_value = MagicMock(reports=MagicMock())

    from app.tasks import run_analysis
    run_analysis("report-456", "TestBrand", [])

    update = mock_db.return_value.reports.update_one.call_args[0][1]["$set"]
    labels = [p["model"] for p in update["model_perceptions"]]
    assert labels == ["Brand Perception", "News Sentiment", "Competitor Analysis"]

    assert update["model_perceptions"][0]["sentiment"] == 0.7
    assert update["model_perceptions"][1]["key_themes"] == ["growth", "expansion"]


@patch("app.core.progress._get_redis")
@patch("app.tasks._anthropic_client")
@patch("app.tasks.get_sync_db")
def test_run_analysis_api_failure_marks_failed(mock_db, mock_client, mock_redis):
    """When the Claude API raises, report status should be set to failed."""
    mock_r, store = _make_redis_store()
    mock_redis.return_value = mock_r

    mock_client.messages.create.side_effect = Exception("API timeout")

    mock_collection = MagicMock()
    mock_db.return_value = MagicMock(reports=mock_collection)

    from app.tasks import run_analysis

    with pytest.raises(Exception):
        run_analysis("report-err", "TestBrand", [])

    # DB should be marked as failed
    mock_collection.update_one.assert_called_once()
    update = mock_collection.update_one.call_args[0][1]["$set"]
    assert update == {"status": "failed"}

    # Redis progress should be failed
    state = json.loads(store.get("progress:report-err", "{}"))
    assert state["status"] == "failed"


@patch("app.core.progress._get_redis")
@patch("app.tasks._anthropic_client")
@patch("app.tasks.get_sync_db")
def test_run_analysis_invalid_json_marks_failed(mock_db, mock_client, mock_redis):
    """When Claude returns unparseable JSON, report should be marked failed."""
    mock_r, store = _make_redis_store()
    mock_redis.return_value = mock_r

    mock_client.messages.create.return_value = _mock_message("not valid json at all")

    mock_collection = MagicMock()
    mock_db.return_value = MagicMock(reports=mock_collection)

    from app.tasks import run_analysis

    with pytest.raises(Exception):
        run_analysis("report-bad", "TestBrand", [])

    update = mock_collection.update_one.call_args[0][1]["$set"]
    assert update == {"status": "failed"}


@patch("app.core.progress._get_redis")
@patch("app.tasks._anthropic_client")
@patch("app.tasks.get_sync_db")
def test_run_analysis_emits_running_then_complete(mock_db, mock_client, mock_redis):
    """Progress should transition from running to complete."""
    mock_r, store = _make_redis_store()
    mock_redis.return_value = mock_r

    emitted_states = []
    original_set = mock_r.set.side_effect

    def capture_set(k, v, **kw):
        original_set(k, v, **kw)
        if k.startswith("progress:"):
            state = json.loads(v)
            if "analysis" in state.get("jobs", {}):
                emitted_states.append(state["jobs"]["analysis"]["status"])

    mock_r.set.side_effect = capture_set

    mock_client.messages.create.return_value = _mock_message(json.dumps(MOCK_API_RESPONSE))
    mock_db.return_value = MagicMock(reports=MagicMock())

    from app.tasks import run_analysis
    run_analysis("report-prog", "TestBrand", [])

    assert "running" in emitted_states
    assert "complete" in emitted_states
    assert emitted_states.index("running") < emitted_states.index("complete")
