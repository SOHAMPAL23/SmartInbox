"""
app/middleware.py
-----------------
Centralised error-handling and request/response logging middleware.
"""

import time
import traceback
import uuid

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger("middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log every request/response with:
      - request_id (UUID, injected into request.state)
      - method, path, status_code
      - duration in milliseconds
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.perf_counter()
        logger.info(
            "REQ [%s] %s %s | ip=%s",
            request_id, request.method, request.url.path,
            request.client.host if request.client else "unknown",
        )

        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "RES [%s] %s %s | status=%d | %.1f ms",
            request_id, request.method, request.url.path,
            response.status_code, duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
        return response


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    """
    Catch any unhandled exception from a route handler,
    log it with a full traceback, and return a clean JSON 500 response
    instead of an HTML error page.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "?")
            logger.error(
                "Unhandled exception | id=%s | %s %s\n%s",
                request_id,
                request.method, request.url.path,
                traceback.format_exc(),
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail":     "An internal server error occurred.",
                    "request_id": request_id,
                },
            )
