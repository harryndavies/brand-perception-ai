"""Structured JSON logging with correlation ID support.

Produces machine-readable log lines that integrate with log aggregation
tools like Datadog, CloudWatch, or GCP Cloud Logging.
"""

import json
import logging
import sys
from contextvars import ContextVar

# Correlation ID propagated across async contexts and threads
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON with correlation context."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id.get("-"),
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include extra fields passed via logger.info("msg", extra={...})
        for key in ("report_id", "brand", "task_name", "duration_ms", "status_code",
                     "method", "path", "user_id", "job_id", "model"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        return json.dumps(log_entry)


def setup_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging for the application."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quieten noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
