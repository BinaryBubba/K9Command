"""
Task Forms API
Staff-assignable form templates (e.g. facility inspection checklists).
Completions are tracked as form_submissions, optionally required before
a task can be marked complete (see Task.require_form_completion).

This was previously implemented directly in main.py at /api/forms/*,
which accidentally collided with routes/forms.py's customer-facing
GET /{form_id} wildcard route (registered earlier via include_router),
making it completely unreachable. Rebuilt here as its own router at a
non-colliding prefix.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timezone
import uuid

from database import get_db
from auth import get_current_user, require_role
from db_models import FormTemplateORM, FormSubmissionORM, User as UserORM, UserRole

router = APIRouter(prefix="/api/task-forms", tags=["task-forms"])


def _template_dict(t: FormTemplateORM) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "location_id": t.location_id,
        "fields": t.fields or [],
        "assignable_to": t.assignable_to,
        "require_signature": t.require_signature,
        "require_gps": t.require_gps,
        "allow_save_draft": t.allow_save_draft,
        "allow_edit_after_submit": t.allow_edit_after_submit,
        "is_active": t.is_active,
        "version": t.version,
        "category": t.category,
        "tags": t.tags or [],
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _submission_dict(s: FormSubmissionORM) -> dict:
    return {
        "id": s.id,
        "template_id": s.template_id,
        "staff_id": s.staff_id,
        "staff_name": s.staff_name,
        "values": s.values or {},
        "signature_data": s.signature_data,
        "status": s.status,
        "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        "related_type": s.related_type,
        "related_id": s.related_id,
        "reviewed_by": s.reviewed_by,
        "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
        "review_notes": s.review_notes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("/templates")
async def list_templates(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FormTemplateORM).where(FormTemplateORM.is_active == True).order_by(FormTemplateORM.created_at.desc())
    )
    return [_template_dict(t) for t in result.scalars().all()]


@router.post("/templates")
async def create_template(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    template = FormTemplateORM(
        id=str(uuid.uuid4()),
        name=name,
        description=data.get("description"),
        fields=data.get("fields", []),
        assignable_to=data.get("assignable_to", "all"),
        require_signature=bool(data.get("require_signature", False)),
        require_gps=bool(data.get("require_gps", False)),
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return _template_dict(template)


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    template = await db.get(FormTemplateORM, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_dict(template)


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    template = await db.get(FormTemplateORM, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    for field in ["name", "description", "fields", "assignable_to", "require_signature", "require_gps", "is_active"]:
        if field in data:
            setattr(template, field, data[field])
    await db.commit()
    await db.refresh(template)
    return _template_dict(template)


@router.get("/submissions")
async def list_submissions(
    related_type: Optional[str] = Query(None),
    related_id: Optional[str] = Query(None),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(FormSubmissionORM).order_by(FormSubmissionORM.created_at.desc())
    if current_user.role == UserRole.STAFF:
        stmt = stmt.where(FormSubmissionORM.staff_id == current_user.id)
    if related_type:
        stmt = stmt.where(FormSubmissionORM.related_type == related_type)
    if related_id:
        stmt = stmt.where(FormSubmissionORM.related_id == related_id)
    result = await db.execute(stmt)
    return [_submission_dict(s) for s in result.scalars().all()]


@router.post("/submissions")
async def submit_form(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    template_id = data.get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="template_id is required")
    template = await db.get(FormTemplateORM, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    submission = FormSubmissionORM(
        id=str(uuid.uuid4()),
        template_id=template_id,
        staff_id=current_user.id,
        staff_name=current_user.full_name,
        values=data.get("values", {}),
        signature_data=data.get("signature_data"),
        status="submitted",
        submitted_at=datetime.now(timezone.utc),
        related_type=data.get("related_type"),
        related_id=data.get("related_id"),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return _submission_dict(submission)


@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    submission = await db.get(FormSubmissionORM, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if current_user.role == UserRole.STAFF and submission.staff_id != current_user.id:
        raise HTTPException(status_code=404, detail="Submission not found")
    return _submission_dict(submission)
