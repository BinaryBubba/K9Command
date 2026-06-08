"""
Dogs API
Handles dog profile creation, retrieval, updates, and safety information.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from database import get_db
from auth import get_current_user, require_role
from db_models import (
    Dog as DogORM, Household, BehaviorProfile,
    VaccinationRecord, VaccinationStatus, MeetAndGreet,
    User as UserORM, UserRole
)
import uuid

router = APIRouter(prefix="/api/dogs", tags=["dogs"])


# ── List dogs ────────────────────────────────────────────────────────────────

@router.get("")
async def list_dogs(
    household_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="No organization assigned")

    q = select(DogORM).where(DogORM.organization_id == org_id)

    if active_only:
        q = q.where(DogORM.is_active == True)
    if household_id:
        q = q.where(DogORM.household_id == household_id)
    if search:
        q = q.where(DogORM.name.ilike(f"%{search}%"))

    q = q.order_by(DogORM.name).offset(skip).limit(limit)
    result = await db.execute(q)
    dogs = result.scalars().all()
    return [_dog_summary(d) for d in dogs]


# ── Get single dog ───────────────────────────────────────────────────────────

@router.get("/{dog_id}")
async def get_dog(
    dog_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    dog = await _get_dog_or_404(dog_id, current_user.organization_id, db)

    # Load behavior profile
    bp_result = await db.execute(
        select(BehaviorProfile).where(BehaviorProfile.dog_id == dog_id)
    )
    behavior = bp_result.scalar_one_or_none()

    # Load vaccination records
    vax_result = await db.execute(
        select(VaccinationRecord).where(VaccinationRecord.dog_id == dog_id)
        .order_by(VaccinationRecord.expiration_date.desc())
    )
    vaccinations = vax_result.scalars().all()

    # Load most recent meet and greet
    mag_result = await db.execute(
        select(MeetAndGreet).where(MeetAndGreet.dog_id == dog_id)
        .order_by(MeetAndGreet.created_at.desc()).limit(1)
    )
    latest_mag = mag_result.scalar_one_or_none()

    result = _dog_detail(dog)
    result["behavior_profile"] = _behavior_dict(behavior) if behavior else None
    result["vaccinations"] = [_vaccination_dict(v) for v in vaccinations]
    result["latest_meet_and_greet"] = _mag_dict(latest_mag) if latest_mag else None
    return result


# ── Create dog ───────────────────────────────────────────────────────────────

@router.post("")
async def create_dog(
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="No organization assigned")

    name = data.get("name", "").strip()
    household_id = data.get("household_id", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not household_id:
        raise HTTPException(status_code=400, detail="household_id is required")

    # Verify household belongs to this org
    hh = await db.execute(
        select(Household).where(
            Household.id == household_id,
            Household.organization_id == org_id
        )
    )
    if not hh.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Household not found")

    dog = DogORM(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        household_id=household_id,
        name=name,
        breed=data.get("breed", "Unknown"),
        age=data.get("age"),
        weight=data.get("weight"),
        gender=data.get("gender"),
        color=data.get("color"),
        spay_neuter_status=data.get("spay_neuter_status"),
        microchip_number=data.get("microchip_number"),
        veterinarian_id=data.get("veterinarian_id"),
        meal_routine=data.get("meal_routine"),
        medication_requirements=data.get("medication_requirements"),
        allergies=data.get("allergies"),
        behavioral_notes=data.get("behavioral_notes"),
        internal_notes=data.get("internal_notes"),
        meet_and_greet_status="required",
        boarding_eligible=False,
        daycare_eligible=False,
        escape_risk=data.get("escape_risk", False),
        medical_alert=data.get("medical_alert", False),
        is_deceased=False,
    )
    db.add(dog)
    await db.flush()

    # Create empty behavior profile
    behavior = BehaviorProfile(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        dog_id=dog.id,
        bite_history=data.get("bite_history", False),
        food_guarding=data.get("food_guarding", False),
        handlers_required=1,
    )
    db.add(behavior)

    await db.commit()
    await db.refresh(dog)
    return _dog_detail(dog)


# ── Update dog ───────────────────────────────────────────────────────────────

@router.patch("/{dog_id}")
async def update_dog(
    dog_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    dog = await _get_dog_or_404(dog_id, current_user.organization_id, db)

    allowed = [
        "name", "breed", "age", "weight", "gender", "color",
        "spay_neuter_status", "microchip_number", "veterinarian_id",
        "meal_routine", "medication_requirements", "allergies",
        "behavioral_notes", "internal_notes", "escape_risk",
        "medical_alert", "boarding_eligible", "daycare_eligible",
        "meet_and_greet_status", "is_active", "is_deceased",
    ]
    for field in allowed:
        if field in data:
            setattr(dog, field, data[field])

    await db.commit()
    await db.refresh(dog)
    return _dog_detail(dog)


# ── Update behavior profile ──────────────────────────────────────────────────

@router.patch("/{dog_id}/behavior")
async def update_behavior(
    dog_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    await _get_dog_or_404(dog_id, current_user.organization_id, db)

    bp_result = await db.execute(
        select(BehaviorProfile).where(BehaviorProfile.dog_id == dog_id)
    )
    bp = bp_result.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=404, detail="Behavior profile not found")

    allowed = [
        "handling_restrictions", "known_triggers", "dog_compatibility",
        "human_compatibility", "food_guarding", "toy_guarding",
        "barrier_reactivity", "leash_behavior", "escape_behavior",
        "bite_history", "bite_history_detail", "muzzle_required",
        "handlers_required", "approved_playgroups", "prohibited_pairings",
        "active_safety_alert", "safety_alert_detail",
    ]
    for field in allowed:
        if field in data:
            setattr(bp, field, data[field])

    bp.reviewed_by = current_user.id
    from datetime import datetime, timezone
    bp.last_reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(bp)
    return _behavior_dict(bp)


# ── Get safety summary (for check-in / dog card) ─────────────────────────────

@router.get("/{dog_id}/safety-summary")
async def get_safety_summary(
    dog_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    dog = await _get_dog_or_404(dog_id, current_user.organization_id, db)
    bp_result = await db.execute(
        select(BehaviorProfile).where(BehaviorProfile.dog_id == dog_id)
    )
    bp = bp_result.scalar_one_or_none()

    warnings = []
    if dog.escape_risk:
        warnings.append({"level": "warning", "type": "escape_risk", "message": "Escape risk — ensure secure handling"})
    if dog.medical_alert:
        warnings.append({"level": "warning", "type": "medical_alert", "message": "Medical alert — review care instructions"})
    if bp:
        if bp.bite_history:
            warnings.append({"level": "warning", "type": "bite_history", "message": "Bite history on record"})
        if bp.muzzle_required:
            warnings.append({"level": "warning", "type": "muzzle_required", "message": "Muzzle required"})
        if bp.active_safety_alert:
            warnings.append({"level": "critical", "type": "safety_alert", "message": bp.safety_alert_detail or "Active safety alert"})
        if bp.food_guarding:
            warnings.append({"level": "caution", "type": "food_guarding", "message": "Food guarding behavior"})
        if bp.handlers_required and bp.handlers_required > 1:
            warnings.append({"level": "caution", "type": "handlers", "message": f"Requires {bp.handlers_required} handlers"})

    return {
        "dog_id": dog_id,
        "dog_name": dog.name,
        "warnings": warnings,
        "has_critical": any(w["level"] == "critical" for w in warnings),
        "boarding_eligible": dog.boarding_eligible,
        "daycare_eligible": dog.daycare_eligible,
        "meet_and_greet_status": dog.meet_and_greet_status,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_dog_or_404(dog_id: str, org_id: str, db: AsyncSession) -> DogORM:
    result = await db.execute(
        select(DogORM).where(DogORM.id == dog_id, DogORM.organization_id == org_id)
    )
    dog = result.scalar_one_or_none()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    return dog

def _dog_summary(d: DogORM) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "breed": d.breed,
        "household_id": d.household_id,
        "age": d.age,
        "weight": d.weight,
        "gender": d.gender,
        "boarding_eligible": d.boarding_eligible,
        "daycare_eligible": d.daycare_eligible,
        "meet_and_greet_status": d.meet_and_greet_status,
        "escape_risk": d.escape_risk,
        "medical_alert": d.medical_alert,
    }

def _dog_detail(d: DogORM) -> dict:
    result = _dog_summary(d)
    result.update({
        "color": d.color,
        "spay_neuter_status": d.spay_neuter_status,
        "microchip_number": d.microchip_number,
        "veterinarian_id": d.veterinarian_id,
        "meal_routine": d.meal_routine,
        "medication_requirements": d.medication_requirements,
        "allergies": d.allergies,
        "behavioral_notes": d.behavioral_notes,
        "internal_notes": d.internal_notes,
        "is_deceased": getattr(d, "is_deceased", False),
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    })
    return result

def _behavior_dict(bp: BehaviorProfile) -> dict:
    return {
        "id": bp.id,
        "dog_id": bp.dog_id,
        "handling_restrictions": bp.handling_restrictions,
        "known_triggers": bp.known_triggers,
        "dog_compatibility": bp.dog_compatibility,
        "human_compatibility": bp.human_compatibility,
        "food_guarding": bp.food_guarding,
        "toy_guarding": bp.toy_guarding,
        "barrier_reactivity": bp.barrier_reactivity,
        "bite_history": bp.bite_history,
        "bite_history_detail": bp.bite_history_detail,
        "muzzle_required": bp.muzzle_required,
        "handlers_required": bp.handlers_required,
        "active_safety_alert": bp.active_safety_alert,
        "safety_alert_detail": bp.safety_alert_detail,
        "prohibited_pairings": bp.prohibited_pairings,
        "last_reviewed_at": bp.last_reviewed_at.isoformat() if bp.last_reviewed_at else None,
    }

def _vaccination_dict(v: VaccinationRecord) -> dict:
    return {
        "id": v.id,
        "vaccination_type": v.vaccination_type,
        "administration_date": v.administration_date.isoformat() if v.administration_date else None,
        "expiration_date": v.expiration_date.isoformat() if v.expiration_date else None,
        "verification_status": v.verification_status.value,
        "rejection_reason": v.rejection_reason,
        "document_path": v.document_path,
        "provider": v.provider,
    }

def _mag_dict(m: MeetAndGreet) -> dict:
    return {
        "id": m.id,
        "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
        "outcome": m.outcome.value if m.outcome else None,
        "conditions": m.conditions,
        "boarding_eligible_granted": m.boarding_eligible_granted,
        "daycare_eligible_granted": m.daycare_eligible_granted,
        "completed_at": m.completed_at.isoformat() if m.completed_at else None,
    }
