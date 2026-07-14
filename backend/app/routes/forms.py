"""
Forms API - form templates, submissions, and access control
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from auth import get_current_user, require_role
from db_models import User as UserORM, UserRole
import uuid, json

router = APIRouter(prefix="/api/forms", tags=["forms"])

# Default access by form type
DEFAULT_ACCESS = {
    "intake": ["customer", "staff", "manager", "admin"],
    "boarding_agreement": ["customer", "staff", "manager", "admin"],
    "checklist": ["staff", "manager", "admin"],
    "onboarding": ["staff", "manager", "admin"],
    "vaccination": ["customer", "staff", "manager", "admin"],
    "custom": ["admin"],
}


def _form_dict(row) -> dict:
    fields = row.fields
    if isinstance(fields, str):
        try: fields = json.loads(fields)
        except: fields = []
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "form_type": row.form_type,
        "access_level": row.access_level,
        "fields": fields,
        "is_active": row.is_active,
        "version": row.version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("")
async def list_forms(
    form_type: Optional[str] = Query(None),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List forms accessible to the current user."""
    role = str(current_user.role).lower().replace("userrole.", "")

    # Build allowed types based on role
    role_types = {
        "admin": ["intake","boarding_agreement","checklist","onboarding","vaccination","custom"],
        "manager": ["intake","boarding_agreement","checklist","onboarding","vaccination","custom"],
        "staff": ["intake","boarding_agreement","checklist","onboarding","vaccination"],
    }
    allowed_types = role_types.get(role, ["intake","boarding_agreement","vaccination"])

    # Use IN with explicit placeholders
    type_placeholders = ', '.join([f':t{i}' for i in range(len(allowed_types))])
    type_params = {f't{i}': t for i, t in enumerate(allowed_types)}
    params = {"org_id": current_user.organization_id, "user_id": current_user.id}
    params.update(type_params)

    result = await db.execute(text(f"""
        SELECT f.id, f.title, f.description, f.form_type, f.access_level,
               f.fields, f.is_active, f.version, f.created_at
        FROM forms f
        WHERE f.organization_id = :org_id
        AND f.is_active = TRUE
        AND (
            f.form_type IN ({type_placeholders})
            OR EXISTS (
                SELECT 1 FROM form_access fa
                WHERE fa.form_id = f.id AND fa.user_id = :user_id AND fa.access_type = 'granted'
            )
        )
        AND NOT EXISTS (
            SELECT 1 FROM form_access fa
            WHERE fa.form_id = f.id AND fa.user_id = :user_id AND fa.access_type = 'revoked'
        )
        ORDER BY f.form_type, f.title
    """), params)

    rows = result.fetchall()
    forms = [_form_dict(r) for r in rows]

    if form_type:
        forms = [f for f in forms if f["form_type"] == form_type]

    return forms


@router.get("/{form_id}")
async def get_form(
    form_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT id, title, description, form_type, access_level, fields, is_active, version, created_at
        FROM forms WHERE id = :id AND organization_id = :org_id
    """), {"id": form_id, "org_id": current_user.organization_id})
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Form not found")

    role = str(current_user.role).lower().replace("userrole.", "")
    role_types = {
        "admin": ["intake","boarding_agreement","checklist","onboarding","vaccination","custom"],
        "manager": ["intake","boarding_agreement","checklist","onboarding","vaccination","custom"],
        "staff": ["intake","boarding_agreement","checklist","onboarding","vaccination"],
    }
    allowed_types = role_types.get(role, ["intake","boarding_agreement","vaccination"])

    if row.form_type not in allowed_types:
        access_result = await db.execute(text("""
            SELECT access_type FROM form_access
            WHERE form_id = :form_id AND user_id = :user_id
            ORDER BY access_type DESC LIMIT 1
        """), {"form_id": form_id, "user_id": current_user.id})
        access_row = access_result.fetchone()
        if not access_row or access_row.access_type != "granted":
            raise HTTPException(status_code=404, detail="Form not found")

    return _form_dict(row)


@router.post("")
async def create_form(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    form_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO forms (id, organization_id, title, description, form_type, access_level, fields, created_by)
        VALUES (:id, :org_id, :title, :description, :form_type, :access_level, :fields, :created_by)
    """), {
        "id": form_id,
        "org_id": current_user.organization_id,
        "title": data.get("title", ""),
        "description": data.get("description"),
        "form_type": data.get("form_type", "custom"),
        "access_level": data.get("access_level", "staff"),
        "fields": json.dumps(data.get("fields", [])),
        "created_by": current_user.id,
    })
    await db.commit()
    return {"id": form_id, "created": True}


@router.patch("/{form_id}")
async def update_form(
    form_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    updates = []
    params = {"id": form_id, "org_id": current_user.organization_id}
    for field in ["title", "description", "fields", "access_level", "is_active"]:
        if field in data:
            updates.append(f"{field} = :{field}")
            params[field] = json.dumps(data[field]) if field == "fields" else data[field]
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    updates.append("updated_at = NOW()")
    await db.execute(text(f"""
        UPDATE forms SET {', '.join(updates)}
        WHERE id = :id AND organization_id = :org_id
    """), params)
    await db.commit()
    return {"updated": True}


@router.post("/{form_id}/access")
async def set_form_access(
    form_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Grant or revoke form access for a specific user."""
    user_id = data.get("user_id")
    access_type = data.get("access_type", "granted")  # granted or revoked
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    await db.execute(text("""
        INSERT INTO form_access (id, organization_id, form_id, user_id, access_type, granted_by)
        VALUES (:id, :org_id, :form_id, :user_id, :access_type, :granted_by)
        ON CONFLICT (form_id, user_id) DO UPDATE SET access_type = :access_type
    """), {
        "id": str(uuid.uuid4()),
        "org_id": current_user.organization_id,
        "form_id": form_id,
        "user_id": user_id,
        "access_type": access_type,
        "granted_by": current_user.id,
    })
    await db.commit()
    return {"set": True, "access_type": access_type}


@router.get("/{form_id}/submissions")
async def list_submissions(
    form_id: str,
    household_id: Optional[str] = Query(None),
    dog_id: Optional[str] = Query(None),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Reads from customer_form_submissions -- a dedicated table for
    customer-facing form submissions (intake, boarding agreements, etc).
    Not to be confused with form_submissions/form_templates, which is a
    separate, unrelated staff field-report subsystem."""
    conditions = ["fs.organization_id = :org_id", "fs.form_id = :form_id"]
    params = {"org_id": current_user.organization_id, "form_id": form_id}
    if household_id:
        conditions.append("fs.household_id = :household_id")
        params["household_id"] = household_id
    if dog_id:
        conditions.append("fs.dog_id = :dog_id")
        params["dog_id"] = dog_id

    where = " AND ".join(conditions)
    result = await db.execute(text(f"""
        SELECT fs.id, fs.form_id, fs.submitted_by, fs.dog_id, fs.household_id,
               fs.data, fs.signed_name, fs.signed_at, fs.created_at,
               u.full_name as submitted_by_name
        FROM customer_form_submissions fs
        LEFT JOIN users u ON fs.submitted_by = u.id
        WHERE {where}
        ORDER BY fs.created_at DESC
    """), params)
    rows = result.fetchall()
    return [{
        "id": r.id,
        "form_id": r.form_id,
        "submitted_by_name": r.submitted_by_name,
        "dog_id": r.dog_id,
        "household_id": r.household_id,
        "data": r.data,
        "signed_name": r.signed_name,
        "signed_at": r.signed_at.isoformat() if r.signed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]


@router.post("/{form_id}/submit")
async def submit_form(
    form_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Writes to customer_form_submissions -- see list_submissions docstring."""
    submission_id = str(uuid.uuid4())
    signed_name = data.get("signed_name")
    signed_at = datetime.now(timezone.utc) if signed_name else None

    await db.execute(text("""
        INSERT INTO customer_form_submissions
            (id, organization_id, form_id, submitted_by, dog_id, household_id, stay_id, task_id, data, signed_name, signed_at)
        VALUES
            (:id, :org_id, :form_id, :submitted_by, :dog_id, :household_id, :stay_id, :task_id, :data, :signed_name, :signed_at)
    """), {
        "id": submission_id,
        "org_id": current_user.organization_id,
        "form_id": form_id,
        "submitted_by": current_user.id,
        "dog_id": data.get("dog_id"),
        "household_id": data.get("household_id"),
        "stay_id": data.get("stay_id"),
        "task_id": data.get("task_id"),
        "data": json.dumps(data.get("responses", {})),
        "signed_name": signed_name,
        "signed_at": signed_at,
    })
    await db.commit()
    return {"submission_id": submission_id, "submitted": True}
