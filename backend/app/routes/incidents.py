"""
Incidents API - 4-tier severity with owner acknowledgment for warning/critical.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from auth import get_current_user, require_role
from db_models import Incident, IncidentSeverity, IncidentStatus, User as UserORM, UserRole
import uuid

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("")
async def list_incidents(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    dog_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    conditions = ["organization_id = :org_id"]
    params = {"org_id": org_id, "skip": skip, "limit": limit}

    if status:
        conditions.append("status::text = :status")
        params["status"] = status.upper()
    else:
        conditions.append("status::text NOT IN ('CLOSED')")
    if severity:
        conditions.append("severity::text = :severity")
        params["severity"] = severity.upper()
    if dog_id:
        conditions.append("dog_id = :dog_id")
        params["dog_id"] = dog_id

    where = " AND ".join(conditions)
    result = await db.execute(
        text(f"SELECT id FROM incidents WHERE {where} ORDER BY occurred_at DESC NULLS LAST OFFSET :skip LIMIT :limit"),
        params
    )
    ids = [r[0] for r in result.fetchall()]
    if not ids:
        return []
    result2 = await db.execute(
        select(Incident).where(Incident.id.in_(ids)).order_by(Incident.occurred_at.desc())
    )
    return [_incident_dict(i) for i in result2.scalars().all()]


@router.get("/unacknowledged")
async def get_unacknowledged(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""SELECT id FROM incidents
                WHERE organization_id = :org_id
                AND severity::text IN ('WARNING','CRITICAL')
                AND acknowledged_at IS NULL
                AND status::text != 'CLOSED'
                ORDER BY occurred_at DESC"""),
        {"org_id": current_user.organization_id}
    )
    ids = [r[0] for r in result.fetchall()]
    if not ids:
        return []
    result2 = await db.execute(select(Incident).where(Incident.id.in_(ids)))
    return [_incident_dict(i) for i in result2.scalars().all()]


@router.post("")
async def create_incident(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    severity_str = data.get("severity", "").upper()

    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    if not description:
        raise HTTPException(status_code=400, detail="description is required")
    try:
        severity = IncidentSeverity[severity_str]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid severity. Must be: info, caution, warning, critical")

    occurred_at = _parse_date(data.get("occurred_at")) or datetime.now(timezone.utc)

    incident = Incident(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        title=title,
        description=description,
        severity=severity,
        status="OPEN",
        dog_id=data.get("dog_id"),
        stay_id=data.get("stay_id"),
        reported_by=current_user.id,
        assigned_to=data.get("assigned_to"),
        occurred_at=occurred_at,
        location_description=data.get("location_description"),
        witness_names=data.get("witness_names"),
        immediate_action_taken=data.get("immediate_action_taken"),
        follow_up_required=data.get("follow_up_required", False),
        follow_up_notes=data.get("follow_up_notes"),
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return _incident_dict(incident)


@router.get("/{incident_id}")
async def get_incident(
    incident_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    incident = await _get_incident_or_404(incident_id, current_user.organization_id, db)
    return _incident_dict(incident)


@router.patch("/{incident_id}")
async def update_incident(
    incident_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    incident = await _get_incident_or_404(incident_id, current_user.organization_id, db)
    allowed = ["title", "description", "assigned_to", "follow_up_required",
               "follow_up_notes", "immediate_action_taken", "witness_names", "location_description"]
    for field in allowed:
        if field in data:
            setattr(incident, field, data[field])
    await db.commit()
    await db.refresh(incident)
    return _incident_dict(incident)


@router.post("/{incident_id}/acknowledge")
async def acknowledge_incident(
    incident_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    incident = await _get_incident_or_404(incident_id, current_user.organization_id, db)
    if incident.acknowledged_at:
        raise HTTPException(status_code=400, detail="Already acknowledged")
    incident.acknowledged_by = current_user.id
    incident.acknowledged_at = datetime.now(timezone.utc)
    incident.status = "ACKNOWLEDGED"
    await db.commit()
    await db.refresh(incident)
    return _incident_dict(incident)


@router.post("/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    incident = await _get_incident_or_404(incident_id, current_user.organization_id, db)
    if incident.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Incident is already closed")
    incident.status = "RESOLVED"
    incident.resolved_by = current_user.id
    incident.resolved_at = datetime.now(timezone.utc)
    incident.resolution_notes = data.get("resolution_notes")
    await db.commit()
    await db.refresh(incident)
    return _incident_dict(incident)


@router.post("/{incident_id}/close")
async def close_incident(
    incident_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    incident = await _get_incident_or_404(incident_id, current_user.organization_id, db)
    incident.status = "CLOSED"
    await db.commit()
    await db.refresh(incident)
    return _incident_dict(incident)


async def _get_incident_or_404(incident_id: str, org_id: str, db: AsyncSession) -> Incident:
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id, Incident.organization_id == org_id)
    )
    i = result.scalar_one_or_none()
    if not i:
        raise HTTPException(status_code=404, detail="Incident not found")
    return i


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _incident_dict(i: Incident) -> dict:
    sev = i.severity.value if hasattr(i.severity, 'value') else str(i.severity)
    status = i.status.value if hasattr(i.status, 'value') else str(i.status)
    return {
        "id": i.id,
        "title": i.title,
        "description": i.description,
        "severity": sev.lower(),
        "status": status.lower(),
        "dog_id": i.dog_id,
        "stay_id": i.stay_id,
        "reported_by": i.reported_by,
        "assigned_to": i.assigned_to,
        "occurred_at": i.occurred_at.isoformat() if i.occurred_at else None,
        "location_description": i.location_description,
        "witness_names": i.witness_names,
        "immediate_action_taken": i.immediate_action_taken,
        "follow_up_required": i.follow_up_required,
        "follow_up_notes": i.follow_up_notes,
        "acknowledged_by": i.acknowledged_by,
        "acknowledged_at": i.acknowledged_at.isoformat() if i.acknowledged_at else None,
        "resolved_by": i.resolved_by,
        "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
        "resolution_notes": i.resolution_notes,
        "created_at": i.created_at.isoformat() if i.created_at else None,
        "requires_acknowledgment": sev.upper() in ['WARNING', 'CRITICAL'] and not i.acknowledged_at,
    }


@router.get("/{incident_id}/notes")
async def get_incident_notes(
    incident_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    await _get_incident_or_404(incident_id, current_user.organization_id, db)
    result = await db.execute(text("""
        SELECT n.id, n.note_text, n.photo_keys, n.created_at,
               u.full_name as created_by_name
        FROM incident_notes n
        LEFT JOIN users u ON n.created_by = u.id
        WHERE n.incident_id = :incident_id
        ORDER BY n.created_at DESC
    """), {"incident_id": incident_id})
    rows = result.fetchall()
    from app.storage import get_public_url, BUCKET_INCIDENTS
    notes = []
    for r in rows:
        keys = r.photo_keys or []
        notes.append({
            "id": r.id,
            "note_text": r.note_text,
            "photo_keys": keys,
            "photo_urls": [get_public_url(BUCKET_INCIDENTS, k) for k in keys if k],
            "created_by_name": r.created_by_name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return notes


@router.post("/{incident_id}/notes")
async def add_incident_note(
    incident_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    import uuid, json
    from sqlalchemy import text
    await _get_incident_or_404(incident_id, current_user.organization_id, db)
    note_text = data.get("note_text", "").strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text required")
    photo_keys = data.get("photo_keys", [])
    await db.execute(text("""
        INSERT INTO incident_notes (id, organization_id, incident_id, note_text, photo_keys, created_by)
        VALUES (:id, :org_id, :incident_id, :note_text, :photo_keys, :created_by)
    """), {
        "id": str(uuid.uuid4()),
        "org_id": current_user.organization_id,
        "incident_id": incident_id,
        "note_text": note_text,
        "photo_keys": json.dumps(photo_keys),
        "created_by": current_user.id,
    })
    await db.commit()
    return {"created": True}
