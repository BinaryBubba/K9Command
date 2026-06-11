"""
Vaccination Records API
Handles vaccination record creation, verification workflow, and expiry tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timezone, timedelta
from database import get_db
from auth import get_current_user, require_role
from db_models import (
    VaccinationRecord, VaccinationStatus, Dog as DogORM,
    User as UserORM, UserRole
)
import uuid

router = APIRouter(prefix="/api/vaccinations", tags=["vaccinations"])

EXPIRY_WARNING_DAYS = 30


# ── List vaccinations for a dog ──────────────────────────────────────────────

@router.get("/dog/{dog_id}")
async def list_dog_vaccinations(
    dog_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_dog_access(dog_id, current_user.organization_id, db)
    result = await db.execute(
        select(VaccinationRecord)
        .where(VaccinationRecord.dog_id == dog_id)
        .order_by(VaccinationRecord.expiration_date.desc())
    )
    records = result.scalars().all()
    return [_vax_dict(v) for v in records]


# ── Add vaccination record ───────────────────────────────────────────────────

@router.post("/dog/{dog_id}")
async def add_vaccination(
    dog_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_dog_access(dog_id, current_user.organization_id, db)

    vax_type = data.get("vaccination_type", "").strip()
    if not vax_type:
        raise HTTPException(status_code=400, detail="vaccination_type is required")

    record = VaccinationRecord(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        dog_id=dog_id,
        vaccination_type=vax_type,
        administration_date=_parse_date(data.get("administration_date")),
        expiration_date=_parse_date(data.get("expiration_date")),
        provider=data.get("provider"),
        verification_status=VaccinationStatus.PENDING,
        document_path=data.get("document_path"),
        uploaded_by=current_user.id,
        notes=data.get("notes"),
    )
    # If staff is submitting on behalf of customer, auto-verify
    if current_user.role in ["admin", "staff"] and data.get("auto_verify"):
        record.verification_status = VaccinationStatus.VERIFIED
        record.verified_by = current_user.id
        from datetime import datetime, timezone
        record.verified_at = datetime.now(timezone.utc)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _vax_dict(record)


# ── Verify vaccination (owner only) ─────────────────────────────────────────

@router.post("/{record_id}/verify")
async def verify_vaccination(
    record_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    record = await _get_record_or_404(record_id, current_user.organization_id, db)

    if record.verification_status == VaccinationStatus.VERIFIED:
        raise HTTPException(status_code=400, detail="Already verified")

    record.verification_status = VaccinationStatus.VERIFIED
    record.verified_by = current_user.id
    record.verified_at = datetime.now(timezone.utc)
    record.rejection_reason = None

    await db.commit()
    await db.refresh(record)
    return _vax_dict(record)


# ── Reject vaccination (owner only) ─────────────────────────────────────────

@router.post("/{record_id}/reject")
async def reject_vaccination(
    record_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    record = await _get_record_or_404(record_id, current_user.organization_id, db)

    reason = data.get("reason", "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="reason is required when rejecting")

    record.verification_status = VaccinationStatus.REJECTED
    record.rejection_reason = reason
    record.verified_by = current_user.id
    record.verified_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(record)
    return _vax_dict(record)


# ── Get vaccination status summary for a dog ────────────────────────────────

@router.get("/dog/{dog_id}/status")
async def get_vaccination_status(
    dog_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_dog_access(dog_id, current_user.organization_id, db)

    result = await db.execute(
        select(VaccinationRecord).where(VaccinationRecord.dog_id == dog_id)
    )
    records = result.scalars().all()

    now = datetime.now(timezone.utc)
    warning_threshold = now + timedelta(days=EXPIRY_WARNING_DAYS)
    issues = []

    for r in records:
        if r.verification_status == VaccinationStatus.REJECTED:
            issues.append({"type": "rejected", "vaccination_type": r.vaccination_type,
                          "message": f"{r.vaccination_type} rejected: {r.rejection_reason}"})
        elif r.verification_status == VaccinationStatus.PENDING:
            issues.append({"type": "pending", "vaccination_type": r.vaccination_type,
                          "message": f"{r.vaccination_type} pending verification"})
        elif r.expiration_date and r.expiration_date < now:
            issues.append({"type": "expired", "vaccination_type": r.vaccination_type,
                          "message": f"{r.vaccination_type} expired on {r.expiration_date.date()}"})
        elif r.expiration_date and r.expiration_date < warning_threshold:
            issues.append({"type": "expiring_soon", "vaccination_type": r.vaccination_type,
                          "message": f"{r.vaccination_type} expires on {r.expiration_date.date()}"})

    return {
        "dog_id": dog_id,
        "total_records": len(records),
        "issues": issues,
        "has_issues": len(issues) > 0,
        "records": [_vax_dict(r) for r in records],
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _verify_dog_access(dog_id: str, org_id: str, db: AsyncSession):
    result = await db.execute(
        select(DogORM).where(DogORM.id == dog_id, DogORM.organization_id == org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Dog not found")

async def _get_record_or_404(record_id: str, org_id: str, db: AsyncSession) -> VaccinationRecord:
    result = await db.execute(
        select(VaccinationRecord).where(
            VaccinationRecord.id == record_id,
            VaccinationRecord.organization_id == org_id
        )
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Vaccination record not found")
    return r

def _parse_date(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
    except Exception:
        return None

def _vax_dict(v: VaccinationRecord) -> dict:
    doc_url = None
    if v.document_path:
        try:
            from app.storage import get_presigned_url, get_public_url, BUCKET_VACCINATIONS
            doc_url = get_public_url(BUCKET_VACCINATIONS, v.document_path)
        except Exception:
            pass
    return {
        "id": v.id,
        "dog_id": v.dog_id,
        "vaccination_type": v.vaccination_type,
        "administration_date": v.administration_date.isoformat() if v.administration_date else None,
        "expiration_date": v.expiration_date.isoformat() if v.expiration_date else None,
        "provider": v.provider,
        "verification_status": v.verification_status.value,
        "rejection_reason": v.rejection_reason,
        "document_path": v.document_path,
        "document_url": doc_url,
        "uploaded_by": v.uploaded_by,
        "verified_by": v.verified_by,
        "verified_at": v.verified_at.isoformat() if v.verified_at else None,
        "notes": v.notes,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }

from typing import Optional
