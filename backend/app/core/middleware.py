"""Custom middleware: tenant context, request ID, request logging, CORS."""

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.logging_config import logger


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extract customer_id from request header and store in request.state.

    The frontend sends `X-Customer-Id` after login. This middleware makes it
    available to all downstream dependencies via `request.state.customer_id`.
    """

    async def dispatch(self, request: Request, call_next):
        customer_id = request.headers.get("X-Customer-Id")
        if customer_id:
            request.state.customer_id = customer_id
        response = await call_next(request)
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID (X-Request-ID) for tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client=request.client.host if request.client else "-",
        )
        return response


def setup_middleware(app: FastAPI) -> None:
    """Register all middleware on the FastAPI application."""

    # CORS — must be outermost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Tenant context
    app.add_middleware(TenantContextMiddleware)

    # Request ID
    app.add_middleware(RequestIDMiddleware)

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
