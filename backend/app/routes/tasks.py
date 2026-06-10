"""
Tasks API
Handles task creation, assignment, completion, and filtering.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from auth import get_current_user, require_role
from db_models import Task, TaskStatus, TaskPriority, User as UserORM, UserRole
import uuid

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    dog_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    q = select(Task).where(Task.organization_id == org_id)

    if status:
        q = q.where(Task.status == status.upper())
    else:
        q = q.where(Task.status.notin_(['COMPLETED', 'CANCELLED']))
    if assigned_to:
        q = q.where(Task.assigned_to == assigned_to)
    if priority:
        q = q.where(Task.priority == priority.upper())
    if dog_id:
        q = q.where(Task.dog_id == dog_id)

    q = q.order_by(Task.due_date.asc().nullsfirst(), Task.priority.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return [_task_dict(t) for t in result.scalars().all()]


@router.post("")
async def create_task(
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    title = data.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    task = Task(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        title=title,
        description=data.get("description"),
        status=TaskStatus.PENDING,
        priority=data.get("priority", "MEDIUM").upper(),
        assigned_to=data.get("assigned_to"),
        created_by=current_user.id,
        dog_id=data.get("dog_id"),
        stay_id=data.get("stay_id"),
        due_date=_parse_date(data.get("due_date")),
        checklist=data.get("checklist", []),
        tags=data.get("tags", []),
        recurrence=data.get("recurrence"),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)


@router.get("/my")
async def get_my_tasks(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(
            Task.organization_id == current_user.organization_id,
            Task.assigned_to == current_user.id,
            Task.status.notin_(['COMPLETED', 'CANCELLED']),
        ).order_by(Task.due_date.asc().nullsfirst(), Task.priority.desc())
    )
    return [_task_dict(t) for t in result.scalars().all()]


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, current_user.organization_id, db)
    return _task_dict(task)


@router.patch("/{task_id}")
async def update_task(
    task_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, current_user.organization_id, db)

    allowed = ["title", "description", "priority", "assigned_to",
               "due_date", "checklist", "tags", "recurrence", "dog_id"]
    for field in allowed:
        if field in data:
            val = data[field]
            if field == "due_date":
                val = _parse_date(val)
            elif field == "priority":
                val = val.upper() if val else val
            setattr(task, field, val)

    await db.commit()
    await db.refresh(task)
    return _task_dict(task)


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, current_user.organization_id, db)
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(timezone.utc)
    task.completed_by = current_user.id
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, current_user.organization_id, db)
    task.status = TaskStatus.CANCELLED
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)


@router.patch("/{task_id}/checklist")
async def update_checklist(
    task_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, current_user.organization_id, db)
    task.checklist = data.get("checklist", [])
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)


async def _get_task_or_404(task_id: str, org_id: str, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.organization_id == org_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return t

def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

def _task_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "status": t.status.value if hasattr(t.status, 'value') else t.status,
        "priority": t.priority.value if hasattr(t.priority, 'value') else t.priority,
        "assigned_to": t.assigned_to,
        "created_by": t.created_by,
        "dog_id": t.dog_id,
        "stay_id": t.stay_id,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "completed_by": t.completed_by,
        "checklist": t.checklist or [],
        "tags": t.tags or [],
        "recurrence": t.recurrence,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }
