"""
Households and Contacts API
Handles customer household creation, retrieval, and contact management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import Optional
from database import get_db
from auth import get_current_user, require_role
from db_models import (
    Household, Contact, User as UserORM,
    HouseholdStatus, ContactType, UserRole
)
import uuid

router = APIRouter(prefix="/api/households", tags=["households"])


# ── List households ──────────────────────────────────────────────────────────

@router.get("")
async def list_households(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="No organization assigned")

    q = select(Household).where(Household.organization_id == org_id)

    if status:
        q = q.where(Household.status == status.upper())
    else:
        q = q.where(Household.status == HouseholdStatus.ACTIVE)

    if search:
        q = q.where(Household.display_name.ilike(f"%{search}%"))

    q = q.order_by(Household.display_name).offset(skip).limit(limit)
    result = await db.execute(q)
    households = result.scalars().all()

    return [_household_dict(h) for h in households]


# ── Get single household ─────────────────────────────────────────────────────

@router.get("/{household_id}")
async def get_household(
    household_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    h = await _get_household_or_404(household_id, current_user.organization_id, db)
    contacts = await _get_contacts(household_id, db)
    result = _household_dict(h)
    result["contacts"] = [_contact_dict(c) for c in contacts]
    return result


# ── Create household ─────────────────────────────────────────────────────────

@router.post("")
async def create_household(
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="No organization assigned")

    display_name = data.get("display_name", "").strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="display_name is required")

    # Duplicate check on display name
    existing = await db.execute(
        select(Household).where(
            Household.organization_id == org_id,
            Household.display_name.ilike(display_name),
            Household.status == HouseholdStatus.ACTIVE
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"An active household named '{display_name}' already exists"
        )

    household = Household(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        display_name=display_name,
        preferred_contact_method=data.get("preferred_contact_method"),
        general_notes=data.get("general_notes"),
        referral_source=data.get("referral_source"),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(household)
    await db.flush()

    # Create primary contact if provided
    contact_data = data.get("primary_contact")
    if contact_data:
        contact = Contact(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            household_id=household.id,
            first_name=contact_data.get("first_name", ""),
            last_name=contact_data.get("last_name"),
            contact_type=ContactType.PRIMARY,
            phone=contact_data.get("phone"),
            email=contact_data.get("email"),
            is_primary=True,
            is_emergency_contact=contact_data.get("is_emergency_contact", False),
            is_authorized_pickup=contact_data.get("is_authorized_pickup", True),
            relationship_to_household=contact_data.get("relationship_to_household"),
        )
        db.add(contact)

    await db.commit()
    await db.refresh(household)
    return _household_dict(household)


# ── Update household ─────────────────────────────────────────────────────────

@router.patch("/{household_id}")
async def update_household(
    household_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    h = await _get_household_or_404(household_id, current_user.organization_id, db)

    allowed = ["display_name", "preferred_contact_method", "general_notes",
               "referral_source", "status", "meet_and_greet_status"]
    for field in allowed:
        if field in data:
            setattr(h, field, data[field])
    h.updated_by = current_user.id

    await db.commit()
    await db.refresh(h)
    return _household_dict(h)


# ── Add contact to household ─────────────────────────────────────────────────

@router.post("/{household_id}/contacts")
async def add_contact(
    household_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    h = await _get_household_or_404(household_id, current_user.organization_id, db)

    first_name = data.get("first_name", "").strip()
    if not first_name:
        raise HTTPException(status_code=400, detail="first_name is required")

    contact = Contact(
        id=str(uuid.uuid4()),
        organization_id=h.organization_id,
        household_id=household_id,
        first_name=first_name,
        last_name=data.get("last_name"),
        contact_type=data.get("contact_type", ContactType.PRIMARY),
        phone=data.get("phone"),
        email=data.get("email"),
        is_primary=data.get("is_primary", False),
        is_emergency_contact=data.get("is_emergency_contact", False),
        is_authorized_pickup=data.get("is_authorized_pickup", False),
        relationship_to_household=data.get("relationship_to_household"),
        notes=data.get("notes"),
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return _contact_dict(contact)


# ── Search (duplicate detection) ─────────────────────────────────────────────

@router.get("/search/duplicates")
async def check_duplicates(
    name: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check for likely duplicate households before creating a new one."""
    org_id = current_user.organization_id
    matches = []

    if name:
        result = await db.execute(
            select(Household).where(
                Household.organization_id == org_id,
                Household.display_name.ilike(f"%{name}%")
            ).limit(5)
        )
        for h in result.scalars().all():
            matches.append({"type": "name_match", "household": _household_dict(h)})

    if email or phone:
        q = select(Contact).where(Contact.organization_id == org_id)
        if email:
            q = q.where(Contact.email.ilike(email))
        if phone:
            q = q.where(Contact.phone == phone)
        result = await db.execute(q.limit(5))
        for c in result.scalars().all():
            h_result = await db.execute(
                select(Household).where(Household.id == c.household_id)
            )
            h = h_result.scalar_one_or_none()
            if h:
                matches.append({"type": "contact_match", "household": _household_dict(h), "matched_contact": _contact_dict(c)})

    return {"matches": matches}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_household_or_404(household_id: str, org_id: str, db: AsyncSession) -> Household:
    result = await db.execute(
        select(Household).where(
            Household.id == household_id,
            Household.organization_id == org_id
        )
    )
    h = result.scalar_one_or_none()
    if not h:
        raise HTTPException(status_code=404, detail="Household not found")
    return h

async def _get_contacts(household_id: str, db: AsyncSession):
    result = await db.execute(
        select(Contact).where(Contact.household_id == household_id)
        .order_by(Contact.is_primary.desc(), Contact.first_name)
    )
    return result.scalars().all()

def _household_dict(h: Household) -> dict:
    return {
        "id": h.id,
        "display_name": h.display_name,
        "status": h.status.value if h.status else "active",
        "preferred_contact_method": h.preferred_contact_method,
        "general_notes": h.general_notes,
        "referral_source": h.referral_source,
        "meet_and_greet_status": h.meet_and_greet_status.value if h.meet_and_greet_status else "required",
        "created_at": h.created_at.isoformat() if h.created_at else None,
        "updated_at": h.updated_at.isoformat() if h.updated_at else None,
    }

def _contact_dict(c: Contact) -> dict:
    return {
        "id": c.id,
        "household_id": c.household_id,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "contact_type": c.contact_type.value if c.contact_type else "primary",
        "phone": c.phone,
        "email": c.email,
        "is_primary": c.is_primary,
        "is_emergency_contact": c.is_emergency_contact,
        "is_authorized_pickup": c.is_authorized_pickup,
        "relationship_to_household": c.relationship_to_household,
        "notes": c.notes,
    }
