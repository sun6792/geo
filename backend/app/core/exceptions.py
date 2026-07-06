"""Custom application exceptions and global exception handlers."""

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception with HTTP status code."""

    def __init__(self, message: str, status_code: int = 400, detail: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class NotFoundException(AppException):
    """Resource not found (404)."""

    def __init__(self, resource: str, resource_id: str | None = None):
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} with id '{resource_id}' not found"
        super().__init__(msg, status_code=status.HTTP_404_NOT_FOUND)


class ForbiddenException(AppException):
    """Permission denied (403)."""

    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class ValidationException(AppException):
    """Business validation error (422)."""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class ConflictException(AppException):
    """Resource conflict (409)."""

    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class ReviewGateException(AppException):
    """Review workflow gate violation — content cannot proceed without passing review stages."""

    def __init__(self, stage: str, draft_id: str):
        super().__init__(
            f"Review gate blocked: '{stage}' must be approved before proceeding. Draft: {draft_id}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"stage": stage, "draft_id": draft_id},
        )


class KbSourceRequiredException(AppException):
    """Content brief must reference knowledge base assets."""

    def __init__(self):
        super().__init__(
            "Content creation requires at least one knowledge base source asset. "
            "Please build the knowledge base first.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


# ── Global handlers ───────────────────────────────────────────────


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "detail": exc.detail, "type": type(exc).__name__},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "type": type(exc).__name__},
    )
