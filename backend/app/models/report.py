import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from app.core.enums import DEFAULT_MODEL, ReportStatus


class Report(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    brand: str
    competitors: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=lambda: [DEFAULT_MODEL])
    status: ReportStatus = ReportStatus.PENDING
    sentiment_score: Optional[float] = None
    scores: dict = Field(default_factory=dict)
    pillars: list[dict] = Field(default_factory=list)
    model_perceptions: list[dict] = Field(default_factory=list)
    competitor_positions: list[dict] = Field(default_factory=list)
    trend_data: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def to_doc(self) -> dict:
        """Convert to MongoDB document."""
        data = self.model_dump()
        data["_id"] = data.pop("id")
        return data

    @classmethod
    def from_doc(cls, doc: dict) -> "Report":
        """Create from MongoDB document."""
        doc["id"] = doc.pop("_id")
        return cls(**doc)
