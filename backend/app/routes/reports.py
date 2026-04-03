from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.database import get_async_db
from app.core.progress import _get_redis, init as init_progress
from app.models.report import Report
from app.models.user import User
from app.services.analysis import stream_progress
from app.services.providers import MODELS
from app.tasks import run_analysis

router = APIRouter(prefix="/api/reports", tags=["reports"])


class CreateReportRequest(BaseModel):
    brand: str = Field(..., min_length=1, max_length=100)
    competitors: list[str] = Field(default=[], max_length=3)
    models: list[str] = Field(default=["claude-sonnet"], min_length=1, max_length=7)


@router.get("")
async def list_reports(user: User = Depends(get_current_user)):
    db = get_async_db()
    cursor = db.reports.find({"user_id": user.id}).sort("created_at", -1)
    docs = await cursor.to_list(length=100)
    return [Report.from_doc(doc).model_dump() for doc in docs]


@router.get("/models")
async def list_models():
    """Return available models for the frontend."""
    from app.services.providers import get_available_models
    return get_available_models()


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

    # Check user has at least one API key
    has_key = bool(user.api_keys) or user.encrypted_api_key is not None
    if not has_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please add at least one API key before running an analysis.",
        )

    # Validate all requested models exist
    for mk in body.models:
        if mk not in MODELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown model: {mk}",
            )

    # Check user has keys for all required providers
    required_providers = {MODELS[mk]["provider"] for mk in body.models}
    available_providers = set(user.api_keys.keys())
    if user.encrypted_api_key:
        available_providers.add("anthropic")
    missing = required_providers - available_providers
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing API keys for: {', '.join(missing)}. Add them in settings.",
        )

    db = get_async_db()

    report = Report(
        user_id=user.id,
        brand=body.brand,
        competitors=body.competitors,
        models=body.models,
        status="processing",
    )
    await db.reports.insert_one(report.to_doc())

    # Seed Redis with one progress entry per model
    init_progress(report.id, body.models)

    # Dispatch analysis to Celery worker
    run_analysis.delay(report.id, report.brand, report.competitors, user.id, body.models)

    return report.model_dump()


@router.get("/{report_id}/stream")
async def stream_report(report_id: str, token: str):
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
