"""
Bookings API
Handles reservation creation, capacity checks, conflict detection, and calendar data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from database import get_db
from auth import get_current_user, require_role
from db_models import (
    Booking, BookingDog, BookingStatus, Dog as DogORM,
    Household, Room, ServiceType, FacilityStatus, FacilityStatusType,
    User as UserORM, UserRole, VaccinationRecord, VaccinationStatus,
    BehaviorProfile
)
import uuid

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


# ── List bookings ────────────────────────────────────────────────────────────

@router.get("")
async def list_bookings(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    household_id: Optional[str] = Query(None),
    service_code: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    q = select(Booking).where(Booking.organization_id == org_id)

    if status:
        q = q.where(Booking.status == status)
    if household_id:
        q = q.where(Booking.household_id == household_id)
    if start_date:
        q = q.where(Booking.check_out_date >= _parse_date(start_date))
    if end_date:
        q = q.where(Booking.check_in_date <= _parse_date(end_date))

    q = q.order_by(Booking.check_in_date).offset(skip).limit(limit)
    result = await db.execute(q)
    bookings = result.scalars().all()

    out = []
    for b in bookings:
        bd = await _get_booking_dogs(b.id, db)
        out.append(_booking_dict(b, bd))
    return out


# ── Get single booking ───────────────────────────────────────────────────────

@router.get("/{booking_id}")
async def get_booking(
    booking_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await _get_booking_or_404(booking_id, current_user.organization_id, db)
    bd = await _get_booking_dogs(booking_id, db)
    conflicts = await _check_conflicts(booking, db)
    result = _booking_dict(booking, bd)
    result["conflicts"] = conflicts
    return result


# ── Create booking ───────────────────────────────────────────────────────────

@router.post("")
async def create_booking(
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    household_id = data.get("household_id", "").strip()
    dog_ids = data.get("dog_ids", [])
    check_in_date = _parse_date(data.get("check_in_date"))
    check_out_date = _parse_date(data.get("check_out_date"))

    if not household_id:
        raise HTTPException(status_code=400, detail="household_id is required")
    if not dog_ids:
        raise HTTPException(status_code=400, detail="At least one dog is required")
    if not check_in_date or not check_out_date:
        raise HTTPException(status_code=400, detail="check_in_date and check_out_date are required")
    if check_out_date <= check_in_date:
        raise HTTPException(status_code=400, detail="check_out_date must be after check_in_date")

    # Verify household
    hh = (await db.execute(
        select(Household).where(Household.id == household_id, Household.organization_id == org_id)
    )).scalar_one_or_none()
    if not hh:
        raise HTTPException(status_code=404, detail="Household not found")

    # Verify all dogs belong to org and check eligibility
    warnings = []
    for dog_id in dog_ids:
        dog = (await db.execute(
            select(DogORM).where(DogORM.id == dog_id, DogORM.organization_id == org_id)
        )).scalar_one_or_none()
        if not dog:
            raise HTTPException(status_code=404, detail=f"Dog {dog_id} not found")

        # Meet and greet check
        if dog.meet_and_greet_status != "completed":
            if current_user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=400,
                    detail=f"{dog.name} has not completed a meet-and-greet. Owner override required."
                )
            warnings.append({"type": "meet_and_greet", "dog_id": dog_id, "dog_name": dog.name,
                            "message": f"{dog.name} has not completed a meet-and-greet"})

        # Vaccination check
        vax_issues = await _check_vaccinations(dog_id, org_id, db)
        warnings.extend(vax_issues)

    # Facility closure check
    closure = await _check_facility_closure(org_id, check_in_date, check_out_date, db)
    if closure and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=400, detail=f"Facility is closed: {closure}")
    if closure:
        warnings.append({"type": "facility_closure", "message": closure})

    # Check overall capacity
    capacity_warning = await _check_capacity(org_id, check_in_date, check_out_date, len(dog_ids), db)
    if capacity_warning:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=400, detail=capacity_warning)
        warnings.append({"type": "capacity", "message": capacity_warning})

    booking = Booking(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        household_id=household_id,
        location_id=data.get("location_id") or await _get_default_location(org_id, db),
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        status=BookingStatus.CONFIRMED,
        total_price=data.get("total_price", 0.0),
        notes=data.get("notes"),
        special_request=data.get("special_request"),
        created_by=current_user.id,
        dog_ids=dog_ids,
    )
    db.add(booking)
    await db.flush()

    # Create BookingDog records
    for dog_id in dog_ids:
        bd = BookingDog(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            booking_id=booking.id,
            dog_id=dog_id,
            care_notes=data.get("care_notes"),
        )
        db.add(bd)

    await db.commit()
    await db.refresh(booking)
    booking_dogs = await _get_booking_dogs(booking.id, db)
    result = _booking_dict(booking, booking_dogs)
    result["warnings"] = warnings
    return result


# ── Update booking status ────────────────────────────────────────────────────

@router.patch("/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await _get_booking_or_404(booking_id, current_user.organization_id, db)
    new_status = data.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="status is required")

    booking.status = new_status
    if data.get("notes"):
        booking.notes = data["notes"]

    await db.commit()
    await db.refresh(booking)
    bd = await _get_booking_dogs(booking_id, db)
    return _booking_dict(booking, bd)


# ── Cancel booking ────────────────────────────────────────────────────────────

@router.post("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await _get_booking_or_404(booking_id, current_user.organization_id, db)

    if booking.status in [BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]:
        raise HTTPException(status_code=400, detail="Cannot cancel a booking that is checked in or completed")

    booking.status = BookingStatus.CANCELLED
    booking.modification_reason = data.get("reason")

    await db.commit()
    await db.refresh(booking)
    bd = await _get_booking_dogs(booking_id, db)
    return _booking_dict(booking, bd)


# ── Calendar endpoint ─────────────────────────────────────────────────────────

@router.get("/calendar/range")
async def get_calendar(
    start: str = Query(...),
    end: str = Query(...),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    start_dt = _parse_date(start)
    end_dt = _parse_date(end)

    # Get bookings in range
    bookings_result = await db.execute(
        select(Booking).where(
            Booking.organization_id == org_id,
            Booking.check_in_date <= end_dt,
            Booking.check_out_date >= start_dt,
            Booking.status != BookingStatus.CANCELLED,
        ).order_by(Booking.check_in_date)
    )
    bookings = bookings_result.scalars().all()

    # Get facility closures in range
    closures_result = await db.execute(
        select(FacilityStatus).where(
            FacilityStatus.organization_id == org_id,
            FacilityStatus.date >= start_dt,
            FacilityStatus.date <= end_dt,
            FacilityStatus.status != FacilityStatusType.OPEN,
        )
    )
    closures = closures_result.scalars().all()

    # Build calendar entries
    entries = []
    for b in bookings:
        bd = await _get_booking_dogs(b.id, db)
        entry = _booking_dict(b, bd)
        entry["calendar_type"] = "booking"
        entries.append(entry)

    for c in closures:
        entries.append({
            "calendar_type": "closure",
            "date": c.date.isoformat(),
            "status": c.status.value,
            "reason": c.reason,
            "affects_bookings": c.affects_bookings,
        })

    # Occupancy by date
    occupancy = await _get_occupancy_summary(org_id, start_dt, end_dt, db)

    return {
        "entries": entries,
        "occupancy": occupancy,
        "total_rooms": 8,
    }


# ── Rooms list ────────────────────────────────────────────────────────────────

@router.get("/rooms/list")
async def list_rooms(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Room).where(
            Room.organization_id == current_user.organization_id,
            Room.is_active == True,
        ).order_by(Room.sort_order)
    )
    rooms = result.scalars().all()
    return [_room_dict(r) for r in rooms]


# ── Conflict check ────────────────────────────────────────────────────────────

@router.post("/check-conflicts")
async def check_conflicts(
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    check_in_date = _parse_date(data.get("check_in_date"))
    check_out_date = _parse_date(data.get("check_out_date"))
    dog_ids = data.get("dog_ids", [])

    conflicts = []

    # Dog double-booking check
    for dog_id in dog_ids:
        existing = await db.execute(
            select(Booking).join(
                BookingDog, BookingDog.booking_id == Booking.id
            ).where(
                Booking.organization_id == org_id,
                BookingDog.dog_id == dog_id,
                Booking.status.notin_([BookingStatus.CANCELLED]),
                Booking.check_in_date < check_out_date,
                Booking.check_out_date > check_in_date,
            )
        )
        if existing.scalar_one_or_none():
            dog = (await db.execute(select(DogORM).where(DogORM.id == dog_id))).scalar_one_or_none()
            conflicts.append({
                "type": "double_booking",
                "severity": "blocking",
                "message": f"{dog.name if dog else dog_id} already has a booking in this date range"
            })

    # Capacity check
    cap_warning = await _check_capacity(org_id, check_in_date, check_out_date, len(dog_ids), db)
    if cap_warning:
        conflicts.append({"type": "capacity", "severity": "warning", "message": cap_warning})

    # Facility closure check
    closure = await _check_facility_closure(org_id, check_in_date, check_out_date, db)
    if closure:
        conflicts.append({"type": "facility_closure", "severity": "blocking", "message": closure})

    return {"conflicts": conflicts, "has_blocking": any(c["severity"] == "blocking" for c in conflicts)}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_booking_or_404(booking_id: str, org_id: str, db: AsyncSession) -> Booking:
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id, Booking.organization_id == org_id)
    )
    b = result.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    return b

async def _get_booking_dogs(booking_id: str, db: AsyncSession) -> list:
    result = await db.execute(
        select(BookingDog).where(BookingDog.booking_id == booking_id)
    )
    return result.scalars().all()

async def _check_conflicts(booking: Booking, db: AsyncSession) -> list:
    conflicts = []
    closure = await _check_facility_closure(
        booking.organization_id, booking.check_in_date, booking.check_out_date, db
    )
    if closure:
        conflicts.append({"type": "facility_closure", "message": closure})
    return conflicts

async def _check_facility_closure(org_id: str, start: datetime, end: datetime, db: AsyncSession):
    result = await db.execute(
        select(FacilityStatus).where(
            FacilityStatus.organization_id == org_id,
            FacilityStatus.date >= start,
            FacilityStatus.date <= end,
            FacilityStatus.status != FacilityStatusType.OPEN,
            FacilityStatus.affects_bookings == True,
        ).limit(1)
    )
    closure = result.scalar_one_or_none()
    if closure:
        return f"Facility is {closure.status.value} on {closure.date.date()}: {closure.reason or 'No reason given'}"
    return None

async def _check_capacity(org_id: str, start: datetime, end: datetime, new_dogs: int, db: AsyncSession):
    # Count dogs already booked in this range
    result = await db.execute(
        select(func.count(BookingDog.id)).join(
            Booking, Booking.id == BookingDog.booking_id
        ).where(
            Booking.organization_id == org_id,
            Booking.status.notin_([BookingStatus.CANCELLED]),
            Booking.check_in_date < end,
            Booking.check_out_date > start,
        )
    )
    current_dogs = result.scalar() or 0
    total_capacity = 24  # 8 rooms x 3 dogs
    if current_dogs + new_dogs > total_capacity:
        available = max(0, total_capacity - current_dogs)
        return f"Capacity exceeded: {current_dogs} dogs booked, {available} spots available, {new_dogs} requested"
    return None

async def _check_vaccinations(dog_id: str, org_id: str, db: AsyncSession) -> list:
    from datetime import datetime, timezone
    result = await db.execute(
        select(VaccinationRecord).where(
            VaccinationRecord.dog_id == dog_id,
            VaccinationRecord.organization_id == org_id,
        )
    )
    records = result.scalars().all()
    issues = []
    now = datetime.now(timezone.utc)
    for r in records:
        if r.verification_status == VaccinationStatus.REJECTED:
            issues.append({"type": "vaccination_rejected", "dog_id": dog_id,
                          "message": f"{r.vaccination_type} vaccination rejected"})
        elif r.verification_status == VaccinationStatus.PENDING:
            issues.append({"type": "vaccination_pending", "dog_id": dog_id,
                          "message": f"{r.vaccination_type} vaccination pending verification"})
        elif r.expiration_date and r.expiration_date < now:
            issues.append({"type": "vaccination_expired", "dog_id": dog_id,
                          "message": f"{r.vaccination_type} vaccination expired"})
    return issues

async def _get_occupancy_summary(org_id: str, start: datetime, end: datetime, db: AsyncSession) -> list:
    result = await db.execute(
        select(Booking).where(
            Booking.organization_id == org_id,
            Booking.check_in_date <= end,
            Booking.check_out_date >= start,
            Booking.status.notin_([BookingStatus.CANCELLED]),
        )
    )
    bookings = result.scalars().all()
    return [{"booking_id": b.id, "check_in": b.check_in_date.isoformat(),
             "check_out": b.check_out_date.isoformat(), "dog_count": len(b.dog_ids or [])} for b in bookings]

async def _get_default_location(org_id: str, db: AsyncSession) -> str:
    from db_models import Location as LocationORM
    result = await db.execute(
        select(LocationORM).where(LocationORM.organization_id == org_id).limit(1)
    )
    loc = result.scalar_one_or_none()
    if not loc:
        # Create a default location if none exists
        from db_models import Location as LocationORM
        import uuid
        loc = LocationORM(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            name="K9 Country Club",
            address="Elk River, MN",
            capacity=24,
            contact_email="",
            contact_phone="",
        )
        db.add(loc)
        await db.flush()
    return loc.id

async def _get_default_location(org_id: str, db: AsyncSession) -> str:
    from db_models import Location as LocationORM
    result = await db.execute(
        select(LocationORM).where(LocationORM.organization_id == org_id).limit(1)
    )
    loc = result.scalar_one_or_none()
    if not loc:
        # Create a default location if none exists
        from db_models import Location as LocationORM
        import uuid
        loc = LocationORM(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            name="K9 Country Club",
            address="Elk River, MN",
            capacity=24,
            contact_email="",
            contact_phone="",
        )
        db.add(loc)
        await db.flush()
    return loc.id

def _parse_date(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

def _booking_dict(b: Booking, booking_dogs: list, household_name: str = None, dog_names: list = None) -> dict:
    return {
        "id": b.id,
        "household_id": b.household_id,
        "household_name": household_name,
        "check_in_date": b.check_in_date.isoformat() if b.check_in_date else None,
        "check_out_date": b.check_out_date.isoformat() if b.check_out_date else None,
        "status": b.status.value if b.status else None,
        "total_price": b.total_price,
        "notes": b.notes,
        "special_request": b.special_request,
        "dog_ids": [bd.dog_id for bd in booking_dogs],
        "dog_names": dog_names or [],
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }

def _room_dict(r: Room) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "room_type": r.room_type,
        "max_dogs": r.max_dogs,
        "adjacency_group": r.adjacency_group,
        "is_active": r.is_active,
        "is_out_of_service": r.is_out_of_service,
        "out_of_service_reason": r.out_of_service_reason,
        "sort_order": r.sort_order,
    }

from typing import Optional
