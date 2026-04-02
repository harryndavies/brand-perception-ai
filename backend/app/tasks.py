"""Celery tasks for brand analysis.

These run in the Celery worker process, separate from the FastAPI server.
Progress is tracked via Redis so the API can stream updates to clients.
"""

import json
import logging
import os
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

_anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ── Prompt ──────────────────────────────────────────────────────────────────

ANALYSIS_PROMPT = """Analyse the brand "{brand}" with competitors [{competitors}].

Return a single JSON object with exactly this structure. Do not include any text outside the JSON.

{{
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


def _build_trend(brand: str, current_sentiment: float) -> list[dict]:
    """Build trend data from past completed analyses of this brand."""
    db = get_sync_db()
    past = list(
        db.reports.find(
            {"brand": {"$regex": f"^{re.escape(brand)}$", "$options": "i"}, "status": "complete"},
            {"sentiment_score": 1, "completed_at": 1},
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
                "volume": 1,
            })

    # Always include the current analysis as the latest point
    data.append({
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sentiment": current_sentiment,
        "volume": 1,
    })

    return data


# ── Main Celery task ─────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.run_analysis", bind=True, max_retries=2)
def run_analysis(self, report_id: str, brand: str, competitors: list[str]):
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

        message = _anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
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

        pillars = result.get("pillars", [])
        competitor_positions = result.get("competitor_analysis", {}).get("competitor_positions", [])

        sentiments = [s["sentiment"] for _, s in sections]
        avg_sentiment = round(sum(sentiments) / len(sentiments), 2)
        trend_data = _build_trend(brand, avg_sentiment)

        progress.emit(report_id, "analysis", "complete", 100)

        # Persist to database
        db = get_sync_db()
        db.reports.update_one(
            {"_id": report_id},
            {"$set": {
                "status": "complete",
                "sentiment_score": avg_sentiment,
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
            "error": str(exc),
        })
        logger.exception("Analysis failed for report %s", report_id)
        raise self.retry(exc=exc, countdown=5)
