"""
Meet and Greet API
Handles scheduling, outcome recording, and eligibility updates.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from database import get_db
from auth import get_current_user, require_role
from db_models import (
    MeetAndGreet, MeetAndGreetOutcome, Dog as DogORM,
    Household, User as UserORM, UserRole
)
import uuid

router = APIRouter(prefix="/api/meet-and-greets", tags=["meet-and-greets"])


@router.get("/dog/{dog_id}")
async def list_dog_mags(
    dog_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_dog_access(dog_id, current_user.organization_id, db)
    result = await db.execute(
        select(MeetAndGreet).where(MeetAndGreet.dog_id == dog_id)
        .order_by(MeetAndGreet.created_at.desc())
    )
    return [_mag_dict(m) for m in result.scalars().all()]


@router.post("")
async def schedule_mag(
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    dog_id = data.get("dog_id", "").strip()
    household_id = data.get("household_id", "").strip()

    if not dog_id or not household_id:
        raise HTTPException(status_code=400, detail="dog_id and household_id are required")

    await _verify_dog_access(dog_id, org_id, db)

    mag = MeetAndGreet(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        dog_id=dog_id,
        household_id=household_id,
        scheduled_at=_parse_date(data.get("scheduled_at")),
        created_by=current_user.id,
    )
    db.add(mag)

    # Update dog meet_and_greet_status to scheduled
    dog_result = await db.execute(
        select(DogORM).where(DogORM.id == dog_id)
    )
    dog = dog_result.scalar_one_or_none()
    if dog:
        dog.meet_and_greet_status = "scheduled"

    await db.commit()
    await db.refresh(mag)
    return _mag_dict(mag)


@router.get("/available-slots")
async def get_available_slots(
    date: str = Query(None),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get available M&G slots for a given date. Only Sun/Mon/Wed/Fri allowed."""
    from datetime import datetime, date as date_type
    import calendar

    ALLOWED_DAYS = [6, 0, 2, 4]  # Sun=6, Mon=0, Wed=2, Fri=4
    SLOTS = [
        "10:00-10:30", "10:30-11:00", "11:00-11:30", "11:30-12:00",
        "14:00-14:30", "14:30-15:00", "15:00-15:30", "15:30-16:00"
    ]

    if date:
        try:
            d = datetime.strptime(date, "%Y-%m-%d").date()
            if d.weekday() not in ALLOWED_DAYS and d.isoweekday() % 7 not in ALLOWED_DAYS:
                # Check if Sunday (isoweekday=7 -> weekday=6)
                weekday = d.weekday()  # Mon=0 ... Sun=6
                if weekday not in ALLOWED_DAYS:
                    return {"date": date, "available": False, "slots": [], "reason": "M&G not available on this day"}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

        # Check which slots are taken
        from sqlalchemy import text
        result = await db.execute(text("""
            SELECT slot FROM meet_and_greets
            WHERE organization_id = :org_id
            AND DATE(scheduled_at) = :date
            AND status NOT IN ('cancelled', 'completed')
            AND slot IS NOT NULL
        """), {"org_id": current_user.organization_id, "date": date})
        taken = {r.slot for r in result.fetchall()}
        available_slots = [s for s in SLOTS if s not in taken]
        return {"date": date, "available": True, "slots": available_slots, "taken": list(taken)}

    # Return general availability info
    return {
        "days": ["Sunday", "Monday", "Wednesday", "Friday"],
        "slots": SLOTS,
        "windows": ["10:00 AM – 12:00 PM", "2:00 PM – 4:00 PM"],
        "description": "Meet & Greets available Sun/Mon/Wed/Fri, 10am-noon or 2pm-4pm"
    }


@router.post("/request")
async def request_mag(
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Customer requests a M&G slot."""
    from sqlalchemy import text
    import uuid

    dog_id = data.get("dog_id")
    household_id = data.get("household_id")
    scheduled_date = data.get("scheduled_date")
    slot = data.get("slot")
    from datetime import date as _date2, datetime as _dt2
    stay_start_str = data.get("stay_start")
    stay_end_str = data.get("stay_end")
    stay_start = _date2.fromisoformat(stay_start_str) if stay_start_str else None
    stay_end = _date2.fromisoformat(stay_end_str) if stay_end_str else None

    if not all([dog_id, household_id, scheduled_date, slot]):
        raise HTTPException(status_code=400, detail="dog_id, household_id, scheduled_date, slot required")

    # Check slot not taken
    from datetime import date as _date
    try:
        parsed_date = _date.fromisoformat(scheduled_date)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format")
    taken = await db.execute(text("""
        SELECT id FROM meet_and_greets
        WHERE organization_id = :org_id
        AND DATE(scheduled_at) = :date
        AND slot = :slot
        AND status NOT IN ('cancelled', 'completed')
    """), {"org_id": current_user.organization_id, "date": parsed_date, "slot": slot})
    if taken.fetchone():
        raise HTTPException(status_code=409, detail="This slot is already booked. Please choose another.")

    # Parse scheduled_at from date + slot start time
    from datetime import datetime as _dt
    slot_start = slot.split("-")[0]
    scheduled_at = _dt.fromisoformat(f"{scheduled_date}T{slot_start}:00")

    mag_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO meet_and_greets 
          (id, organization_id, dog_id, household_id, scheduled_at, slot, status, requested_stay_start, requested_stay_end, requested_by)
        VALUES (:id, :org_id, :dog_id, :hh_id, :scheduled_at, :slot, 'pending', :stay_start, :stay_end, :user_id)
    """), {
        "id": mag_id,
        "org_id": current_user.organization_id,
        "dog_id": dog_id,
        "hh_id": household_id,
        "scheduled_at": scheduled_at,
        "slot": slot,
        "stay_start": stay_start or None,
        "stay_end": stay_end or None,
        "user_id": current_user.id
    })

    # Create pending booking if stay dates provided
    if stay_start and stay_end:
        import uuid as _uuid
        booking_id = str(_uuid.uuid4())
        # Get dog_ids for this household
        await db.execute(text("""
            INSERT INTO bookings (id, organization_id, household_id, check_in_date, check_out_date, status, notes)
            VALUES (:id, :org_id, :hh_id, :start, :end, 'PENDING', 'Pending M&G completion')
        """), {
            "id": booking_id,
            "org_id": current_user.organization_id,
            "hh_id": household_id,
            "start": stay_start,
            "end": stay_end
        })
        await db.execute(text("""
            INSERT INTO booking_dogs (booking_id, dog_id) VALUES (:bid, :did)
        """), {"bid": booking_id, "did": dog_id})

    await db.commit()
    return {"id": mag_id, "status": "pending", "scheduled_at": scheduled_at, "slot": slot}


@router.get("/upcoming")
async def get_upcoming_mags(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming M&G requests for admin/manager dashboard."""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT m.id, m.scheduled_at, m.slot, m.status,
               d.name as dog_name, h.display_name as household_name,
               m.requested_stay_start, m.requested_stay_end
        FROM meet_and_greets m
        JOIN dogs d ON d.id = m.dog_id
        JOIN households h ON h.id = m.household_id
        WHERE m.organization_id = :org_id
        AND m.scheduled_at >= NOW()
        AND m.status NOT IN ('completed', 'cancelled')
        AND m.outcome IS NULL
        ORDER BY m.scheduled_at ASC
        LIMIT 10
    """), {"org_id": current_user.organization_id})
    rows = result.fetchall()
    return [{
        "id": r.id,
        "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
        "slot": r.slot,
        "status": r.status,
        "dog_name": r.dog_name,
        "household_name": r.household_name,
        "requested_stay_start": r.requested_stay_start.isoformat() if r.requested_stay_start else None,
        "requested_stay_end": r.requested_stay_end.isoformat() if r.requested_stay_end else None,
    } for r in rows]


@router.patch("/{mag_id}/status")
async def update_mag_status(
    mag_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    status = data.get("status", "").lower()
    if status not in ["pending", "confirmed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    await db.execute(text("""
        UPDATE meet_and_greets SET status = :status
        WHERE id = :id AND organization_id = :org_id
    """), {"status": status, "id": mag_id, "org_id": current_user.organization_id})
    await db.commit()
    return {"updated": True}


@router.patch("/{mag_id}/status")
async def update_mag_status(
    mag_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    status = data.get("status", "").lower()
    if status not in ["pending", "confirmed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    await db.execute(text("""
        UPDATE meet_and_greets SET status = :status
        WHERE id = :id AND organization_id = :org_id
    """), {"status": status, "id": mag_id, "org_id": current_user.organization_id})
    await db.commit()
    return {"updated": True}


@router.post("/{mag_id}/outcome")
async def record_outcome(
    mag_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mag = await _get_mag_or_404(mag_id, current_user.organization_id, db)

    outcome_str = data.get("outcome", "").upper()
    try:
        outcome = MeetAndGreetOutcome[outcome_str]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid outcome. Must be one of: {[o.value for o in MeetAndGreetOutcome]}"
        )

    if outcome == MeetAndGreetOutcome.CONDITIONAL and not data.get("conditions"):
        raise HTTPException(status_code=400, detail="conditions are required for a conditional outcome")

    mag.outcome = outcome
    mag.conditions = data.get("conditions")
    mag.notes = data.get("notes")
    mag.conducted_by = current_user.id
    mag.completed_at = datetime.now(timezone.utc)

    # Update dog eligibility based on outcome
    dog_result = await db.execute(
        select(DogORM).where(DogORM.id == mag.dog_id)
    )
    dog = dog_result.scalar_one_or_none()

    if dog:
        if outcome == MeetAndGreetOutcome.PASS:
            mag.boarding_eligible_granted = True
            mag.daycare_eligible_granted = True
            dog.boarding_eligible = True
            dog.daycare_eligible = True
            dog.meet_and_greet_status = "completed"
            dog.meet_and_greet_outcome = "pass"
        elif outcome == MeetAndGreetOutcome.CONDITIONAL:
            mag.boarding_eligible_granted = data.get("boarding_eligible_granted", False)
            mag.daycare_eligible_granted = data.get("daycare_eligible_granted", False)
            dog.boarding_eligible = mag.boarding_eligible_granted
            dog.daycare_eligible = mag.daycare_eligible_granted
            dog.meet_and_greet_status = "completed"
            dog.meet_and_greet_outcome = "conditional"
        elif outcome == MeetAndGreetOutcome.FAIL:
            mag.boarding_eligible_granted = False
            mag.daycare_eligible_granted = False
            dog.boarding_eligible = False
            dog.daycare_eligible = False
            dog.meet_and_greet_status = "completed"
            dog.meet_and_greet_outcome = "fail"
        elif outcome == MeetAndGreetOutcome.NO_SHOW:
            dog.meet_and_greet_status = "required"
            dog.meet_and_greet_outcome = "no_show"
        elif outcome == MeetAndGreetOutcome.RESCHEDULED:
            dog.meet_and_greet_status = "scheduled"
            dog.meet_and_greet_outcome = "rescheduled"
    # Auto-create household note with M&G outcome
    if dog and dog.household_id:
        from sqlalchemy import text as _sqlt
        import uuid as _uuid
        outcome_label = {"PASS": "Pass", "CONDITIONAL": "Conditional", "FAIL": "Fail",
                         "NO_SHOW": "No Show", "RESCHEDULED": "Rescheduled"}.get(outcome_str, outcome_str)
        note_parts = [f"M&G {outcome_label} for {dog.name}"]
        if mag.notes: note_parts.append(mag.notes)
        if mag.conditions: note_parts.append(f"Conditions: {mag.conditions}")
        await db.execute(_sqlt("""
            INSERT INTO household_notes (id, organization_id, household_id, note_text, created_by)
            VALUES (:id, :org_id, :hh_id, :note, :uid)
        """), {"id": str(_uuid.uuid4()), "org_id": current_user.organization_id,
               "hh_id": dog.household_id, "note": " | ".join(note_parts), "uid": current_user.id})

    await db.commit()
    await db.refresh(mag)
    return _mag_dict(mag)


async def _verify_dog_access(dog_id: str, org_id: str, db: AsyncSession):
    result = await db.execute(
        select(DogORM).where(DogORM.id == dog_id, DogORM.organization_id == org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Dog not found")

async def _get_mag_or_404(mag_id: str, org_id: str, db: AsyncSession) -> MeetAndGreet:
    result = await db.execute(
        select(MeetAndGreet).where(
            MeetAndGreet.id == mag_id,
            MeetAndGreet.organization_id == org_id
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Meet and greet not found")
    return m

def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

def _mag_dict(m: MeetAndGreet) -> dict:
    return {
        "id": m.id,
        "dog_id": m.dog_id,
        "household_id": m.household_id,
        "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
        "conducted_by": m.conducted_by,
        "outcome": m.outcome.value if m.outcome else None,
        "conditions": m.conditions,
        "boarding_eligible_granted": m.boarding_eligible_granted,
        "daycare_eligible_granted": m.daycare_eligible_granted,
        "notes": m.notes,
        "completed_at": m.completed_at.isoformat() if m.completed_at else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
