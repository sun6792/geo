"""Public health-check endpoint (no authentication required)."""

from fastapi import APIRouter

from app.core.database import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/api/health")
async def health_check():
    """Public health check — used by load balancers and monitoring."""
    db_ok = await check_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "version": "0.1.0",
    }
