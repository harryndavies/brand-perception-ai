import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Report(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    brand: str
    competitors: list[str] = []
    models: list[str] = ["claude-sonnet"]
    status: str = "pending"
    sentiment_score: Optional[float] = None
    scores: dict = {}
    pillars: list[dict] = []
    model_perceptions: list[dict] = []
    competitor_positions: list[dict] = []
    trend_data: list[dict] = []
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
