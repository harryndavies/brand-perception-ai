import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    hashed_password: str
    team: str = "Default"
    encrypted_api_key: str | None = None  # deprecated, kept for migration
    api_keys: dict[str, str] = Field(default_factory=dict)  # provider -> encrypted key
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_doc(self) -> dict:
        """Convert to MongoDB document."""
        data = self.model_dump()
        data["_id"] = data.pop("id")
        return data

    @classmethod
    def from_doc(cls, doc: dict) -> "User":
        """Create from MongoDB document."""
        doc["id"] = doc.pop("_id")
        return cls(**doc)
