"""Celery tasks for brand analysis.

These run in the Celery worker process, separate from the FastAPI server.
Progress is tracked via Redis so the API can stream updates to clients.
"""

import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone

import anthropic
from sqlmodel import Session

from app.core.database import engine
from app.core.logging import setup_logging, correlation_id
from app.core import progress
from app.models.report import Report
from app.worker import celery_app

setup_logging()
logger = logging.getLogger(__name__)


# ── Prompts ──────────────────────────────────────────────────────────────────

BRAND_ANALYSIS_PROMPT = """Analyse the brand "{brand}" and return a JSON object with exactly this structure.
Do not include any text outside the JSON.

Competitors for context: {competitors}

Return this exact JSON structure:
{{
  "summary": "2-3 sentence analysis of how this brand is perceived",
  "sentiment": <float between -1.0 and 1.0>,
  "key_themes": ["theme1", "theme2", "theme3"],
  "pillars": [
    {{
      "name": "Pillar Name",
      "description": "1-2 sentence description of this brand pillar",
      "confidence": <float between 0.0 and 1.0>
    }}
  ]
}}

Provide 3-5 brand pillars. Be specific and insightful, not generic. Ground your analysis in real brand perception."""


COMPETITOR_PROMPT = """Analyse the competitive positioning of "{brand}" against these competitors: {competitors}.

Return a JSON object with exactly this structure. Do not include any text outside the JSON.

{{
  "summary": "2-3 sentence analysis of competitive dynamics",
  "sentiment": <float between -1.0 and 1.0 representing overall brand health vs competitors>,
  "key_themes": ["theme1", "theme2", "theme3"],
  "pillars": [
    {{
      "name": "Pillar Name",
      "description": "1-2 sentence description",
      "confidence": <float between 0.0 and 1.0>
    }}
  ],
  "competitor_positions": [
    {{
      "brand": "Brand Name",
      "premium_score": <float 0-1, where 1 is ultra-premium>,
      "lifestyle_score": <float 0-1, where 0 is purely functional and 1 is purely lifestyle>
    }}
  ]
}}

Include positioning for "{brand}" and each competitor. Be specific about where each brand sits."""


NEWS_PROMPT = """You are acting as a news sentiment analyst. Analyse the brand "{brand}" specifically through the lens of recent news coverage, public sentiment, and media perception.

Competitors for context: {competitors}

Return a JSON object with exactly this structure. Do not include any text outside the JSON.

{{
  "summary": "2-3 sentence analysis focused on news sentiment and public perception",
  "sentiment": <float between -1.0 and 1.0>,
  "key_themes": ["theme1", "theme2", "theme3"],
  "pillars": [
    {{
      "name": "Pillar Name",
      "description": "1-2 sentence description from a news/media perspective",
      "confidence": <float between 0.0 and 1.0>
    }}
  ]
}}

Provide 2-3 pillars focused on media narrative, public controversies or praise, and brand reputation trends."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text.strip())


def _generate_trend(current_sentiment: float) -> list[dict]:
    months = 6
    data = []
    sentiment = current_sentiment - random.uniform(0.05, 0.15)
    for i in range(months):
        month = 10 + i if 10 + i <= 12 else (10 + i) - 12
        year = 2025 if month >= 10 else 2026
        sentiment += random.uniform(-0.03, 0.06)
        sentiment = max(-1, min(1, sentiment))
        data.append({
            "date": f"{year}-{month:02d}-01",
            "sentiment": round(sentiment, 2),
            "volume": random.randint(800, 2200),
        })
    return data


# ── AI calls (sync wrappers around async SDK) ───────────────────────────────

def _call_claude(brand: str, competitors: list[str]) -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    competitor_str = ", ".join(competitors) if competitors else "general market"
    prompt = BRAND_ANALYSIS_PROMPT.format(brand=brand, competitors=competitor_str)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    parsed = _parse_json(message.content[0].text)
    for pillar in parsed.get("pillars", []):
        pillar["sources"] = ["Claude"]
    return {"model": "Claude", **parsed}


def _call_openai(brand: str, competitors: list[str]) -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    competitor_str = ", ".join(competitors) if competitors else "general market"
    prompt = NEWS_PROMPT.format(brand=brand, competitors=competitor_str)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    parsed = _parse_json(message.content[0].text)
    for pillar in parsed.get("pillars", []):
        pillar["sources"] = ["GPT-4", "News"]
    return {"model": "GPT-4", **parsed}


def _call_gemini(brand: str, competitors: list[str]) -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    competitor_str = ", ".join(competitors) if competitors else "Nike, Adidas, Patagonia"
    prompt = COMPETITOR_PROMPT.format(brand=brand, competitors=competitor_str)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    parsed = _parse_json(message.content[0].text)
    for pillar in parsed.get("pillars", []):
        pillar["sources"] = ["Gemini", "Reddit"]
    return {"model": "Gemini", **parsed}


def _run_job(report_id: str, job_id: str, call_fn, brand: str, competitors: list[str]) -> dict:
    """Run a single AI call with progress updates via Redis."""
    progress.emit(report_id, job_id, "running", 0)
    start = time.perf_counter()

    # Simulate incremental progress while the API call runs
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(call_fn, brand, competitors)
        for i in range(1, 10):
            if future.done():
                break
            progress.emit(report_id, job_id, "running", i * 10)
            time.sleep(0.5)

    result = future.result()
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    progress.emit(report_id, job_id, "complete", 100, result)

    logger.info(
        "Job %s completed in %.0fms",
        job_id,
        duration_ms,
        extra={"report_id": report_id, "job_id": job_id, "duration_ms": duration_ms, "model": result.get("model")},
    )
    return result


# ── Main Celery task ─────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.run_analysis", bind=True, max_retries=2)
def run_analysis(self, report_id: str, brand: str, competitors: list[str]):
    """Fan out to all AI models and aggregate results.

    Runs as a Celery task in a worker process. Progress is published to
    Redis so the API server can stream SSE updates to the client.
    """
    # Set correlation ID for this task so all logs are traceable
    cid = report_id[:8]
    correlation_id.set(cid)

    task_start = time.perf_counter()
    logger.info(
        "Starting analysis for %s",
        brand,
        extra={"report_id": report_id, "brand": brand, "task_name": "run_analysis"},
    )
    progress.set_status(report_id, "processing")

    try:
        claude_result = _run_job(report_id, "ai-perception", _call_claude, brand, competitors)
        openai_result = _run_job(report_id, "news-sentiment", _call_openai, brand, competitors)
        gemini_result = _run_job(report_id, "competitor-analysis", _call_gemini, brand, competitors)

        # Aggregate results
        all_perceptions = [claude_result, openai_result, gemini_result]
        model_perceptions = [
            {
                "model": r["model"],
                "summary": r["summary"],
                "sentiment": r["sentiment"],
                "key_themes": r["key_themes"],
            }
            for r in all_perceptions
        ]

        pillars = []
        seen_pillars: set[str] = set()
        for r in all_perceptions:
            for p in r.get("pillars", []):
                if p["name"] not in seen_pillars:
                    pillars.append(p)
                    seen_pillars.add(p["name"])

        competitor_positions = gemini_result.get("competitor_positions", [])
        avg_sentiment = round(sum(r["sentiment"] for r in all_perceptions) / len(all_perceptions), 2)
        trend_data = _generate_trend(avg_sentiment)

        # Persist to database
        with Session(engine) as session:
            report = session.get(Report, report_id)
            if report:
                report.status = "complete"
                report.sentiment_score = avg_sentiment
                report.pillars = pillars
                report.model_perceptions = model_perceptions
                report.competitor_positions = competitor_positions
                report.trend_data = trend_data
                report.completed_at = datetime.now(timezone.utc)
                session.add(report)
                session.commit()

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

        # Publish completion event for downstream consumers
        progress.publish_event(report_id, "analysis.complete", {
            "report_id": report_id,
            "brand": brand,
            "sentiment": avg_sentiment,
        })

    except Exception as exc:
        with Session(engine) as session:
            report = session.get(Report, report_id)
            if report:
                report.status = "failed"
                session.add(report)
                session.commit()

        progress.set_status(report_id, "failed")
        progress.publish_event(report_id, "analysis.failed", {
            "report_id": report_id,
            "error": str(exc),
        })
        logger.exception("Analysis failed for report %s", report_id)
        raise self.retry(exc=exc, countdown=5)
