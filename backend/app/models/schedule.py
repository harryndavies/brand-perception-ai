import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.core.enums import DEFAULT_MODEL


class Schedule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    brand: str
    competitors: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=lambda: [DEFAULT_MODEL])
    interval_days: int = 30  # default monthly
    next_run: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_doc(self) -> dict:
        data = self.model_dump()
        data["_id"] = data.pop("id")
        return data

    @classmethod
    def from_doc(cls, doc: dict) -> "Schedule":
        doc["id"] = doc.pop("_id")
        return cls(**doc)
