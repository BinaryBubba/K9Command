"""
Stays API
Handles check-in, check-out, stay alerts, feeding overrides, and room assignments.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from auth import get_current_user, require_role
from db_models import (
    Stay, StayStatus, StayAlert, StayAlertSeverity,
    StayFeedingOverride, CheckoutPickupRecord, RoomAssignment,
    Booking, BookingDog, BookingStatus, Dog as DogORM,
    Room, BehaviorProfile, User as UserORM, UserRole,
    VaccinationRecord, VaccinationStatus
)
import uuid

router = APIRouter(prefix="/api/stays", tags=["stays"])


# ── Get current on-site dogs (occupancy board) ───────────────────────────────

@router.get("/on-site")
async def get_on_site(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    result = await db.execute(
        select(Stay).where(
            Stay.organization_id == org_id,
            Stay.status == StayStatus.ON_SITE,
        ).order_by(Stay.checked_in_at)
    )
    stays = result.scalars().all()
    out = []
    for stay in stays:
        dog = await _get_dog(stay.dog_id, db)
        alerts = await _get_active_alerts(stay.id, db)
        room = None
        if stay.room_id:
            room_res = await db.execute(select(Room).where(Room.id == stay.room_id))
            room = room_res.scalar_one_or_none()
        out.append({
            **_stay_dict(stay),
            "dog_name": dog.name if dog else None,
            "dog_breed": dog.breed if dog else None,
            "room_name": room.name if room else None,
            "active_alerts": [_alert_dict(a) for a in alerts],
            "alert_count": len(alerts),
            "has_warning": any(a.severity == StayAlertSeverity.WARNING for a in alerts),
        })
    return out


# ── Get today's arrivals ──────────────────────────────────────────────────────

@router.get("/arrivals/today")
async def get_todays_arrivals(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(Booking).where(
            Booking.organization_id == org_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]),
            Booking.check_in_date >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc),
            Booking.check_in_date < datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc),
        ).order_by(Booking.check_in_date)
    )
    bookings = result.scalars().all()

    out = []
    for b in bookings:
        bd_result = await db.execute(
            select(BookingDog).where(BookingDog.booking_id == b.id)
        )
        booking_dogs = bd_result.scalars().all()
        for bd in booking_dogs:
            dog = await _get_dog(bd.dog_id, db)
            existing_stay = (await db.execute(
                select(Stay).where(
                    Stay.booking_id == b.id,
                    Stay.dog_id == bd.dog_id,
                )
            )).scalar_one_or_none()

            out.append({
                "booking_id": b.id,
                "dog_id": bd.dog_id,
                "dog_name": dog.name if dog else None,
                "check_in_date": b.check_in_date.isoformat(),
                "check_out_date": b.check_out_date.isoformat(),
                "already_checked_in": existing_stay is not None and existing_stay.status == StayStatus.ON_SITE,
                "is_first_stay": await _is_first_stay(bd.dog_id, org_id, db),
            })
    return out


# ── Get today's departures ────────────────────────────────────────────────────

@router.get("/departures/today")
async def get_todays_departures(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(Stay).where(
            Stay.organization_id == org_id,
            Stay.status == StayStatus.ON_SITE,
        )
    )
    stays = result.scalars().all()

    departures = []
    for stay in stays:
        booking = (await db.execute(
            select(Booking).where(Booking.id == stay.booking_id)
        )).scalar_one_or_none()
        if not booking:
            continue
        checkout_date = booking.check_out_date.date()
        if checkout_date == today:
            dog = await _get_dog(stay.dog_id, db)
            alerts = await _get_active_alerts(stay.id, db)
            departures.append({
                **_stay_dict(stay),
                "dog_name": dog.name if dog else None,
                "check_out_date": booking.check_out_date.isoformat(),
                "active_alerts": [_alert_dict(a) for a in alerts],
            })
    return departures


# ── Check in ─────────────────────────────────────────────────────────────────

@router.post("/check-in")
async def check_in(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    booking_id = data.get("booking_id", "").strip()
    dog_id = data.get("dog_id", "").strip()

    if not booking_id or not dog_id:
        raise HTTPException(status_code=400, detail="booking_id and dog_id are required")

    booking = (await db.execute(
        select(Booking).where(Booking.id == booking_id, Booking.organization_id == org_id)
    )).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Check if already checked in
    existing = (await db.execute(
        select(Stay).where(Stay.booking_id == booking_id, Stay.dog_id == dog_id)
    )).scalar_one_or_none()
    if existing and existing.status == StayStatus.ON_SITE:
        raise HTTPException(status_code=400, detail="Dog is already checked in")

    is_first = await _is_first_stay(dog_id, org_id, db)

    stay = Stay(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        booking_id=booking_id,
        dog_id=dog_id,
        status=StayStatus.ON_SITE,
        room_id=data.get("room_id"),
        checked_in_at=datetime.now(timezone.utc),
        checked_in_by=current_user.id,
        is_first_stay=is_first,
        intake_condition_note=data.get("intake_condition_note"),
        belongings_note=data.get("belongings_note"),
    )
    db.add(stay)
    await db.flush()

    # Create room assignment if room provided
    if data.get("room_id"):
        assignment = RoomAssignment(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            stay_id=stay.id,
            room_id=data["room_id"],
            assigned_by=current_user.id,
        )
        db.add(assignment)

    # Create feeding override if provided
    if data.get("feeding_override"):
        fo = data["feeding_override"]
        override = StayFeedingOverride(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            stay_id=stay.id,
            dog_id=dog_id,
            override_type=fo.get("type", "instructions"),
            override_detail=fo.get("detail", ""),
            reason=fo.get("reason"),
            created_by=current_user.id,
        )
        db.add(override)

    # Update booking status
    booking.status = BookingStatus.CHECKED_IN
    booking.checked_in_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(stay)

    dog = await _get_dog(dog_id, db)
    vax_warnings = await _get_vax_warnings(dog_id, org_id, db)
    behavior = (await db.execute(
        select(BehaviorProfile).where(BehaviorProfile.dog_id == dog_id)
    )).scalar_one_or_none()

    return {
        **_stay_dict(stay),
        "dog_name": dog.name if dog else None,
        "is_first_stay": is_first,
        "vaccination_warnings": vax_warnings,
        "behavior_profile": _behavior_summary(behavior),
    }


# ── Check out ────────────────────────────────────────────────────────────────

@router.post("/{stay_id}/check-out")
async def check_out(
    stay_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    stay = await _get_stay_or_404(stay_id, current_user.organization_id, db)

    if stay.status != StayStatus.ON_SITE:
        raise HTTPException(status_code=400, detail="Dog is not currently on site")

    pickup_name = data.get("pickup_person_name", "").strip()
    if not pickup_name:
        raise HTTPException(status_code=400, detail="pickup_person_name is required")

    # Create pickup record
    pickup = CheckoutPickupRecord(
        id=str(uuid.uuid4()),
        organization_id=stay.organization_id,
        stay_id=stay_id,
        pickup_person_name=pickup_name,
        relationship_to_household=data.get("relationship_to_household"),
        is_authorized_pickup=data.get("is_authorized_pickup", False),
        id_verified=data.get("id_verified", False),
        id_type=data.get("id_type"),
        confirmed_by=current_user.id,
        notes=data.get("notes"),
    )
    db.add(pickup)

    # Update stay
    stay.status = StayStatus.CHECKED_OUT
    stay.checked_out_at = datetime.now(timezone.utc)
    stay.checked_out_by = current_user.id
    stay.checkout_summary = data.get("checkout_summary")

    # Clear active stay alerts
    alerts_result = await db.execute(
        select(StayAlert).where(
            StayAlert.stay_id == stay_id,
            StayAlert.cleared_at.is_(None),
        )
    )
    for alert in alerts_result.scalars().all():
        alert.cleared_at = datetime.now(timezone.utc)
        alert.cleared_by = current_user.id
        alert.cleared_reason = "Auto-cleared at checkout"

    # End room assignment
    if stay.room_id:
        assignment_result = await db.execute(
            select(RoomAssignment).where(
                RoomAssignment.stay_id == stay_id,
                RoomAssignment.ended_at.is_(None),
            )
        )
        for assignment in assignment_result.scalars().all():
            assignment.ended_at = datetime.now(timezone.utc)

    # Update booking status
    booking = (await db.execute(
        select(Booking).where(Booking.id == stay.booking_id)
    )).scalar_one_or_none()
    if booking:
        booking.status = BookingStatus.CHECKED_OUT
        booking.checked_out_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(stay)

    warn = not data.get("is_authorized_pickup", False)
    return {
        **_stay_dict(stay),
        "pickup_record": _pickup_dict(pickup),
        "unauthorized_pickup_warning": warn,
    }


# ── Stay alerts ───────────────────────────────────────────────────────────────

@router.get("/{stay_id}/alerts")
async def get_alerts(
    stay_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    await _get_stay_or_404(stay_id, current_user.organization_id, db)
    alerts = await _get_active_alerts(stay_id, db)
    return [_alert_dict(a) for a in alerts]


@router.post("/{stay_id}/alerts")
async def add_alert(
    stay_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    stay = await _get_stay_or_404(stay_id, current_user.organization_id, db)

    message = data.get("alert_message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="alert_message is required")

    severity_str = data.get("severity", "caution").upper()
    try:
        severity = StayAlertSeverity[severity_str]
    except KeyError:
        severity = StayAlertSeverity.CAUTION

    alert = StayAlert(
        id=str(uuid.uuid4()),
        organization_id=stay.organization_id,
        stay_id=stay_id,
        dog_id=stay.dog_id,
        alert_message=message,
        severity=severity,
        created_by=current_user.id,
        expires_at=_parse_date(data.get("expires_at")),
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return _alert_dict(alert)


@router.post("/{stay_id}/alerts/{alert_id}/clear")
async def clear_alert(
    stay_id: str,
    alert_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    await _get_stay_or_404(stay_id, current_user.organization_id, db)
    result = await db.execute(
        select(StayAlert).where(StayAlert.id == alert_id, StayAlert.stay_id == stay_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.cleared_at = datetime.now(timezone.utc)
    alert.cleared_by = current_user.id
    alert.cleared_reason = data.get("reason")
    await db.commit()
    await db.refresh(alert)
    return _alert_dict(alert)


# ── Feeding overrides ─────────────────────────────────────────────────────────

@router.get("/{stay_id}/feeding-overrides")
async def get_feeding_overrides(
    stay_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    await _get_stay_or_404(stay_id, current_user.organization_id, db)
    result = await db.execute(
        select(StayFeedingOverride).where(
            StayFeedingOverride.stay_id == stay_id,
            StayFeedingOverride.is_active == True,
        )
    )
    return [_feeding_override_dict(f) for f in result.scalars().all()]


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_stay_or_404(stay_id: str, org_id: str, db: AsyncSession) -> Stay:
    result = await db.execute(
        select(Stay).where(Stay.id == stay_id, Stay.organization_id == org_id)
    )
    stay = result.scalar_one_or_none()
    if not stay:
        raise HTTPException(status_code=404, detail="Stay not found")
    return stay

async def _get_dog(dog_id: str, db: AsyncSession):
    result = await db.execute(select(DogORM).where(DogORM.id == dog_id))
    return result.scalar_one_or_none()

async def _get_active_alerts(stay_id: str, db: AsyncSession):
    result = await db.execute(
        select(StayAlert).where(
            StayAlert.stay_id == stay_id,
            StayAlert.cleared_at.is_(None),
        ).order_by(StayAlert.created_at.desc())
    )
    return result.scalars().all()

async def _is_first_stay(dog_id: str, org_id: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(Stay).where(
            Stay.dog_id == dog_id,
            Stay.organization_id == org_id,
            Stay.status == StayStatus.CHECKED_OUT,
        ).limit(1)
    )
    return result.scalar_one_or_none() is None

async def _get_vax_warnings(dog_id: str, org_id: str, db: AsyncSession) -> list:
    result = await db.execute(
        select(VaccinationRecord).where(
            VaccinationRecord.dog_id == dog_id,
            VaccinationRecord.organization_id == org_id,
        )
    )
    records = result.scalars().all()
    warnings = []
    now = datetime.now(timezone.utc)
    for r in records:
        if r.verification_status == VaccinationStatus.PENDING:
            warnings.append({"type": "unverified", "vaccination_type": r.vaccination_type,
                           "message": f"{r.vaccination_type} pending verification — owner acknowledgment required"})
        elif r.verification_status == VaccinationStatus.REJECTED:
            warnings.append({"type": "rejected", "vaccination_type": r.vaccination_type,
                           "message": f"{r.vaccination_type} rejected"})
        elif r.expiration_date and r.expiration_date < now:
            warnings.append({"type": "expired", "vaccination_type": r.vaccination_type,
                           "message": f"{r.vaccination_type} expired"})
    return warnings

def _behavior_summary(bp) -> dict:
    if not bp:
        return {}
    return {
        "bite_history": bp.bite_history,
        "muzzle_required": bp.muzzle_required,
        "food_guarding": bp.food_guarding,
        "active_safety_alert": bp.active_safety_alert,
        "handling_restrictions": bp.handling_restrictions,
        "handlers_required": bp.handlers_required,
    }

def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

def _stay_dict(s: Stay) -> dict:
    return {
        "id": s.id,
        "booking_id": s.booking_id,
        "dog_id": s.dog_id,
        "status": s.status.value,
        "room_id": s.room_id,
        "checked_in_at": s.checked_in_at.isoformat() if s.checked_in_at else None,
        "checked_out_at": s.checked_out_at.isoformat() if s.checked_out_at else None,
        "is_first_stay": s.is_first_stay,
        "intake_condition_note": s.intake_condition_note,
        "belongings_note": s.belongings_note,
        "checkout_summary": s.checkout_summary,
    }

def _alert_dict(a: StayAlert) -> dict:
    return {
        "id": a.id,
        "stay_id": a.stay_id,
        "dog_id": a.dog_id,
        "alert_message": a.alert_message,
        "severity": a.severity.value,
        "created_by": a.created_by,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "expires_at": a.expires_at.isoformat() if a.expires_at else None,
        "cleared_at": a.cleared_at.isoformat() if a.cleared_at else None,
        "is_active": a.cleared_at is None,
    }

def _pickup_dict(p: CheckoutPickupRecord) -> dict:
    return {
        "id": p.id,
        "pickup_person_name": p.pickup_person_name,
        "relationship_to_household": p.relationship_to_household,
        "is_authorized_pickup": p.is_authorized_pickup,
        "id_verified": p.id_verified,
        "id_type": p.id_type,
        "confirmed_by": p.confirmed_by,
    }

def _feeding_override_dict(f: StayFeedingOverride) -> dict:
    return {
        "id": f.id,
        "override_type": f.override_type,
        "override_detail": f.override_detail,
        "reason": f.reason,
        "is_active": f.is_active,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }

@router.patch("/{stay_id}/room")
async def transfer_room(
    stay_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Move a dog to a different room during their stay."""
    from db_models import Stay, Room
    result = await db.execute(
        select(Stay).where(
            Stay.id == stay_id,
            Stay.organization_id == current_user.organization_id
        )
    )
    stay = result.scalar_one_or_none()
    if not stay:
        raise HTTPException(status_code=404, detail="Stay not found")
    if stay.status not in ["checked_in", "CHECKED_IN"]:
        raise HTTPException(status_code=400, detail="Dog must be checked in to transfer rooms")

    new_room_id = data.get("room_id")
    if not new_room_id:
        raise HTTPException(status_code=400, detail="room_id is required")

    room_result = await db.execute(
        select(Room).where(
            Room.id == new_room_id,
            Room.organization_id == current_user.organization_id
        )
    )
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.is_out_of_service:
        raise HTTPException(status_code=400, detail="Room is out of service")

    old_room = stay.room_id
    stay.room_id = new_room_id
    await db.commit()
    await db.refresh(stay)

    return {"stay_id": stay_id, "old_room_id": old_room, "new_room_id": new_room_id, "dog_id": stay.dog_id}
