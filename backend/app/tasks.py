"""Celery tasks for brand analysis.

These run in the Celery worker process, separate from the FastAPI server.
Progress is tracked via Redis so the API can stream updates to clients.
"""

import concurrent.futures
import logging
import re
import time
from datetime import datetime, timedelta, timezone

from app.core.database import get_sync_db
from app.core.enums import DEFAULT_MODEL, ReportStatus
from app.core.logging import setup_logging, correlation_id
from app.core import progress
from app.core.utils import parse_json_response
from app.services.providers import call_model, MODELS
from app.worker import celery_app

setup_logging()
logger = logging.getLogger(__name__)


# -- Prompt --------------------------------------------------------------------

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
      "sources": ["source"]
    }}
  ]
}}

Include 4-6 brand pillars covering perception, media narrative, and competitive positioning.
Include positioning for "{brand}" and each competitor in competitor_positions.
Be specific and insightful, not generic. Ground your analysis in real brand perception."""


# -- Helpers -------------------------------------------------------------------

def _build_trend(brand: str, avg_sentiment: float, model_keys: list[str]) -> list[dict]:
    """Build trend data from past completed analyses of this brand."""
    db = get_sync_db()
    past = list(
        db.reports.find(
            {"brand": {"$regex": f"^{re.escape(brand)}$", "$options": "i"}, "status": ReportStatus.COMPLETE},
            {"sentiment_score": 1, "completed_at": 1, "models": 1, "model": 1},
        )
        .sort("completed_at", 1)
        .limit(50)
    )

    data = []
    for doc in past:
        if doc.get("sentiment_score") is not None and doc.get("completed_at"):
            # Support both old single-model and new multi-model reports
            model = doc.get("models", [doc.get("model", DEFAULT_MODEL)])
            if isinstance(model, str):
                model = [model]
            data.append({
                "date": doc["completed_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sentiment": doc["sentiment_score"],
                "model": ", ".join(model),
            })

    # Current analysis
    data.append({
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sentiment": avg_sentiment,
        "model": ", ".join(model_keys),
    })

    return data


def _run_single_model(user_id: str, model_key: str, prompt: str, report_id: str) -> dict:
    """Call one model and emit completion when done."""
    start = time.perf_counter()

    spec = MODELS[model_key]
    result = call_model(user_id, model_key, prompt)

    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    progress.emit(report_id, model_key, ReportStatus.COMPLETE, 100)

    logger.info(
        "Model %s completed in %.0fms",
        spec["label"],
        duration_ms,
        extra={"report_id": report_id, "model": model_key, "duration_ms": duration_ms},
    )

    return {"model_key": model_key, "label": spec["label"], **result}


# -- Main Celery task ----------------------------------------------------------

@celery_app.task(name="app.tasks.run_analysis", bind=True, max_retries=2)
def run_analysis(self, report_id: str, brand: str, competitors: list[str], user_id: str, model_keys: list[str]):
    """Run analysis across one or more AI models in parallel.

    Runs as a Celery task in a worker process. Progress is published to
    Redis so the API server can stream SSE updates to the client.
    """
    cid = report_id[:8]
    correlation_id.set(cid)

    task_start = time.perf_counter()
    logger.info(
        "Starting analysis for %s with models %s",
        brand,
        model_keys,
        extra={"report_id": report_id, "brand": brand, "models": model_keys},
    )

    try:
        competitor_str = ", ".join(competitors) if competitors else "general market"
        prompt = ANALYSIS_PROMPT.format(brand=brand, competitors=competitor_str)

        # Mark all models as running before fan-out
        for mk in model_keys:
            progress.emit(report_id, mk, ReportStatus.PROCESSING, 0)

        # Fan out across models in parallel
        results = []
        if len(model_keys) == 1:
            results.append(_run_single_model(user_id, model_keys[0], prompt, report_id))
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(model_keys)) as pool:
                futures = {
                    pool.submit(_run_single_model, user_id, mk, prompt, report_id): mk
                    for mk in model_keys
                }
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())

        # Build model_perceptions -- one entry per model
        model_perceptions = []
        all_scores = {}
        all_pillars = []
        all_competitor_positions = []
        seen_pillars: set[str] = set()

        for r in results:
            label = r["label"]

            # Sections
            sections = [
                ("Brand Perception", r.get("brand_perception", {})),
                ("News Sentiment", r.get("news_sentiment", {})),
                ("Competitor Analysis", r.get("competitor_analysis", {})),
            ]

            sentiments = [s.get("sentiment", 0) for _, s in sections]
            avg = round(sum(sentiments) / len(sentiments), 2) if sentiments else 0

            themes = []
            for _, section in sections:
                themes.extend(section.get("key_themes", []))

            model_perceptions.append({
                "model": label,
                "summary": r.get("brand_perception", {}).get("summary", ""),
                "sentiment": avg,
                "key_themes": themes[:5],
            })

            # Scores -- average across models
            scores = r.get("scores", {})
            for k, v in scores.items():
                all_scores.setdefault(k, []).append(v)

            # Pillars -- deduplicate by name
            for p in r.get("pillars", []):
                p["sources"] = [label]
                if p["name"] not in seen_pillars:
                    all_pillars.append(p)
                    seen_pillars.add(p["name"])

            # Competitor positions -- take from first result that has them
            positions = r.get("competitor_analysis", {}).get("competitor_positions", [])
            if positions and not all_competitor_positions:
                all_competitor_positions = positions

        # Average scores across models
        averaged_scores = {k: round(sum(v) / len(v)) for k, v in all_scores.items()}

        # Overall sentiment
        all_sentiments = [mp["sentiment"] for mp in model_perceptions]
        avg_sentiment = round(sum(all_sentiments) / len(all_sentiments), 2)

        trend_data = _build_trend(brand, avg_sentiment, model_keys)

        # Persist to database
        db = get_sync_db()
        db.reports.update_one(
            {"_id": report_id},
            {"$set": {
                "status": ReportStatus.COMPLETE,
                "sentiment_score": avg_sentiment,
                "scores": averaged_scores,
                "pillars": all_pillars,
                "model_perceptions": model_perceptions,
                "competitor_positions": all_competitor_positions,
                "trend_data": trend_data,
                "completed_at": datetime.now(timezone.utc),
            }},
        )

        progress.set_status(report_id, ReportStatus.COMPLETE)

        task_duration = round((time.perf_counter() - task_start) * 1000, 1)
        logger.info(
            "Analysis complete for %s (%.0fms, sentiment=%.2f, models=%s)",
            brand,
            task_duration,
            avg_sentiment,
            model_keys,
            extra={
                "report_id": report_id,
                "brand": brand,
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
            {"$set": {"status": ReportStatus.FAILED}},
        )

        progress.set_status(report_id, ReportStatus.FAILED)
        progress.publish_event(report_id, "analysis.failed", {
            "report_id": report_id,
            "error": "Analysis failed. Please try again.",
        })
        logger.exception("Analysis failed for report %s", report_id)
        raise self.retry(exc=exc, countdown=5)


# -- Scheduled analysis --------------------------------------------------------

@celery_app.task(name="app.tasks.process_schedules")
def process_schedules():
    """Check for due schedules and dispatch analysis tasks."""
    import uuid
    from app.core.progress import init as init_progress

    db = get_sync_db()
    now = datetime.now(timezone.utc)

    due = list(db.schedules.find({"active": True, "next_run": {"$lte": now}}))
    for schedule in due:
        user_id = schedule["user_id"]
        brand = schedule["brand"]
        competitors = schedule.get("competitors", [])
        interval_days = schedule.get("interval_days", 30)
        model_keys = schedule["models"]

        report_id = str(uuid.uuid4())
        db.reports.insert_one({
            "_id": report_id,
            "user_id": user_id,
            "brand": brand,
            "competitors": competitors,
            "models": model_keys,
            "status": ReportStatus.PROCESSING,
            "sentiment_score": None,
            "scores": {},
            "pillars": [],
            "model_perceptions": [],
            "competitor_positions": [],
            "trend_data": [],
            "created_at": now,
            "completed_at": None,
        })

        init_progress(report_id, model_keys)
        run_analysis.delay(report_id, brand, competitors, user_id, model_keys)

        db.schedules.update_one(
            {"_id": schedule["_id"]},
            {"$set": {"next_run": now + timedelta(days=interval_days)}},
        )

        logger.info(
            "Dispatched scheduled analysis for %s (schedule %s)",
            brand,
            schedule["_id"],
        )
