from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.database import get_async_db
from app.models.user import User

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("")
async def get_usage(user: User = Depends(get_current_user)):
    db = get_async_db()
    total = await db.reports.count_documents({"user_id": user.id})
    return {
        "credits_used": total,
        "credits_total": 100,
        "analyses_this_month": total,
    }
