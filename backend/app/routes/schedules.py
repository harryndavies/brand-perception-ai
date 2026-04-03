from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.database import get_async_db
from app.models.schedule import Schedule
from app.models.user import User
from app.services.providers import MODELS

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class CreateScheduleRequest(BaseModel):
    brand: str = Field(..., min_length=1, max_length=100)
    competitors: list[str] = Field(default=[], max_length=3)
    models: list[str] = Field(default=["claude-sonnet"], min_length=1, max_length=7)
    interval_days: int = Field(default=30, ge=1, le=365)


@router.get("")
async def list_schedules(user: User = Depends(get_current_user)):
    db = get_async_db()
    cursor = db.schedules.find({"user_id": user.id, "active": True}).sort("created_at", -1)
    docs = await cursor.to_list(length=50)
    return [Schedule.from_doc(doc).model_dump() for doc in docs]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_schedule(
    body: CreateScheduleRequest,
    user: User = Depends(get_current_user),
):
    has_key = bool(user.api_keys) or user.encrypted_api_key is not None
    if not has_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please add at least one API key before scheduling analyses.",
        )

    for mk in body.models:
        if mk not in MODELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown model: {mk}",
            )

    db = get_async_db()

    schedule = Schedule(
        user_id=user.id,
        brand=body.brand,
        competitors=body.competitors,
        models=body.models,
        interval_days=body.interval_days,
        next_run=datetime.now(timezone.utc) + timedelta(days=body.interval_days),
    )
    await db.schedules.insert_one(schedule.to_doc())
    return schedule.model_dump()


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str, user: User = Depends(get_current_user)):
    db = get_async_db()
    result = await db.schedules.update_one(
        {"_id": schedule_id, "user_id": user.id},
        {"$set": {"active": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return {"ok": True}
