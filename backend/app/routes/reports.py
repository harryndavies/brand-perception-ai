from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt as jose_jwt
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_async_db
from app.core.enums import DEFAULT_MODEL
from app.models.report import Report
from app.models.user import User
from app.services.analysis import stream_progress
from app.services.providers import get_available_models
from app.services.rate_limiter import check_rate_limit
from app.services.report_service import create_report as create_report_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


class CreateReportRequest(BaseModel):
    brand: str = Field(..., min_length=1, max_length=100)
    competitors: list[str] = Field(default=[], max_length=3)
    models: list[str] = Field(default=[DEFAULT_MODEL], min_length=1, max_length=7)


@router.get("")
async def list_reports(user: User = Depends(get_current_user)):
    db = get_async_db()
    cursor = db.reports.find({"user_id": user.id}).sort("created_at", -1)
    docs = await cursor.to_list(length=100)
    return [Report.from_doc(doc).model_dump() for doc in docs]


@router.get("/models")
async def list_models():
    """Return available models for the frontend."""
    return get_available_models()


@router.get("/{report_id}")
async def get_report(report_id: str, user: User = Depends(get_current_user)):
    db = get_async_db()
    doc = await db.reports.find_one({"_id": report_id, "user_id": user.id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return Report.from_doc(doc).model_dump()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_report(
    body: CreateReportRequest,
    user: User = Depends(get_current_user),
):
    check_rate_limit(f"ratelimit:create:{user.id}", settings.rate_limit_window, settings.rate_limit_max)
    return await create_report_service(user, body.brand, body.competitors, body.models)


@router.get("/{report_id}/stream")
async def stream_report(report_id: str, token: str):
    # NOTE: SSE (EventSource API) does not support custom headers, so the JWT
    # is passed as a query parameter.  This is standard for SSE but means the
    # token may appear in server/proxy access logs.  Use HTTPS in production.
    try:
        payload = jose_jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
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
