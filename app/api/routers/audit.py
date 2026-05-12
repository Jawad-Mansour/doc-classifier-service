"""Audit log routes (read-only)."""

from fastapi import APIRouter, Depends

from app.api.deps.permissions import require_permission
from app.auth.casbin import RESOURCE_AUDIT_LOG, ACTION_READ
from app.api.schemas import AuditLogResponse
from app.auth.users import UserRead
from app.services.audit_service import list_logs

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get("", response_model=list[AuditLogResponse])
async def get_audit_logs(
    user: UserRead = Depends(require_permission(RESOURCE_AUDIT_LOG, ACTION_READ)),
    skip: int = 0,
    limit: int = 50,
) -> list[AuditLogResponse]:
    """Get audit logs (read-only)."""
    return await list_logs(skip=skip, limit=limit)
