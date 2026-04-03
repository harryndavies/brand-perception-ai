"""Celery tasks for brand analysis.

These run in the Celery worker process, separate from the FastAPI server.
Progress is tracked via Redis so the API can stream updates to clients.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone

import anthropic

from app.core.database import get_sync_db
from app.core.logging import setup_logging, correlation_id
from app.core import progress
from app.worker import celery_app

setup_logging()
logger = logging.getLogger(__name__)

def _get_client(user_id: str) -> anthropic.Anthropic:
    """Return an Anthropic client using the user's encrypted API key."""
    from app.core.encryption import decrypt

    db = get_sync_db()
    doc = db.users.find_one({"_id": user_id}, {"encrypted_api_key": 1})
    if not doc or not doc.get("encrypted_api_key"):
        raise RuntimeError("No API key found for user")
    return anthropic.Anthropic(api_key=decrypt(doc["encrypted_api_key"]))


# ── Prompt ──────────────────────────────────────────────────────────────────

ANALYSIS_PROMPT = """Analyse the brand "{brand}" with competitors [{competitors}].

Score every dimension using the rubrics below. Apply the criteria strictly and consistently.

SCORING RUBRICS:

Brand Recognition (1-10):
  1-3: Unknown or frequently confused with others
  4-6: Known within its category but not top-of-mind
  7-10: Category leader, immediately recognised

Sentiment (1-10):
  1-3: Predominantly negative associations, controversies, or warnings
  4-6: Mixed or neutral perception
  7-10: Strongly positive, recommended, or aspirational

Innovation (1-10):
  1-3: Seen as stagnant or derivative
  4-6: Keeps pace with the market but doesn't lead
  7-10: Widely cited as an innovator or disruptor

Value Perception (1-10):
  1-3: Seen as overpriced or poor value
  4-6: Fairly priced for what it offers
  7-10: Seen as excellent value or worth a premium

Market Positioning (1-10):
  1-3: Weak position, easily substituted
  4-6: Established but faces strong competition
  7-10: Dominant or clearly differentiated position

Return a single JSON object with exactly this structure. Do not include any text outside the JSON.

{{
  "scores": {{
    "brand_recognition": <int 1-10>,
    "sentiment": <int 1-10>,
    "innovation": <int 1-10>,
    "value_perception": <int 1-10>,
    "market_positioning": <int 1-10>
  }},
  "brand_perception": {{
    "summary": "2-3 sentence analysis of how this brand is perceived",
    "sentiment": <float between -1.0 and 1.0>,
    "key_themes": ["theme1", "theme2", "theme3"]
  }},
  "news_sentiment": {{
    "summary": "2-3 sentence analysis focused on news sentiment and public perception",
    "sentiment": <float between -1.0 and 1.0>,
    "key_themes": ["theme1", "theme2", "theme3"]
  }},
  "competitor_analysis": {{
    "summary": "2-3 sentence analysis of competitive dynamics",
    "sentiment": <float between -1.0 and 1.0>,
    "key_themes": ["theme1", "theme2", "theme3"],
    "competitor_positions": [
      {{
        "brand": "Brand Name",
        "premium_score": <float 0-1, where 1 is ultra-premium>,
        "lifestyle_score": <float 0-1, where 0 is purely functional and 1 is purely lifestyle>
      }}
    ]
  }},
  "pillars": [
    {{
      "name": "Pillar Name",
      "description": "1-2 sentence description of this brand pillar",
      "confidence": <float between 0.0 and 1.0>,
      "sources": ["Claude"]
    }}
  ]
}}

Include 4-6 brand pillars covering perception, media narrative, and competitive positioning.
Include positioning for "{brand}" and each competitor in competitor_positions.
Be specific and insightful, not generic. Ground your analysis in real brand perception."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text.strip())


def _build_trend(brand: str, current_sentiment: float, current_model: str = "sonnet") -> list[dict]:
    """Build trend data from past completed analyses of this brand."""
    db = get_sync_db()
    past = list(
        db.reports.find(
            {"brand": {"$regex": f"^{re.escape(brand)}$", "$options": "i"}, "status": "complete"},
            {"sentiment_score": 1, "completed_at": 1, "model": 1},
        )
        .sort("completed_at", 1)
        .limit(50)
    )

    data = []
    for doc in past:
        if doc.get("sentiment_score") is not None and doc.get("completed_at"):
            data.append({
                "date": doc["completed_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sentiment": doc["sentiment_score"],
                "model": doc.get("model", "sonnet"),
            })

    data.append({
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sentiment": current_sentiment,
        "model": current_model,
    })

    return data


# ── Main Celery task ─────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.run_analysis", bind=True, max_retries=2)
def run_analysis(self, report_id: str, brand: str, competitors: list[str], user_id: str | None = None, model_id: str = "claude-sonnet-4-20250514"):
    """Run a single Claude call to analyse a brand.

    Runs as a Celery task in a worker process. Progress is published to
    Redis so the API server can stream SSE updates to the client.
    """
    cid = report_id[:8]
    correlation_id.set(cid)

    task_start = time.perf_counter()
    logger.info(
        "Starting analysis for %s",
        brand,
        extra={"report_id": report_id, "brand": brand, "task_name": "run_analysis"},
    )
    progress.emit(report_id, "analysis", "running", 0)

    try:
        competitor_str = ", ".join(competitors) if competitors else "general market"
        prompt = ANALYSIS_PROMPT.format(brand=brand, competitors=competitor_str)

        client = _get_client(user_id)
        message = client.messages.create(
            model=model_id,
            max_tokens=2048,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json(message.content[0].text)

        # Build model_perceptions from the three sections
        sections = [
            ("Brand Perception", result["brand_perception"]),
            ("News Sentiment", result["news_sentiment"]),
            ("Competitor Analysis", result["competitor_analysis"]),
        ]
        model_perceptions = [
            {
                "model": label,
                "summary": section["summary"],
                "sentiment": section["sentiment"],
                "key_themes": section["key_themes"],
            }
            for label, section in sections
        ]

        scores = result.get("scores", {})
        pillars = result.get("pillars", [])
        competitor_positions = result.get("competitor_analysis", {}).get("competitor_positions", [])

        sentiments = [s["sentiment"] for _, s in sections]
        avg_sentiment = round(sum(sentiments) / len(sentiments), 2)

        db = get_sync_db()

        # Read the model key stored on the report
        report_doc = db.reports.find_one({"_id": report_id}, {"model": 1})
        model_key = report_doc.get("model", "sonnet") if report_doc else "sonnet"
        trend_data = _build_trend(brand, avg_sentiment, model_key)

        progress.emit(report_id, "analysis", "complete", 100)
        db.reports.update_one(
            {"_id": report_id},
            {"$set": {
                "status": "complete",
                "sentiment_score": avg_sentiment,
                "scores": scores,
                "pillars": pillars,
                "model_perceptions": model_perceptions,
                "competitor_positions": competitor_positions,
                "trend_data": trend_data,
                "completed_at": datetime.now(timezone.utc),
            }},
        )

        progress.set_status(report_id, "complete")

        task_duration = round((time.perf_counter() - task_start) * 1000, 1)
        logger.info(
            "Analysis complete for %s (%.0fms, sentiment=%.2f)",
            brand,
            task_duration,
            avg_sentiment,
            extra={
                "report_id": report_id,
                "brand": brand,
                "task_name": "run_analysis",
                "duration_ms": task_duration,
            },
        )

        progress.publish_event(report_id, "analysis.complete", {
            "report_id": report_id,
            "brand": brand,
            "sentiment": avg_sentiment,
        })

    except Exception as exc:
        db = get_sync_db()
        db.reports.update_one(
            {"_id": report_id},
            {"$set": {"status": "failed"}},
        )

        progress.set_status(report_id, "failed")
        progress.publish_event(report_id, "analysis.failed", {
            "report_id": report_id,
            "error": "Analysis failed. Please try again.",
        })
        logger.exception("Analysis failed for report %s", report_id)
        raise self.retry(exc=exc, countdown=5)


# ── Scheduled analysis ───────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.process_schedules")
def process_schedules():
    """Check for due schedules and dispatch analysis tasks."""
    import uuid
    from app.core.progress import init as init_progress

    db = get_sync_db()
    now = datetime.now(timezone.utc)

    # Import model mapping from reports route
    from app.routes.reports import ALLOWED_MODELS

    due = list(db.schedules.find({"active": True, "next_run": {"$lte": now}}))
    for schedule in due:
        user_id = schedule["user_id"]
        brand = schedule["brand"]
        competitors = schedule.get("competitors", [])
        interval_days = schedule.get("interval_days", 30)
        model_key = schedule.get("model", "sonnet")
        model_id = ALLOWED_MODELS.get(model_key, ALLOWED_MODELS["sonnet"])

        # Create a report
        report_id = str(uuid.uuid4())
        db.reports.insert_one({
            "_id": report_id,
            "user_id": user_id,
            "brand": brand,
            "competitors": competitors,
            "model": model_key,
            "status": "processing",
            "sentiment_score": None,
            "scores": {},
            "pillars": [],
            "model_perceptions": [],
            "competitor_positions": [],
            "trend_data": [],
            "created_at": now,
            "completed_at": None,
        })

        init_progress(report_id, ["analysis"])
        run_analysis.delay(report_id, brand, competitors, user_id, model_id)

        # Advance next_run
        from datetime import timedelta
        db.schedules.update_one(
            {"_id": schedule["_id"]},
            {"$set": {"next_run": now + timedelta(days=interval_days)}},
        )

        logger.info(
            "Dispatched scheduled analysis for %s (schedule %s)",
            brand,
            schedule["_id"],
        )
