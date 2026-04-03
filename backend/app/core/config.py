"""Centralised application settings using pydantic-settings.

All environment variables are validated at startup and accessible via the
module-level ``settings`` instance.  In tests, override individual values
with ``settings.model_copy(update={...})``.
"""

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Environment ──────────────────────────────────────────────────────
    env: str = "development"

    # ── Auth / JWT ───────────────────────────────────────────────────────
    secret_key: str = "dev-secret-change-me-in-production"
    encryption_key: str = "dev-encryption-key-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000"]

    # ── MongoDB ──────────────────────────────────────────────────────────
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "perception"

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Rate limiting ────────────────────────────────────────────────────
    rate_limit_window: int = 60  # seconds
    rate_limit_max: int = 5  # max analyses per window
    auth_rate_limit_window: int = 300  # seconds
    auth_rate_limit_max: int = 10  # max auth attempts per window

    # ── Validators ───────────────────────────────────────────────────────

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> object:
        """Accept both JSON arrays and comma-separated strings."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @model_validator(mode="after")
    def check_production_secrets(self) -> "Settings":
        if self.env == "production":
            if self.secret_key == "dev-secret-change-me-in-production":
                raise ValueError("SECRET_KEY must be set in production")
            if self.encryption_key == "dev-encryption-key-change-me":
                raise ValueError("ENCRYPTION_KEY must be set in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
