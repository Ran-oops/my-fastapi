from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_active_superuser
from app.common.pagination import PaginatedResponse
from app.tasks.db import get_sync_session
from app.tasks.models import TaskStatus
from app.tasks.schemas import TaskRead
from app.tasks.service import cancel_task, get_task, list_tasks, retry_task


router = APIRouter()


@router.get("", response_model=PaginatedResponse[TaskRead])
def get_tasks(
    status: TaskStatus | None = Query(None),
    task_name: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    _current_user=Depends(get_current_active_superuser),
):
    session = next(get_sync_session())
    try:
        status_value = status.value if status else None
        records, total = list_tasks(session, status=status_value, task_name=task_name, page=page, page_size=page_size)
        total_pages = (total + page_size - 1) // page_size
        return PaginatedResponse(
            data=[TaskRead.model_validate(r) for r in records],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    finally:
        session.close()


@router.get("/{task_id}", response_model=TaskRead)
def get_task_detail(
    task_id: int,
    _current_user=Depends(get_current_active_superuser),
):
    session = next(get_sync_session())
    try:
        task_record = get_task(session, task_id)
        if not task_record:
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskRead.model_validate(task_record)
    finally:
        session.close()


@router.post("/{task_id}/retry", response_model=TaskRead)
def retry_failed_task(
    task_id: int,
    _current_user=Depends(get_current_active_superuser),
):
    session = next(get_sync_session())
    try:
        task_record = retry_task(session, task_id)
        return TaskRead.model_validate(task_record)
    finally:
        session.close()


@router.post("/{task_id}/revive", response_model=TaskRead)
def revive_dead_task(
    task_id: int,
    _current_user=Depends(get_current_active_superuser),
):
    session = next(get_sync_session())
    try:
        task_record = retry_task(session, task_id)
        return TaskRead.model_validate(task_record)
    finally:
        session.close()


@router.delete("/{task_id}", response_model=TaskRead)
def cancel_pending_task(
    task_id: int,
    _current_user=Depends(get_current_active_superuser),
):
    session = next(get_sync_session())
    try:
        task_record = cancel_task(session, task_id)
        return TaskRead.model_validate(task_record)
    finally:
        session.close()
