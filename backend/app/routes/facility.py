"""
Facility Status API
Handles closure dates, holidays, and check-in window configuration.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from auth import get_current_user, require_role
from db_models import (
    FacilityStatus, FacilityStatusType,
    User as UserORM, UserRole
)
import uuid

router = APIRouter(prefix="/api/facility", tags=["facility"])


# ── List facility status dates ───────────────────────────────────────────────

@router.get("/status")
async def list_facility_status(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    q = select(FacilityStatus).where(FacilityStatus.organization_id == org_id)

    if start_date:
        q = q.where(FacilityStatus.date >= _parse_date(start_date))
    if end_date:
        q = q.where(FacilityStatus.date <= _parse_date(end_date))

    q = q.order_by(FacilityStatus.date)
    result = await db.execute(q)
    return [_status_dict(s) for s in result.scalars().all()]


# ── Set facility status (owner only) ─────────────────────────────────────────

@router.post("/status")
async def set_facility_status(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    date = _parse_date(data.get("date"))
    if not date:
        raise HTTPException(status_code=400, detail="date is required")

    status_str = data.get("status", "").upper()
    try:
        status = FacilityStatusType[status_str]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {[s.value for s in FacilityStatusType]}"
        )

    # Check if entry already exists for this date
    existing = (await db.execute(
        select(FacilityStatus).where(
            FacilityStatus.organization_id == org_id,
            FacilityStatus.date == date,
        )
    )).scalar_one_or_none()

    if existing:
        existing.status = status
        existing.reason = data.get("reason")
        existing.affects_bookings = data.get("affects_bookings", True)
        existing.set_by = current_user.id
        await db.commit()
        await db.refresh(existing)
        return _status_dict(existing)

    entry = FacilityStatus(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        date=date,
        status=status,
        reason=data.get("reason"),
        affects_bookings=data.get("affects_bookings", True),
        set_by=current_user.id,
        notes=data.get("notes"),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return _status_dict(entry)


# ── Delete facility status entry (owner only) ────────────────────────────────

@router.delete("/status/{status_id}")
async def delete_facility_status(
    status_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FacilityStatus).where(
            FacilityStatus.id == status_id,
            FacilityStatus.organization_id == current_user.organization_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Facility status entry not found")

    await db.delete(entry)
    await db.commit()
    return {"deleted": True}


# ── Check if date range has closures ─────────────────────────────────────────

@router.get("/status/check")
async def check_date_range(
    start: str = Query(...),
    end: str = Query(...),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    start_dt = _parse_date(start)
    end_dt = _parse_date(end)

    result = await db.execute(
        select(FacilityStatus).where(
            FacilityStatus.organization_id == org_id,
            FacilityStatus.date >= start_dt,
            FacilityStatus.date <= end_dt,
            FacilityStatus.status != FacilityStatusType.OPEN,
            FacilityStatus.affects_bookings == True,
        ).order_by(FacilityStatus.date)
    )
    closures = result.scalars().all()

    return {
        "has_closures": len(closures) > 0,
        "closures": [_status_dict(c) for c in closures],
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

def _status_dict(s: FacilityStatus) -> dict:
    return {
        "id": s.id,
        "date": s.date.isoformat() if s.date else None,
        "status": s.status.value if s.status else None,
        "reason": s.reason,
        "affects_bookings": s.affects_bookings,
        "notes": s.notes,
        "set_by": s.set_by,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }

# ── Room Management ──────────────────────────────────────────────────────────

@router.get("/rooms")
async def list_rooms(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from db_models import Room
    from sqlalchemy import select
    result = await db.execute(
        select(Room).where(Room.organization_id == current_user.organization_id)
        .order_by(Room.sort_order)
    )
    return [_room_dict(r) for r in result.scalars().all()]


@router.patch("/rooms/{room_id}")
async def update_room(
    room_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    from db_models import Room
    from sqlalchemy import select
    result = await db.execute(
        select(Room).where(
            Room.id == room_id,
            Room.organization_id == current_user.organization_id
        )
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    allowed = ["name", "max_dogs", "adjacency_group", "is_active",
               "is_out_of_service", "out_of_service_reason", "notes", "sort_order"]
    for field in allowed:
        if field in data:
            setattr(room, field, data[field])

    await db.commit()
    await db.refresh(room)
    return _room_dict(room)


@router.post("/rooms")
async def create_room(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    from db_models import Room
    import uuid
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    room = Room(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        name=name,
        room_type=data.get("room_type", "room"),
        max_dogs=data.get("max_dogs", 3),
        adjacency_group=data.get("adjacency_group"),
        is_active=True,
        is_out_of_service=False,
        sort_order=data.get("sort_order", 99),
        notes=data.get("notes"),
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return _room_dict(room)


def _room_dict(r) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "room_type": getattr(r, "room_type", "room"),
        "max_dogs": r.max_dogs,
        "adjacency_group": r.adjacency_group,
        "is_active": r.is_active,
        "is_out_of_service": r.is_out_of_service,
        "out_of_service_reason": r.out_of_service_reason,
        "notes": r.notes,
        "sort_order": r.sort_order,
    }

# ── Room Management ──────────────────────────────────────────────────────────

@router.get("/rooms")
async def list_rooms(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from db_models import Room
    from sqlalchemy import select
    result = await db.execute(
        select(Room).where(Room.organization_id == current_user.organization_id)
        .order_by(Room.sort_order)
    )
    return [_room_dict(r) for r in result.scalars().all()]


@router.patch("/rooms/{room_id}")
async def update_room(
    room_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    from db_models import Room
    from sqlalchemy import select
    result = await db.execute(
        select(Room).where(
            Room.id == room_id,
            Room.organization_id == current_user.organization_id
        )
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    allowed = ["name", "max_dogs", "adjacency_group", "is_active",
               "is_out_of_service", "out_of_service_reason", "notes", "sort_order"]
    for field in allowed:
        if field in data:
            setattr(room, field, data[field])

    await db.commit()
    await db.refresh(room)
    return _room_dict(room)


@router.post("/rooms")
async def create_room(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    from db_models import Room
    import uuid
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    room = Room(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        name=name,
        room_type=data.get("room_type", "room"),
        max_dogs=data.get("max_dogs", 3),
        adjacency_group=data.get("adjacency_group"),
        is_active=True,
        is_out_of_service=False,
        sort_order=data.get("sort_order", 99),
        notes=data.get("notes"),
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return _room_dict(room)


def _room_dict(r) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "room_type": getattr(r, "room_type", "room"),
        "max_dogs": r.max_dogs,
        "adjacency_group": r.adjacency_group,
        "is_active": r.is_active,
        "is_out_of_service": r.is_out_of_service,
        "out_of_service_reason": r.out_of_service_reason,
        "notes": r.notes,
        "sort_order": r.sort_order,
    }
