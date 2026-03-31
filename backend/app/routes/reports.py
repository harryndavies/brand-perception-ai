import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.core.database import engine, get_session
from app.models.report import Report
from app.models.user import User
from app.services.analysis import run_analysis, stream_progress

router = APIRouter(prefix="/api/reports", tags=["reports"])


class CreateReportRequest(BaseModel):
    brand: str
    competitors: list[str] = []


@router.get("")
def list_reports(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    reports = session.exec(
        select(Report).where(Report.user_id == user.id).order_by(Report.created_at.desc())
    ).all()
    return reports


@router.get("/{report_id}")
def get_report(
    report_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = session.exec(
        select(Report).where(Report.id == report_id, Report.user_id == user.id)
    ).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_report(
    body: CreateReportRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = Report(
        user_id=user.id,
        brand=body.brand,
        competitors=body.competitors[:3],
        status="processing",
    )
    session.add(report)
    session.commit()
    session.refresh(report)

    # Fire off analysis in the background (non-blocking)
    asyncio.create_task(
        run_analysis(report.id, report.brand, report.competitors)
    )

    return report


@router.get("/{report_id}/stream")
async def stream_report(
    report_id: str,
    token: str,
):
    # SSE can't send auth headers, so we accept token as query param
    from jose import JWTError, jwt as jose_jwt
    from app.core.config import SECRET_KEY, ALGORITHM

    try:
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub", "")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    with Session(engine) as session:
        report = session.exec(
            select(Report).where(Report.id == report_id, Report.user_id == user_id)
        ).first()
        if not report:
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
