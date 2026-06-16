"""
Daily Command Dashboard API
Returns prioritized operational data for the daily dashboard.
Priority order per spec Section 7.5.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timezone, timedelta
from database import get_db
from auth import get_current_user, require_role
from db_models import (UserRole,
    Stay, StayStatus, StayAlert,
    Task, TaskStatus, Incident, IncidentStatus, IncidentSeverity, StayAlertSeverity,
    Booking, BookingStatus, BookingDog,
    Dog as DogORM, Room, User as UserORM,
    VaccinationRecord, VaccinationStatus,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    now = datetime.now(timezone.utc)
    today = now.date()
    two_hours = now + timedelta(hours=2)
    one_hour = now + timedelta(hours=1)
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)

    # ── On-site dogs ──────────────────────────────────────────────────────────
    on_site_result = await db.execute(
        select(Stay).where(
            Stay.organization_id == org_id,
            Stay.status == StayStatus.ON_SITE,
        )
    )
    on_site_stays = on_site_result.scalars().all()
    on_site_count = len(on_site_stays)

    # ── Active warning-level alerts ───────────────────────────────────────────
    warning_alerts_result = await db.execute(
        select(StayAlert).where(
            StayAlert.organization_id == org_id,
            StayAlert.cleared_at.is_(None),
            StayAlert.severity == StayAlertSeverity.WARNING,
        )
    )
    warning_alerts = warning_alerts_result.scalars().all()

    # ── All active alerts ─────────────────────────────────────────────────────
    all_alerts_result = await db.execute(
        select(StayAlert).where(
            StayAlert.organization_id == org_id,
            StayAlert.cleared_at.is_(None),
        ).order_by(StayAlert.severity.desc(), StayAlert.created_at.desc())
    )
    all_alerts = all_alerts_result.scalars().all()

    # ── Today's arrivals ──────────────────────────────────────────────────────
    arrivals_result = await db.execute(
        select(Booking).where(
            Booking.organization_id == org_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]),
            Booking.check_in_date >= today_start,
            Booking.check_in_date <= today_end,
        ).order_by(Booking.check_in_date)
    )
    todays_arrivals = arrivals_result.scalars().all()

    # Arrivals within next 2 hours
    arriving_soon_result = await db.execute(
        select(Booking).where(
            Booking.organization_id == org_id,
            Booking.status == BookingStatus.CONFIRMED,
            Booking.check_in_date >= now,
            Booking.check_in_date <= two_hours,
        )
    )
    arriving_soon = arriving_soon_result.scalars().all()

    # ── Today's departures ────────────────────────────────────────────────────
    departing_today = []
    for stay in on_site_stays:
        booking = (await db.execute(
            select(Booking).where(Booking.id == stay.booking_id)
        )).scalar_one_or_none()
        if booking and booking.check_out_date.date() == today:
            departing_today.append(stay)

    departing_soon = []
    for stay in on_site_stays:
        booking = (await db.execute(
            select(Booking).where(Booking.id == stay.booking_id)
        )).scalar_one_or_none()
        if booking and now <= booking.check_out_date <= two_hours:
            dog = (await db.execute(select(DogORM).where(DogORM.id == stay.dog_id))).scalar_one_or_none()
            room = (await db.execute(select(Room).where(Room.id == stay.room_id))).scalar_one_or_none() if stay.room_id else None
            from db_models import Household
            hh = (await db.execute(select(Household).where(Household.id == booking.household_id))).scalar_one_or_none()
            departing_soon.append({
                "stay_id": stay.id,
                "dog_id": stay.dog_id,
                "dog_name": dog.name if dog else None,
                "room_name": room.name if room else None,
                "household_name": hh.display_name if hh else None,
                "check_out_date": booking.check_out_date.isoformat(),
            })

    # ── Vaccination warnings for on-site dogs ─────────────────────────────────
    vax_warnings = []
    for stay in on_site_stays:
        vax_result = await db.execute(
            select(VaccinationRecord).where(
                VaccinationRecord.dog_id == stay.dog_id,
                VaccinationRecord.organization_id == org_id,
                VaccinationRecord.verification_status.in_([
                    VaccinationStatus.PENDING,
                    VaccinationStatus.REJECTED,
                ])
            )
        )
        for vax in vax_result.scalars().all():
            dog = (await db.execute(select(DogORM).where(DogORM.id == stay.dog_id))).scalar_one_or_none()
            vax_warnings.append({
                "dog_id": stay.dog_id,
                "dog_name": dog.name if dog else None,
                "vaccination_type": vax.vaccination_type,
                "status": vax.verification_status.value,
            })

    # ── Room occupancy summary ────────────────────────────────────────────────
    rooms_result = await db.execute(
        select(Room).where(
            Room.organization_id == org_id,
            Room.is_active == True,
        ).order_by(Room.sort_order)
    )
    rooms = rooms_result.scalars().all()

    room_occupancy = []
    for room in rooms:
        occupants = [s for s in on_site_stays if s.room_id == room.id]
        room_occupancy.append({
            "room_id": room.id,
            "room_name": room.name,
            "max_dogs": room.max_dogs,
            "current_dogs": len(occupants),
            "is_out_of_service": room.is_out_of_service,
            "adjacency_group": room.adjacency_group,
        })

    # ── Build prioritized dashboard ───────────────────────────────────────────
    # Priority order per spec Section 7.5:
    # 1. Active emergencies / severity-4 incidents (placeholder - incidents in Phase 6)
    # 2. Overdue medications (placeholder - medications in Phase 5)
    # 3. Active stay alerts (warning level)
    # 4. Dogs arriving within 2 hours
    # 5. Dogs departing within 2 hours
    # 6. Medications due within 1 hour (placeholder)
    # 7. Overdue tasks (placeholder - tasks in Phase 6)
    # 8. Active stay alerts (caution and info)
    # 9. Overdue care events (placeholder)
    # 10. Dogs on site with care due (placeholder)

    return {
        # Summary counts
        "on_site_count": on_site_count,
        "arriving_today_count": len(todays_arrivals),
        "departing_today_count": len(departing_today),
        "active_alert_count": len(all_alerts),
        "warning_alert_count": len(warning_alerts),

        # Priority 3: Warning-level alerts
        "warning_alerts": [_alert_summary(a) for a in warning_alerts],

        # Priority 4: Arriving soon (within 2 hours)
        "arriving_soon": [await _booking_summary(b, db) for b in arriving_soon],

        # Priority 5: Departing soon (within 2 hours)
        "departing_soon": departing_soon,

        # Priority 8: All other active alerts
        "caution_alerts": [_alert_summary(a) for a in all_alerts
                          if a.severity != StayAlertSeverity.WARNING],

        # Today's full lists
        "todays_arrivals": [await _booking_summary(b, db) for b in todays_arrivals],
        "todays_departures": [_stay_summary(s) for s in departing_today],

        # Room occupancy
        "room_occupancy": room_occupancy,

        # Vaccination warnings
        "vaccination_warnings": vax_warnings,

        # Open incidents needing attention
        "open_incidents": await _get_open_incidents(org_id, db),
        "overdue_tasks": await _get_overdue_tasks(org_id, db),
        "overdue_medications": [],
        "unacknowledged_handoffs": [],
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_open_incidents(org_id: str, db) -> list:
    from sqlalchemy import text
    result = await db.execute(
        text("""SELECT id, title, severity::text, status::text, acknowledged_at
                FROM incidents
                WHERE organization_id = :org_id
                AND status::text NOT IN ('CLOSED', 'RESOLVED', 'closed', 'resolved')
                ORDER BY occurred_at DESC LIMIT 5"""),
        {"org_id": org_id}
    )
    rows = result.fetchall()
    return [{"id": r[0], "title": r[1], "severity": r[2].lower() if r[2] else None,
             "status": r[3].lower() if r[3] else None,
             "requires_acknowledgment": r[2] in ['WARNING', 'CRITICAL'] and not r[4]}
            for r in rows]

async def _get_overdue_tasks(org_id: str, db) -> list:
    from sqlalchemy import text
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    result = await db.execute(
        text("""SELECT id, title, priority, due_date
                FROM tasks
                WHERE organization_id = :org_id
                AND status::text NOT IN ('COMPLETED', 'CANCELLED', 'completed', 'cancelled')
                AND due_date IS NOT NULL
                AND due_date < :now
                LIMIT 5"""),
        {"org_id": org_id, "now": now}
    )
    rows = result.fetchall()
    return [{"id": r[0], "title": r[1], "priority": r[2].lower() if r[2] else None,
             "due_date": r[3].isoformat() if r[3] else None}
            for r in rows]

def _alert_summary(a: StayAlert) -> dict:
    return {
        "id": a.id,
        "stay_id": a.stay_id,
        "dog_id": a.dog_id,
        "alert_message": a.alert_message,
        "severity": a.severity.value,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }

def _stay_summary(s: Stay, dog_name: str = None, room_name: str = None, household_name: str = None) -> dict:
    return {
        "stay_id": s.id,
        "dog_id": s.dog_id,
        "dog_name": dog_name,
        "room_id": s.room_id,
        "room_name": room_name,
        "household_name": household_name,
        "check_out_date": s.booking.check_out_date.isoformat() if hasattr(s, 'booking') and s.booking else None,
        "checked_in_at": s.checked_in_at.isoformat() if s.checked_in_at else None,
    }

async def _booking_summary(b: Booking, db) -> dict:
    bd_result = await db.execute(
        select(BookingDog).where(BookingDog.booking_id == b.id)
    )
    dog_ids = [bd.dog_id for bd in bd_result.scalars().all()]
    # Get dog names
    dog_names = []
    for dog_id in dog_ids:
        dog_result = await db.execute(select(DogORM).where(DogORM.id == dog_id))
        dog = dog_result.scalar_one_or_none()
        if dog:
            dog_names.append(dog.name)
    # Get household name
    from db_models import Household
    hh_result = await db.execute(select(Household).where(Household.id == b.household_id))
    hh = hh_result.scalar_one_or_none()
    return {
        "booking_id": b.id,
        "household_id": b.household_id,
        "household_name": hh.display_name if hh else None,
        "check_in_date": b.check_in_date.isoformat(),
        "check_out_date": b.check_out_date.isoformat(),
        "status": b.status.value,
        "dog_ids": dog_ids,
        "dog_names": dog_names,
    }


# ── CSV Exports ──────────────────────────────────────────────────────────────
from fastapi.responses import StreamingResponse
import csv, io
from datetime import date as date_type

@router.get("/export/bookings")
async def export_bookings(
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    conditions = ["b.organization_id = :org_id"]
    params = {"org_id": org_id}
    if start_date:
        conditions.append("b.check_in_date >= :start")
        params["start"] = start_date
    if end_date:
        conditions.append("b.check_in_date <= :end")
        params["end"] = end_date

    where = " AND ".join(conditions)
    result = await db.execute(text(f"""
        SELECT b.id, b.status, b.check_in_date, b.check_out_date, b.created_at,
               b.accommodation_type,
               h.display_name as household_name,
               STRING_AGG(d.name, ', ') as dogs
        FROM bookings b
        JOIN households h ON b.household_id = h.id
        LEFT JOIN booking_dogs_v2 bd ON bd.booking_id = b.id
        LEFT JOIN dogs d ON bd.dog_id = d.id
        WHERE {where}
        GROUP BY b.id, b.status, b.check_in_date, b.check_out_date, b.created_at,
                 b.accommodation_type, h.display_name
        ORDER BY b.check_in_date DESC
    """), params)
    rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Booking ID", "Status", "Check-In", "Check-Out", "Household", "Dogs", "Type", "Created"])
    for r in rows:
        writer.writerow([r.id, r.status, r.check_in_date, r.check_out_date,
                        r.household_name, r.dogs, r.accommodation_type, r.created_at])

    output.seek(0)
    filename = f"bookings_{date_type.today()}.csv"
    return StreamingResponse(iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/export/customers")
async def export_customers(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT h.id, h.display_name as name,
               (SELECT email FROM contacts WHERE household_id = h.id AND is_primary = TRUE LIMIT 1) as email,
               (SELECT phone FROM contacts WHERE household_id = h.id AND is_primary = TRUE LIMIT 1) as phone,
               h.created_at,
               (SELECT COUNT(*) FROM dogs WHERE household_id = h.id) as dog_count,
               (SELECT COUNT(*) FROM bookings WHERE household_id = h.id) as booking_count
        FROM households h
        WHERE h.organization_id = :org_id
        ORDER BY h.display_name
    """), {"org_id": current_user.organization_id})
    rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Email", "Phone", "Dogs", "Bookings", "Member Since"])
    for r in rows:
        writer.writerow([r.id, r.name, r.email, r.phone,
                        r.dog_count, r.booking_count, r.created_at])

    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=customers_{date_type.today()}.csv"})


@router.get("/export/dogs")
async def export_dogs(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("""
        SELECT d.id, d.name, d.breed, d.age, d.weight, d.gender, d.spay_neuter_status,
               d.medical_alert, d.escape_risk, d.behavioral_notes,
               h.display_name as household_name,
               bp.bite_history, bp.muzzle_required, bp.active_safety_alert
        FROM dogs d
        LEFT JOIN households h ON d.household_id = h.id
        LEFT JOIN behavior_profiles bp ON bp.dog_id = d.id
        WHERE d.organization_id = :org_id
        ORDER BY d.name
    """), {"org_id": current_user.organization_id})
    rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Breed", "Age", "Weight", "Gender", "Spay/Neuter",
                    "Medical Alert", "Escape Risk", "Bite History", "Muzzle Required",
                    "Safety Alert", "Household", "Behavioral Notes"])
    for r in rows:
        writer.writerow([r.id, r.name, r.breed, r.age, r.weight, r.gender,
                        r.spay_neuter_status, r.medical_alert, r.escape_risk,
                        r.bite_history, r.muzzle_required, r.active_safety_alert,
                        r.household_name, r.behavioral_notes])

    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=dogs_{date_type.today()}.csv"})


@router.get("/export/incidents")
async def export_incidents(
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    conditions = ["i.organization_id = :org_id"]
    params = {"org_id": current_user.organization_id}
    if start_date:
        conditions.append("i.occurred_at >= :start")
        params["start"] = start_date
    if end_date:
        conditions.append("i.occurred_at <= :end")
        params["end"] = end_date

    where = " AND ".join(conditions)
    result = await db.execute(text(f"""
        SELECT i.id, i.title, i.severity, i.status, i.occurred_at,
               i.description, i.immediate_action_taken, i.resolution_notes,
               d.name as dog_name, u.full_name as reported_by_name
        FROM incidents i
        LEFT JOIN dogs d ON i.dog_id = d.id
        LEFT JOIN users u ON i.reported_by = u.id
        WHERE {where}
        ORDER BY i.occurred_at DESC
    """), params)
    rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Severity", "Status", "Occurred At", "Dog",
                    "Reported By", "Description", "Immediate Action", "Resolution"])
    for r in rows:
        writer.writerow([r.id, r.title, r.severity, r.status, r.occurred_at,
                        r.dog_name, r.reported_by_name, r.description,
                        r.immediate_action_taken, r.resolution_notes])

    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=incidents_{date_type.today()}.csv"})
