from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.database import get_async_db
from app.models.report import Report
from app.models.user import User
from app.services.analysis import stream_progress
from app.tasks import run_analysis

router = APIRouter(prefix="/api/reports", tags=["reports"])


class CreateReportRequest(BaseModel):
    brand: str
    competitors: list[str] = []


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


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_report(
    body: CreateReportRequest,
    user: User = Depends(get_current_user),
):
    db = get_async_db()

    report = Report(
        user_id=user.id,
        brand=body.brand,
        competitors=body.competitors[:3],
        status="processing",
    )
    await db.reports.insert_one(report.to_doc())

    # Dispatch analysis to Celery worker via Redis broker
    run_analysis.delay(report.id, report.brand, report.competitors)

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
