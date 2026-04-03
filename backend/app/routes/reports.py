from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.database import get_async_db
from app.core.progress import _get_redis, init as init_progress
from app.models.report import Report
from app.models.user import User
from app.services.analysis import stream_progress
from app.tasks import run_analysis

router = APIRouter(prefix="/api/reports", tags=["reports"])


ALLOWED_MODELS = {
    "sonnet": "claude-sonnet-4-20250514",
    "haiku": "claude-haiku-4-5-20251001",
    "opus": "claude-opus-4-20250514",
}


class CreateReportRequest(BaseModel):
    brand: str = Field(..., min_length=1, max_length=100)
    competitors: list[str] = Field(default=[], max_length=3)
    model: Literal["sonnet", "haiku", "opus"] = "sonnet"


@router.get("")
async def list_reports(user: User = Depends(get_current_user)):
    db = get_async_db()
    cursor = db.reports.find({"user_id": user.id}).sort("created_at", -1)
    docs = await cursor.to_list(length=100)
    return [Report.from_doc(doc).model_dump() for doc in docs]


@router.get("/{report_id}")
async def get_report(report_id: str, user: User = Depends(get_current_user)):
    db = get_async_db()
    doc = await db.reports.find_one({"_id": report_id, "user_id": user.id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return Report.from_doc(doc).model_dump()


_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 5  # max analyses per window


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_report(
    body: CreateReportRequest,
    user: User = Depends(get_current_user),
):
    # Rate limit per user
    r = _get_redis()
    rate_key = f"ratelimit:create:{user.id}"
    count = r.incr(rate_key)
    if count == 1:
        r.expire(rate_key, _RATE_LIMIT_WINDOW)
    if count > _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again shortly.",
        )

    if not user.encrypted_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please add your Anthropic API key before running an analysis.",
        )

    db = get_async_db()

    model_id = ALLOWED_MODELS[body.model]

    report = Report(
        user_id=user.id,
        brand=body.brand,
        competitors=body.competitors,
        model=body.model,
        status="processing",
    )
    await db.reports.insert_one(report.to_doc())

    # Seed Redis so SSE stream has data before the worker picks up the task
    init_progress(report.id, ["analysis"])

    # Dispatch analysis to Celery worker via Redis broker
    run_analysis.delay(report.id, report.brand, report.competitors, user.id, model_id)

    return report.model_dump()


@router.get("/{report_id}/stream")
async def stream_report(report_id: str, token: str):
    # SSE can't send auth headers, so we accept token as query param
    from jose import JWTError, jwt as jose_jwt
    from app.core.config import SECRET_KEY, ALGORITHM

    try:
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub", "")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    db = get_async_db()
    doc = await db.reports.find_one({"_id": report_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return StreamingResponse(
        stream_progress(report_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
