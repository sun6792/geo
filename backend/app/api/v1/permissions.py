"""Permission listing endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.account import PermissionResponse
from app.services.account_service import AccountService

router = APIRouter(tags=["Permissions"])


@router.get("/", response_model=list[PermissionResponse])
async def list_permissions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all available permissions in the system."""
    svc = AccountService(db, current_user["customer_id"])
    return await svc.list_permissions()
