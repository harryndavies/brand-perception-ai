"""Request middleware for observability.

Adds correlation ID tracking and request/response logging to every request.
"""

import time
import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import correlation_id

logger = logging.getLogger(__name__)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Generates or propagates a correlation ID for each request.

    - Reads X-Correlation-ID from incoming headers (for distributed tracing)
    - Falls back to generating a new UUID
    - Sets the ID in contextvars so all downstream logs include it
    - Returns the ID in the response header
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Propagate or generate correlation ID
        cid = request.headers.get("x-correlation-id", str(uuid.uuid4())[:8])
        token = correlation_id.set(cid)

        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.error(
                "Request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "status_code": 500,
                },
            )
            raise
        finally:
            correlation_id.reset(token)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        response.headers["X-Correlation-ID"] = cid

        logger.info(
            "%s %s %s %.0fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response
