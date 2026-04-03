"""Shared enums and constants to replace magic strings throughout the codebase."""

from enum import StrEnum

DEFAULT_MODEL = "claude-sonnet"


class Provider(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


class ReportStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"
