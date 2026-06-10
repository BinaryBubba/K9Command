"""
Daily Command Dashboard API
Returns prioritized operational data for the daily dashboard.
Priority order per spec Section 7.5.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta
from database import get_db
from auth import get_current_user
from db_models import (
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
            departing_soon.append(stay)

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
        "departing_soon": [_stay_summary(s) for s in departing_soon],

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
                AND status::text NOT IN ('CLOSED', 'RESOLVED')
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

def _stay_summary(s: Stay) -> dict:
    return {
        "stay_id": s.id,
        "dog_id": s.dog_id,
        "room_id": s.room_id,
        "checked_in_at": s.checked_in_at.isoformat() if s.checked_in_at else None,
    }

async def _booking_summary(b: Booking, db) -> dict:
    bd_result = await db.execute(
        select(BookingDog).where(BookingDog.booking_id == b.id)
    )
    dog_ids = [bd.dog_id for bd in bd_result.scalars().all()]
    return {
        "booking_id": b.id,
        "household_id": b.household_id,
        "check_in_date": b.check_in_date.isoformat(),
        "check_out_date": b.check_out_date.isoformat(),
        "status": b.status.value,
        "dog_ids": dog_ids,
    }
