"""Tests for the Celery analysis task and its error paths."""

import json
import pytest
from unittest.mock import patch, MagicMock


# ── Helpers ──────────────────────────────────────────────────────────────────

MOCK_API_RESPONSE = {
    "scores": {
        "brand_recognition": 8,
        "sentiment": 7,
        "innovation": 6,
        "value_perception": 7,
        "market_positioning": 8,
    },
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
@patch("app.tasks.call_model")
@patch("app.tasks.get_sync_db")
def test_run_analysis_success(mock_db, mock_call_model, mock_redis):
    """Full happy-path: API returns valid JSON, DB is updated, progress is set."""
    mock_r, store = _make_redis_store()
    mock_redis.return_value = mock_r

    mock_call_model.return_value = MOCK_API_RESPONSE

    mock_collection = MagicMock()
    mock_collection.find_one.return_value = {"model": "claude-sonnet", "models": ["claude-sonnet"]}
    mock_db.return_value = MagicMock(reports=mock_collection)

    from app.tasks import run_analysis
    run_analysis("report-123", "TestBrand", ["Rival"], "user-1", ["claude-sonnet"])

    # Verify DB was updated with complete status
    mock_collection.update_one.assert_called_once()
    call_args = mock_collection.update_one.call_args
    assert call_args[0][0] == {"_id": "report-123"}
    update = call_args[0][1]["$set"]
    assert update["status"] == "complete"
    assert update["sentiment_score"] == 0.6  # avg of 0.7, 0.6, 0.5
    assert len(update["pillars"]) == 1
    assert len(update["model_perceptions"]) == 1
    assert len(update["competitor_positions"]) == 2

    # Verify progress was set to complete
    state = json.loads(store.get("progress:report-123", "{}"))
    assert state["status"] == "complete"


@patch("app.core.progress._get_redis")
@patch("app.tasks.call_model")
@patch("app.tasks.get_sync_db")
def test_run_analysis_builds_model_perceptions(mock_db, mock_call_model, mock_redis):
    """Model perceptions should include the model label."""
    mock_r, store = _make_redis_store()
    mock_redis.return_value = mock_r

    mock_call_model.return_value = MOCK_API_RESPONSE
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = {"models": ["claude-sonnet"]}
    mock_db.return_value = MagicMock(reports=mock_collection)

    from app.tasks import run_analysis
    run_analysis("report-456", "TestBrand", [], "user-1", ["claude-sonnet"])

    update = mock_collection.update_one.call_args[0][1]["$set"]
    assert len(update["model_perceptions"]) == 1
    assert update["model_perceptions"][0]["model"] == "Claude Sonnet"


@patch("app.core.progress._get_redis")
@patch("app.tasks.call_model")
@patch("app.tasks.get_sync_db")
def test_run_analysis_api_failure_marks_failed(mock_db, mock_call_model, mock_redis):
    """When the API raises, report status should be set to failed."""
    mock_r, store = _make_redis_store()
    mock_redis.return_value = mock_r

    mock_call_model.side_effect = Exception("API timeout")

    mock_collection = MagicMock()
    mock_db.return_value = MagicMock(reports=mock_collection)

    from app.tasks import run_analysis

    with pytest.raises(Exception):
        run_analysis("report-err", "TestBrand", [], "user-1", ["claude-sonnet"])

    # DB should be marked as failed
    mock_collection.update_one.assert_called_once()
    update = mock_collection.update_one.call_args[0][1]["$set"]
    assert update == {"status": "failed"}

    # Redis progress should be failed
    state = json.loads(store.get("progress:report-err", "{}"))
    assert state["status"] == "failed"


@patch("app.core.progress._get_redis")
@patch("app.tasks.call_model")
@patch("app.tasks.get_sync_db")
def test_run_analysis_invalid_json_marks_failed(mock_db, mock_call_model, mock_redis):
    """When the provider returns bad data, report should be marked failed."""
    mock_r, store = _make_redis_store()
    mock_redis.return_value = mock_r

    # call_model raises because providers._parse_json fails
    mock_call_model.side_effect = json.JSONDecodeError("bad", "", 0)

    mock_collection = MagicMock()
    mock_db.return_value = MagicMock(reports=mock_collection)

    from app.tasks import run_analysis

    with pytest.raises(Exception):
        run_analysis("report-bad", "TestBrand", [], "user-1", ["claude-sonnet"])

    update = mock_collection.update_one.call_args[0][1]["$set"]
    assert update == {"status": "failed"}


@patch("app.core.progress._get_redis")
@patch("app.tasks.call_model")
@patch("app.tasks.get_sync_db")
def test_run_analysis_emits_running_then_complete(mock_db, mock_call_model, mock_redis):
    """Progress should transition from running to complete."""
    mock_r, store = _make_redis_store()
    mock_redis.return_value = mock_r

    emitted_states = []
    original_set = mock_r.set.side_effect

    def capture_set(k, v, **kw):
        original_set(k, v, **kw)
        if k.startswith("progress:"):
            state = json.loads(v)
            for job_id, job in state.get("jobs", {}).items():
                emitted_states.append(job["status"])

    mock_r.set.side_effect = capture_set

    mock_call_model.return_value = MOCK_API_RESPONSE
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = {"models": ["claude-sonnet"]}
    mock_db.return_value = MagicMock(reports=mock_collection)

    from app.tasks import run_analysis
    run_analysis("report-prog", "TestBrand", [], "user-1", ["claude-sonnet"])

    assert "running" in emitted_states
    assert "complete" in emitted_states
    assert emitted_states.index("running") < emitted_states.index("complete")
