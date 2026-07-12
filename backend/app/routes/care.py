"""
Care Operations API
Handles feeding events, medications, and shift handoffs.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from auth import get_current_user, require_role
from db_models import (
    FeedingPlan, FeedingEvent, AppetiteRating,
    Medication, MedicationAdministration, MedicationStatus,
    ShiftHandoff, Stay, StayStatus, StayAlert,
    Dog as DogORM, User as UserORM, UserRole,
    Booking
)
import uuid

router = APIRouter(prefix="/api/care", tags=["care"])

def _parse_date(value):
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _plan_dict(p) -> dict:
    return {
        "id": p.id, "dog_id": p.dog_id, "food_name": p.food_name,
        "amount": p.amount, "frequency": p.frequency,
        "scheduled_times": p.scheduled_times or [],
        "preparation_instructions": p.preparation_instructions,
        "supplements": p.supplements,
        "food_supplied_by_owner": p.food_supplied_by_owner,
        "is_active": p.is_active, "notes": p.notes,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _feeding_event_dict(e) -> dict:
    return {
        "id": e.id, "stay_id": e.stay_id, "dog_id": e.dog_id,
        "scheduled_time": e.scheduled_time.isoformat() if e.scheduled_time else None,
        "completed_time": e.completed_time.isoformat() if e.completed_time else None,
        "completed_by": e.completed_by,
        "amount_offered": e.amount_offered, "amount_eaten": e.amount_eaten,
        "appetite_rating": e.appetite_rating.value if e.appetite_rating else None,
        "refusal_reason": e.refusal_reason, "notes": e.notes,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _medication_dict(m) -> dict:
    return {
        "id": m.id, "dog_id": m.dog_id, "name": m.name, "dose": m.dose,
        "route": m.route, "frequency": m.frequency,
        "scheduled_times": m.scheduled_times or [],
        "start_date": m.start_date.isoformat() if m.start_date else None,
        "end_date": m.end_date.isoformat() if m.end_date else None,
        "as_needed": m.as_needed,
        "storage_instructions": m.storage_instructions,
        "administration_instructions": m.administration_instructions,
        "prescriber": m.prescriber, "is_active": m.is_active, "notes": m.notes,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


def _admin_dict(a) -> dict:
    return {
        "id": a.id, "stay_id": a.stay_id, "dog_id": a.dog_id,
        "medication_id": a.medication_id,
        "scheduled_time": a.scheduled_time.isoformat() if a.scheduled_time else None,
        "administered_time": a.administered_time.isoformat() if a.administered_time else None,
        "administered_by": a.administered_by,
        "status": a.status.value if a.status else None,
        "dose_administered": a.dose_administered,
        "exception_reason": a.exception_reason, "notes": a.notes,
        "reviewed_by": a.reviewed_by,
        "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


# ══════════════════════════════════════════════════════════════
# FEEDING PLANS
# ══════════════════════════════════════════════════════════════

@router.get("/feeding-plans/dog/{dog_id}")
async def get_feeding_plans(
    dog_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FeedingPlan).where(
            FeedingPlan.dog_id == dog_id,
            FeedingPlan.organization_id == current_user.organization_id,
            FeedingPlan.is_active == True,
        )
    )
    return [_plan_dict(p) for p in result.scalars().all()]


@router.post("/feeding-plans/dog/{dog_id}")
async def create_feeding_plan(
    dog_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    plan = FeedingPlan(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        dog_id=dog_id,
        food_name=data.get("food_name", "").strip(),
        amount=data.get("amount", "").strip(),
        frequency=data.get("frequency", "").strip(),
        scheduled_times=data.get("scheduled_times", []),
        preparation_instructions=data.get("preparation_instructions"),
        supplements=data.get("supplements"),
        food_supplied_by_owner=data.get("food_supplied_by_owner", False),
        notes=data.get("notes"),
    )
    if not plan.food_name or not plan.amount or not plan.frequency:
        raise HTTPException(status_code=400, detail="food_name, amount, and frequency are required")
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return _plan_dict(plan)


# ══════════════════════════════════════════════════════════════
# FEEDING EVENTS
# ══════════════════════════════════════════════════════════════

@router.get("/feeding-events/stay/{stay_id}")
async def get_stay_feeding_events(
    stay_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FeedingEvent).where(
            FeedingEvent.stay_id == stay_id,
            FeedingEvent.organization_id == current_user.organization_id,
        ).order_by(FeedingEvent.created_at.desc())
    )
    return [_feeding_event_dict(e) for e in result.scalars().all()]


@router.post("/feeding-events/stay/{stay_id}")
async def log_feeding(
    stay_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    # Verify stay belongs to org
    stay = (await db.execute(
        select(Stay).where(
            Stay.id == stay_id,
            Stay.organization_id == current_user.organization_id
        )
    )).scalar_one_or_none()
    if not stay:
        raise HTTPException(status_code=404, detail="Stay not found")

    appetite_str = data.get("appetite_rating", "").upper()
    appetite = None
    if appetite_str:
        try:
            appetite = AppetiteRating[appetite_str]
        except KeyError:
            pass

    event = FeedingEvent(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        stay_id=stay_id,
        dog_id=stay.dog_id,
        scheduled_time=_parse_date(data.get("scheduled_time")),
        completed_time=datetime.now(timezone.utc),
        completed_by=current_user.id,
        amount_offered=data.get("amount_offered"),
        amount_eaten=data.get("amount_eaten"),
        appetite_rating=appetite,
        refusal_reason=data.get("refusal_reason"),
        notes=data.get("notes"),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return _feeding_event_dict(event)


# ══════════════════════════════════════════════════════════════
# MEDICATIONS
# ══════════════════════════════════════════════════════════════

@router.get("/medications")
async def get_all_active_medications(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Get all active medications for dogs currently on site."""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT m.id, m.dog_id, m.name, m.dose, m.frequency, m.administration_instructions as instructions,
               d.name as dog_name
        FROM medications m
        JOIN dogs d ON m.dog_id = d.id
        JOIN stays s ON s.dog_id = d.id
        WHERE s.organization_id = :org_id
        AND LOWER(s.status::text) IN ('on_site','checked_in')
        AND m.is_active = TRUE
        ORDER BY d.name
    """), {"org_id": current_user.organization_id})
    rows = result.fetchall()
    return [{"id": r.id, "dog_id": r.dog_id, "name": r.name, "dosage": r.dose,
             "frequency": r.frequency, "instructions": r.instructions, "dosage": r.dose,
             "dog_name": r.dog_name} for r in rows]


@router.get("/medications/dog/{dog_id}")
async def get_dog_medications(
    dog_id: str,
    active_only: bool = Query(True),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    q = select(Medication).where(
        Medication.dog_id == dog_id,
        Medication.organization_id == current_user.organization_id,
    )
    if active_only:
        q = q.where(Medication.is_active == True)
    result = await db.execute(q)
    return [_medication_dict(m) for m in result.scalars().all()]


@router.post("/medications/dog/{dog_id}")
async def add_medication(
    dog_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    name = data.get("name", "").strip()
    dose = data.get("dose", "").strip()
    frequency = data.get("frequency", "").strip()
    if not name or not dose or not frequency:
        raise HTTPException(status_code=400, detail="name, dose, and frequency are required")

    med = Medication(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        dog_id=dog_id,
        name=name,
        dose=dose,
        route=data.get("route"),
        frequency=frequency,
        scheduled_times=data.get("scheduled_times", []),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        as_needed=data.get("as_needed", False),
        storage_instructions=data.get("storage_instructions"),
        administration_instructions=data.get("administration_instructions"),
        prescriber=data.get("prescriber"),
        notes=data.get("notes"),
    )
    db.add(med)
    await db.commit()
    await db.refresh(med)
    return _medication_dict(med)


@router.get("/medication-administrations/stay/{stay_id}")
async def get_stay_administrations(
    stay_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MedicationAdministration).where(
            MedicationAdministration.stay_id == stay_id,
            MedicationAdministration.organization_id == current_user.organization_id,
        ).order_by(MedicationAdministration.scheduled_time)
    )
    return [_admin_dict(a) for a in result.scalars().all()]


@router.post("/medication-administrations/stay/{stay_id}")
async def log_administration(
    stay_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    stay = (await db.execute(
        select(Stay).where(
            Stay.id == stay_id,
            Stay.organization_id == current_user.organization_id
        )
    )).scalar_one_or_none()
    if not stay:
        raise HTTPException(status_code=404, detail="Stay not found")

    medication_id = data.get("medication_id", "").strip()
    if not medication_id:
        raise HTTPException(status_code=400, detail="medication_id is required")

    status_str = data.get("status", "administered").upper()
    try:
        status = MedicationStatus[status_str]
    except KeyError:
        status = MedicationStatus.ADMINISTERED

    # Require exception reason for non-administered outcomes
    if status != MedicationStatus.ADMINISTERED and not data.get("exception_reason"):
        raise HTTPException(
            status_code=400,
            detail="exception_reason is required for non-administered outcomes"
        )

    admin = MedicationAdministration(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        stay_id=stay_id,
        dog_id=stay.dog_id,
        medication_id=medication_id,
        scheduled_time=_parse_date(data.get("scheduled_time")),
        administered_time=datetime.now(timezone.utc) if status == MedicationStatus.ADMINISTERED else None,
        administered_by=current_user.id,
        status=status,
        dose_administered=data.get("dose_administered"),
        exception_reason=data.get("exception_reason"),
        notes=data.get("notes"),
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return _admin_dict(admin)


@router.post("/medication-administrations/{admin_id}/review")
async def review_administration(
    admin_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Owner reviews missed/refused medication administrations."""
    result = await db.execute(
        select(MedicationAdministration).where(
            MedicationAdministration.id == admin_id,
            MedicationAdministration.organization_id == current_user.organization_id,
        )
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Administration record not found")

    admin.reviewed_by = current_user.id
    admin.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(admin)
    return _admin_dict(admin)


# ══════════════════════════════════════════════════════════════
# SHIFT HANDOFFS
# ══════════════════════════════════════════════════════════════

@router.get("/handoffs")
async def list_handoffs(
    limit: int = Query(10),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT h.id, h.staff_id, h.shift_start, h.shift_end, h.staff_notes,
               h.follow_up_items, h.outstanding_care, h.active_medications,
               h.active_alerts, h.open_incidents, h.dogs_on_site_snapshot,
               h.submitted_at, h.acknowledged_by, h.acknowledged_at, h.created_at,
               u.full_name as staff_name,
               ab.full_name as acknowledged_by_name
        FROM shift_handoffs h
        JOIN users u ON h.staff_id = u.id
        LEFT JOIN users ab ON h.acknowledged_by = ab.id
        WHERE h.organization_id = :org_id
        ORDER BY h.created_at DESC
        LIMIT :limit
    """), {"org_id": current_user.organization_id, "limit": limit})
    rows = result.fetchall()
    import json as _json
    def safe_json(v):
        if v is None: return []
        if isinstance(v, str):
            try: return _json.loads(v)
            except: return []
        return v
    return [{
        "id": r.id,
        "staff_id": r.staff_id,
        "staff_name": r.staff_name,
        "shift_start": r.shift_start.isoformat() if r.shift_start else None,
        "shift_end": r.shift_end.isoformat() if r.shift_end else None,
        "staff_notes": r.staff_notes,
        "follow_up_items": safe_json(r.follow_up_items),
        "outstanding_care": safe_json(r.outstanding_care),
        "active_medications": safe_json(r.active_medications),
        "active_alerts": safe_json(r.active_alerts),
        "open_incidents": safe_json(r.open_incidents),
        "dogs_on_site_snapshot": safe_json(r.dogs_on_site_snapshot),
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        "acknowledged_by_name": r.acknowledged_by_name,
        "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]


@router.post("/handoffs")
async def create_handoff(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    import uuid, json as _json
    from datetime import datetime, timezone

    # Auto-populate dogs on site
    dogs_result = await db.execute(text("""
        SELECT d.name, d.breed, r.name as room_name
        FROM stays s JOIN dogs d ON s.dog_id = d.id
        LEFT JOIN rooms r ON s.room_id = r.id
        WHERE s.organization_id = :org_id
        AND s.status::text IN ('CHECKED_IN','ON_SITE','on_site','checked_in')
    """), {"org_id": current_user.organization_id})
    dogs_snapshot = [{"name": r.name, "breed": r.breed, "room": r.room_name} for r in dogs_result.fetchall()]

    # Auto-populate active medications
    meds_result = await db.execute(text("""
        SELECT d.name as dog_name, m.name as med_name, m.dosage, m.frequency
        FROM medications m JOIN dogs d ON m.dog_id = d.id
        JOIN stays s ON s.dog_id = d.id
        WHERE s.organization_id = :org_id
        AND s.status::text IN ('CHECKED_IN','ON_SITE','on_site','checked_in')
        AND m.is_active = TRUE
    """), {"org_id": current_user.organization_id})
    meds = [{"dog": r.dog_name, "medication": r.med_name, "dosage": r.dosage, "frequency": r.frequency} for r in meds_result.fetchall()]

    # Auto-populate open incidents
    inc_result = await db.execute(text("""
        SELECT title, severity::text as severity
        FROM incidents
        WHERE organization_id = :org_id
        AND status::text NOT IN ('CLOSED','RESOLVED')
    """), {"org_id": current_user.organization_id})
    incidents = [{"title": r.title, "severity": r.severity} for r in inc_result.fetchall()]

    # Auto-populate active alerts
    alerts_result = await db.execute(text("""
        SELECT d.name as dog_name, sa.alert_message
        FROM stay_alerts sa JOIN stays s ON sa.stay_id = s.id
        JOIN dogs d ON s.dog_id = d.id
        WHERE s.organization_id = :org_id
        AND sa.cleared_at IS NULL
        AND s.status::text IN ('CHECKED_IN','ON_SITE','on_site','checked_in')
    """), {"org_id": current_user.organization_id})
    alerts = [{"dog": r.dog_name, "alert": r.alert_message} for r in alerts_result.fetchall()]

    # Lunch feeding reminder - dogs on site at midday
    lunch_reminder = []
    for dog in dogs_snapshot:
        lunch_reminder.append({"dog": dog["name"], "note": "Check lunch feeding schedule"})

    handoff_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO shift_handoffs (
            id, organization_id, staff_id, shift_start, shift_end,
            dogs_on_site_snapshot, active_medications, active_alerts,
            open_incidents, outstanding_care, follow_up_items, staff_notes, submitted_at
        ) VALUES (
            :id, :org_id, :staff_id, :shift_start, NOW(),
            :dogs, :meds, :alerts, :incidents, :care, :followup, :notes, NOW()
        )
    """), {
        "id": handoff_id,
        "org_id": current_user.organization_id,
        "staff_id": current_user.id,
        "shift_start": data.get("shift_start"),
        "dogs": _json.dumps(dogs_snapshot),
        "meds": _json.dumps(meds),
        "alerts": _json.dumps(alerts),
        "incidents": _json.dumps(incidents),
        "care": _json.dumps(lunch_reminder),
        "followup": _json.dumps(data.get("follow_up_items", [])),
        "notes": data.get("staff_notes", ""),
    })

    # Clock out the user
    await db.execute(text("""
        UPDATE users SET is_on_shift = FALSE, shift_started_at = NULL WHERE id = :user_id
    """), {"user_id": current_user.id})

    await db.commit()
    return {"handoff_id": handoff_id, "clocked_out": True}


@router.post("/handoffs/{handoff_id}/acknowledge")
async def acknowledge_handoff(
    handoff_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    await db.execute(text("""
        UPDATE shift_handoffs SET acknowledged_by = :user_id, acknowledged_at = NOW()
        WHERE id = :id AND organization_id = :org_id
    """), {"user_id": current_user.id, "id": handoff_id, "org_id": current_user.organization_id})
    await db.commit()
    return {"acknowledged": True}
