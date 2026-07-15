"""
Meet and Greet API
Handles scheduling, outcome recording, and eligibility updates.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
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
    await _verify_dog_access(dog_id, current_user.organization_id, db, current_user)
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

    if current_user.role == UserRole.CUSTOMER:
        household_id = current_user.household_id or ""

    if not dog_id or not household_id:
        raise HTTPException(status_code=400, detail="dog_id and household_id are required")

    dog = await _verify_dog_access(dog_id, org_id, db, current_user)
    if current_user.role == UserRole.CUSTOMER and dog.household_id != household_id:
        raise HTTPException(status_code=403, detail="Dog does not belong to your household")

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
    """Customer requests a M&G slot for one or more dogs at once.

    Accepts either `dog_ids` (list) or the legacy single `dog_id` for
    backward compatibility. All dogs share the same scheduled_at/slot --
    one appointment slot per household, one meet_and_greets row per dog.
    """
    from sqlalchemy import text
    import uuid

    dog_ids = data.get("dog_ids")
    if not dog_ids:
        single = data.get("dog_id")
        dog_ids = [single] if single else []
    household_id = data.get("household_id")
    scheduled_date = data.get("scheduled_date")
    slot = data.get("slot")
    from datetime import date as _date2, datetime as _dt2
    stay_start_str = data.get("stay_start")
    stay_end_str = data.get("stay_end")
    stay_start = _date2.fromisoformat(stay_start_str) if stay_start_str else None
    stay_end = _date2.fromisoformat(stay_end_str) if stay_end_str else None

    if not dog_ids or not household_id or not scheduled_date or not slot:
        raise HTTPException(status_code=400, detail="dog_ids, household_id, scheduled_date, slot required")

    if current_user.role == UserRole.CUSTOMER and household_id != current_user.household_id:
        raise HTTPException(status_code=403, detail="You can only schedule for your own household")

    for dog_id in dog_ids:
        dog_result = await db.execute(
            select(DogORM).where(DogORM.id == dog_id, DogORM.organization_id == current_user.organization_id)
        )
        dog = dog_result.scalar_one_or_none()
        if not dog:
            raise HTTPException(status_code=404, detail=f"Dog {dog_id} not found")
        if current_user.role == UserRole.CUSTOMER and dog.household_id != current_user.household_id:
            raise HTTPException(status_code=403, detail=f"{dog.name} does not belong to your household")

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
        AND household_id != :hh_id
    """), {"org_id": current_user.organization_id, "date": parsed_date, "slot": slot, "hh_id": household_id})
    if taken.fetchone():
        raise HTTPException(status_code=409, detail="This slot is already booked. Please choose another.")

    from datetime import datetime as _dt
    slot_start = slot.split("-")[0]
    scheduled_at = _dt.fromisoformat(f"{scheduled_date}T{slot_start}:00")

    mag_ids = []
    for dog_id in dog_ids:
        mag_id = str(uuid.uuid4())
        mag_ids.append(mag_id)
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

    booking_id = None
    if stay_start and stay_end:
        import uuid as _uuid
        import json as _json
        from db_models import Location as LocationORM

        loc_result = await db.execute(
            select(LocationORM).where(LocationORM.organization_id == current_user.organization_id).limit(1)
        )
        loc = loc_result.scalar_one_or_none()
        if not loc:
            loc = LocationORM(
                id=str(_uuid.uuid4()),
                organization_id=current_user.organization_id,
                name="K9 Country Club",
                address="Elk River, MN",
                capacity=24,
                contact_email="",
                contact_phone="",
            )
            db.add(loc)
            await db.flush()

        booking_id = str(_uuid.uuid4())
        await db.execute(text("""
            INSERT INTO bookings (id, organization_id, household_id, location_id, check_in_date, check_out_date, status, total_price, notes, dog_ids)
            VALUES (:id, :org_id, :hh_id, :loc_id, :start, :end, 'PENDING', 0.0, 'Pending M&G completion', :dog_ids)
        """), {
            "id": booking_id,
            "org_id": current_user.organization_id,
            "hh_id": household_id,
            "loc_id": loc.id,
            "start": stay_start,
            "end": stay_end,
            "dog_ids": _json.dumps(dog_ids),
        })
        # booking_dogs_v2 is the real association table the rest of the app
        # reads from (routes/bookings.py's BookingDog ORM) -- plain
        # "booking_dogs" is legacy/superseded and nothing reads it.
        for dog_id in dog_ids:
            await db.execute(text("""
                INSERT INTO booking_dogs_v2 (id, organization_id, booking_id, dog_id)
                VALUES (:id, :org_id, :bid, :did)
            """), {
                "id": str(_uuid.uuid4()),
                "org_id": current_user.organization_id,
                "bid": booking_id,
                "did": dog_id,
            })

    await db.commit()
    return {
        "ids": mag_ids,
        "id": mag_ids[0],
        "status": "pending",
        "scheduled_at": scheduled_at,
        "slot": slot,
        "booking_id": booking_id,
        "dog_count": len(dog_ids),
    }


@router.post("/join-existing")
async def join_existing_mag(
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add another dog to a household's already-scheduled M&G slot."""
    from sqlalchemy import text
    import uuid

    dog_id = data.get("dog_id")
    join_mag_id = data.get("join_mag_id")
    if not dog_id or not join_mag_id:
        raise HTTPException(status_code=400, detail="dog_id and join_mag_id are required")

    existing = await db.execute(
        select(MeetAndGreet).where(
            MeetAndGreet.id == join_mag_id,
            MeetAndGreet.organization_id == current_user.organization_id,
        )
    )
    existing_mag = existing.scalar_one_or_none()
    if not existing_mag:
        raise HTTPException(status_code=404, detail="Meet & greet not found")
    if existing_mag.status in ("cancelled", "completed"):
        raise HTTPException(status_code=400, detail="That meet & greet is no longer upcoming")

    dog_result = await db.execute(
        select(DogORM).where(DogORM.id == dog_id, DogORM.organization_id == current_user.organization_id)
    )
    dog = dog_result.scalar_one_or_none()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    if dog.household_id != existing_mag.household_id:
        raise HTTPException(status_code=403, detail="Dog does not belong to this household meet & greet")
    if current_user.role == UserRole.CUSTOMER and current_user.household_id != existing_mag.household_id:
        raise HTTPException(status_code=403, detail="You can only join your own household meet & greet")

    dup = await db.execute(
        select(MeetAndGreet).where(
            MeetAndGreet.dog_id == dog_id,
            MeetAndGreet.scheduled_at == existing_mag.scheduled_at,
            MeetAndGreet.slot == existing_mag.slot,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This dog is already on that meet & greet")

    mag_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO meet_and_greets
          (id, organization_id, dog_id, household_id, scheduled_at, slot, status, requested_by)
        VALUES (:id, :org_id, :dog_id, :hh_id, :scheduled_at, :slot, 'pending', :user_id)
    """), {
        "id": mag_id,
        "org_id": current_user.organization_id,
        "dog_id": dog_id,
        "hh_id": existing_mag.household_id,
        "scheduled_at": existing_mag.scheduled_at,
        "slot": existing_mag.slot,
        "user_id": current_user.id,
    })
    await db.commit()
    return {
        "id": mag_id,
        "status": "pending",
        "scheduled_at": existing_mag.scheduled_at.isoformat() if existing_mag.scheduled_at else None,
        "slot": existing_mag.slot,
    }


@router.get("/upcoming")
async def get_upcoming_mags(
    household_id: str = Query(None),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming M&G requests for admin/manager dashboard or customer."""
    from sqlalchemy import text
    # Customers can only see their own household's M&Gs
    role = str(current_user.role).lower().replace("userrole.", "")
    if role == "customer" and not household_id:
        household_id = current_user.household_id

    where_extra = "AND m.household_id = :hh_id" if household_id else ""
    params = {"org_id": current_user.organization_id}
    if household_id:
        params["hh_id"] = household_id

    result = await db.execute(text(f"""
        SELECT m.id, m.scheduled_at, m.slot, m.status,
               d.name as dog_name, h.display_name as household_name,
               m.requested_stay_start, m.requested_stay_end,
               m.household_id
        FROM meet_and_greets m
        JOIN dogs d ON d.id = m.dog_id
        JOIN households h ON h.id = m.household_id
        WHERE m.organization_id = :org_id
        AND m.scheduled_at >= NOW()
        AND m.status NOT IN ('completed', 'cancelled')
        AND m.outcome IS NULL
        {where_extra}
        ORDER BY m.scheduled_at ASC
        LIMIT 20
    """), params)
    rows = result.fetchall()
    return [{
        "id": r.id,
        "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
        "slot": r.slot,
        "status": r.status,
        "dog_name": r.dog_name,
        "household_name": r.household_name,
        "household_id": r.household_id,
        "requested_stay_start": r.requested_stay_start.isoformat() if r.requested_stay_start else None,
        "requested_stay_end": r.requested_stay_end.isoformat() if r.requested_stay_end else None,
    } for r in rows]


@router.patch("/{mag_id}/status")
async def update_mag_status(
    mag_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Staff/admin/manager only -- meet-and-greet scheduling status is a
    staff decision, not something a customer can flip on their own record."""
    status = data.get("status", "").lower()
    if status not in ["pending", "confirmed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    mag_result = await db.execute(
        select(MeetAndGreet).where(
            MeetAndGreet.id == mag_id,
            MeetAndGreet.organization_id == current_user.organization_id,
        )
    )
    mag = mag_result.scalar_one_or_none()
    if not mag:
        raise HTTPException(status_code=404, detail="Meet & greet not found")

    old_status = mag.status
    mag.status = status
    await db.commit()
    await db.refresh(mag)

    if old_status != "confirmed" and status == "confirmed":
        try:
            from email_service import send_email, is_configured
            if is_configured():
                dog = (await db.execute(select(DogORM).where(DogORM.id == mag.dog_id))).scalar_one_or_none()
                portal_users = (await db.execute(
                    select(UserORM).where(
                        UserORM.household_id == mag.household_id,
                        UserORM.role == UserRole.CUSTOMER,
                    )
                )).scalars().all()
                dog_name = dog.name if dog else "your dog"
                when = mag.scheduled_at.strftime("%A, %B %-d, %Y") if mag.scheduled_at else "your scheduled date"
                slot_label = mag.slot or ""
                for u in portal_users:
                    if not u.email:
                        continue
                    try:
                        await send_email(
                            to_email=u.email,
                            subject="Your Meet & Greet is Confirmed!",
                            html_body=f"""
                                <p>Hi {u.full_name or ''},</p>
                                <p>Your Meet & Greet for <strong>{dog_name}</strong> is confirmed for
                                <strong>{when}</strong>{f' ({slot_label})' if slot_label else ''}.</p>
                                <p>We look forward to meeting you!</p>
                            """,
                        )
                    except Exception as e:
                        print(f"Failed to send M&G confirmation email to {u.email}: {e}")
        except Exception as e:
            print(f"M&G confirmation email step failed: {e}")

    return {"updated": True}


@router.post("/{mag_id}/outcome")
async def record_outcome(
    mag_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
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


async def _verify_dog_access(dog_id: str, org_id: str, db: AsyncSession, current_user: UserORM = None):
    result = await db.execute(
        select(DogORM).where(DogORM.id == dog_id, DogORM.organization_id == org_id)
    )
    dog = result.scalar_one_or_none()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    if current_user is not None and current_user.role == UserRole.CUSTOMER:
        if dog.household_id != current_user.household_id:
            raise HTTPException(status_code=404, detail="Dog not found")
    return dog

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


@router.post("/send-reminders")
async def send_mag_reminders(
    x_cron_secret: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Meant to be called once a day by a cron job (see
    scripts/send_mag_reminders.sh), not by any user-facing UI. Finds
    pending/confirmed meet-and-greets scheduled within the next 2 days
    that haven't already had a reminder sent, emails the household's
    portal accounts, and marks reminder_sent_at so it only ever fires
    once per record."""
    import os
    from sqlalchemy import text

    expected_secret = os.environ.get("CRON_SECRET")
    if not expected_secret or x_cron_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid or missing cron secret")

    from email_service import send_email, is_configured
    if not is_configured():
        return {"sent": 0, "reason": "Email is not configured"}

    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=2)

    result = await db.execute(text("""
        SELECT id, dog_id, household_id, scheduled_at, slot
        FROM meet_and_greets
        WHERE status IN ('pending', 'confirmed')
        AND reminder_sent_at IS NULL
        AND scheduled_at IS NOT NULL
        AND scheduled_at BETWEEN :now AND :window_end
    """), {"now": now, "window_end": window_end})
    rows = result.fetchall()

    sent_count = 0
    for row in rows:
        dog = (await db.execute(select(DogORM).where(DogORM.id == row.dog_id))).scalar_one_or_none()
        if not dog:
            continue
        portal_users = (await db.execute(
            select(UserORM).where(
                UserORM.household_id == row.household_id,
                UserORM.role == UserRole.CUSTOMER,
            )
        )).scalars().all()

        when = row.scheduled_at.strftime("%A, %B %-d, %Y")
        slot_label = row.slot or ""
        for u in portal_users:
            if not u.email:
                continue
            try:
                await send_email(
                    to_email=u.email,
                    subject="Reminder: Your Meet & Greet is Coming Up!",
                    html_body=f"""
                        <p>Hi {u.full_name or ''},</p>
                        <p>Just a reminder -- <strong>{dog.name}'s</strong> Meet & Greet is coming up on
                        <strong>{when}</strong>{f' ({slot_label})' if slot_label else ''}.</p>
                        <p>We look forward to seeing you!</p>
                    """,
                )
                sent_count += 1
            except Exception as e:
                print(f"Failed to send M&G reminder to {u.email}: {e}")

        await db.execute(text("""
            UPDATE meet_and_greets SET reminder_sent_at = :now WHERE id = :id
        """), {"now": now, "id": row.id})

    await db.commit()
    return {"records_processed": len(rows), "emails_sent": sent_count}
