from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.database import get_async_db
from app.models.schedule import Schedule
from app.models.user import User

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class CreateScheduleRequest(BaseModel):
    brand: str = Field(..., min_length=1, max_length=100)
    competitors: list[str] = Field(default=[], max_length=3)
    model: Literal["sonnet", "haiku", "opus"] = "sonnet"
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
    if not user.encrypted_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please add your Anthropic API key before scheduling analyses.",
        )

    db = get_async_db()

    schedule = Schedule(
        user_id=user.id,
        brand=body.brand,
        competitors=body.competitors,
        model=body.model,
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
