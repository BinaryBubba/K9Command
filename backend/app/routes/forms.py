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
from db_models import User as UserORM, UserRole, Dog as DogORM
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


@router.get("/my-submissions")
async def my_submissions(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The signed-in customer's own form submissions (for the completed indicator)."""
    if not current_user.household_id:
        return []
    rows = (await db.execute(text("""
        SELECT fs.id, fs.form_id, fs.dog_id, fs.signed_at, fs.created_at, fs.form_version, d.name AS dog_name
        FROM customer_form_submissions fs
        LEFT JOIN dogs d ON d.id = fs.dog_id
        WHERE fs.organization_id = :o AND fs.household_id = :h
        ORDER BY fs.created_at DESC
    """), {"o": current_user.organization_id, "h": current_user.household_id})).fetchall()
    return [{
        "id": r.id, "form_id": r.form_id, "dog_id": r.dog_id, "dog_name": r.dog_name,
        "form_version": r.form_version,
        "signed_at": r.signed_at.isoformat() if r.signed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]


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
               fs.signed_ip, fs.form_version, fs.content_hash, fs.consent_text,
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
        "signed_ip": r.signed_ip,
        "form_version": r.form_version,
        "content_hash": r.content_hash,
        "consent_text": r.consent_text,
    } for r in rows]


import hashlib as _hashlib
from fastapi import Request as _Request

CONSENT_TEXT = ("I have read and agree to the terms above. I understand that typing my full name and "
                "checking this box is my legal electronic signature, with the same effect as a handwritten signature.")


@router.post("/{form_id}/submit")
async def submit_form(
    form_id: str,
    data: dict,
    request: _Request,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Writes to customer_form_submissions -- see list_submissions docstring."""
    if str(current_user.role).lower().replace("userrole.", "") == "customer":
        # Customers can only submit for their own household and their own dogs.
        data = dict(data)
        data["household_id"] = current_user.household_id
        if data.get("dog_id"):
            _own = (await db.execute(
                select(DogORM.id).where(
                    DogORM.id == data["dog_id"],
                    DogORM.organization_id == current_user.organization_id,
                    DogORM.household_id == current_user.household_id,
                )
            )).scalar_one_or_none()
            if not _own:
                raise HTTPException(status_code=404, detail="Dog not found")
    _form_row = (await db.execute(text("SELECT title, fields, version FROM forms WHERE id = :fid"), {"fid": form_id})).first()
    if not _form_row:
        raise HTTPException(status_code=404, detail="Form not found")
    submission_id = str(uuid.uuid4())
    signed_name = (data.get("signed_name") or "").strip() or None
    signed_at = datetime.now(timezone.utc) if signed_name else None
    _fields = _form_row.fields
    if isinstance(_fields, str):
        _fields = json.loads(_fields)
    _responses = data.get("responses", {})
    _ip = (request.headers.get("cf-connecting-ip")
           or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
           or (request.client.host if request.client else None)) or None
    _ua = (request.headers.get("user-agent") or "")[:500] or None
    _consent_text = CONSENT_TEXT if (signed_name and data.get("consent") is True) else None
    _snapshot = {"title": _form_row.title, "version": _form_row.version, "fields": _fields}
    _hash = None
    if signed_name:
        _hash = _hashlib.sha256(json.dumps({
            "submission_id": submission_id, "form_id": form_id, "form_version": _form_row.version,
            "fields": _fields, "responses": _responses, "signed_name": signed_name,
            "signed_at": signed_at.isoformat(), "submitted_by": current_user.id,
            "consent_text": _consent_text, "ip": _ip,
        }, sort_keys=True, default=str).encode()).hexdigest()

    await db.execute(text("""
        INSERT INTO customer_form_submissions
            (id, organization_id, form_id, submitted_by, dog_id, household_id, stay_id, task_id, data, signed_name, signed_at,
             signed_ip, signed_user_agent, form_version, form_snapshot, consent_text, content_hash)
        VALUES
            (:id, :org_id, :form_id, :submitted_by, :dog_id, :household_id, :stay_id, :task_id, :data, :signed_name, :signed_at,
             :signed_ip, :signed_ua, :form_version, :form_snapshot, :consent_text, :content_hash)
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
        "signed_ip": _ip,
        "signed_ua": _ua,
        "form_version": _form_row.version,
        "form_snapshot": json.dumps(_snapshot, default=str),
        "consent_text": _consent_text,
        "content_hash": _hash,
    })
    await db.commit()

    # If this was the dog intake questionnaire, apply the answers directly
    # to the dog's profile so staff don't have to re-enter everything by hand.
    if form_id == "form-intake-001" and data.get("dog_id"):
        try:
            dog = (await db.execute(
                select(DogORM).where(DogORM.id == data["dog_id"], DogORM.organization_id == current_user.organization_id)
            )).scalar_one_or_none()
            if dog:
                _apply_intake_responses_to_dog(dog, data.get("responses", {}))
                await db.commit()
        except Exception as e:
            print(f"Failed to apply intake responses to dog profile: {e}")

    return {"submission_id": submission_id, "submitted": True}


def _apply_intake_responses_to_dog(dog: DogORM, responses: dict):
    def yn_to_bool(val):
        if val == "Yes":
            return True
        if val == "No":
            return False
        return None

    text_fields = [
        "breed", "color", "meal_routine", "medication_requirements",
        "allergies", "incidents_of_aggression", "other_notes", "gender",
        "spay_neuter_status",
    ]
    for field in text_fields:
        if responses.get(field):
            setattr(dog, field, responses[field])

    if responses.get("dog_name"):
        dog.name = responses["dog_name"]

    if responses.get("weight") not in (None, ""):
        try:
            dog.weight = float(responses["weight"])
        except (TypeError, ValueError):
            pass

    yes_no_fields = [
        "friendly_with_dogs", "friendly_with_people", "friendly_to_cats",
        "seizure_activity", "afraid_of_thunder", "afraid_of_fireworks",
        "fence_aggression", "resource_guarding", "climbing_habits",
        "digging_habits", "prey_drive", "no_small_dogs", "no_large_dogs",
    ]
    for field in yes_no_fields:
        if field in responses:
            setattr(dog, field, yn_to_bool(responses.get(field)))

    if responses.get("crate_trained"):
        val = responses["crate_trained"]
        dog.crate_trained = "unable" if val == "Unable to be Crated" else val.lower()

    if responses.get("birthday"):
        try:
            from dateutil import parser as _dateparser
            dog.birthday = _dateparser.parse(responses["birthday"])
        except Exception:
            pass

    dog.intake_completed_at = datetime.now(timezone.utc)
