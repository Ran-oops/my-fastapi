from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_session
from app.common.pagination import PaginatedResponse, PaginationParams
from app.common.schemas import DataResponse
from app.core.exceptions import NotFoundException
from app.modules.audit import service as audit_service
from app.modules.audit.schemas import AuditLogRead
from app.modules.users.models import User


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[AuditLogRead])
async def get_audit_logs(
    pagination: PaginationParams = Depends(),
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    if user_id is not None:
        logs = await audit_service.get_audit_logs_by_user(
            session, user_id, skip=pagination.skip, limit=pagination.limit
        )
        total = await audit_service.get_audit_logs_count_by_user(session, user_id)
    elif resource_type is not None and resource_id is not None:
        logs = await audit_service.get_audit_logs_by_resource(
            session, resource_type, resource_id, skip=pagination.skip, limit=pagination.limit
        )
        total = await audit_service.get_audit_logs_count_by_resource(session, resource_type, resource_id)
    else:
        logs = await audit_service.get_audit_logs(session, skip=pagination.skip, limit=pagination.limit)
        total = await audit_service.get_audit_logs_count(session)

    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        data=logs,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        message="Audit logs retrieved successfully",
    )


@router.get("/{log_id}", response_model=DataResponse[AuditLogRead])
async def get_audit_log(
    log_id: int,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_active_superuser),
):
    log = await audit_service.get_audit_log_by_id(session, log_id)
    if not log:
        raise NotFoundException(f"Audit log {log_id} not found")
    return DataResponse(data=log)
