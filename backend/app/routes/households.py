"""
Households and Contacts API
Handles customer household creation, retrieval, and contact management.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
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
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
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
    h = await _get_household_or_404(household_id, current_user.organization_id, db, current_user)
    contacts = await _get_contacts(household_id, db)
    result = _household_dict(h)
    result["contacts"] = [_contact_dict(c) for c in contacts]
    return result


# ── Create household ─────────────────────────────────────────────────────────

@router.post("")
async def create_household(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
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
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    h = await _get_household_or_404(household_id, current_user.organization_id, db, current_user)

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

@router.get("/{household_id}/contacts")
async def get_contacts(
    household_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_household_or_404(household_id, current_user.organization_id, db, current_user)
    contacts = await _get_contacts(household_id, db)
    return [_contact_dict(c) for c in contacts]


@router.post("/{household_id}/contacts")
async def add_contact(
    household_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    h = await _get_household_or_404(household_id, current_user.organization_id, db, current_user)

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
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
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

async def _get_household_or_404(household_id: str, org_id: str, db: AsyncSession, current_user: UserORM = None) -> Household:
    result = await db.execute(
        select(Household).where(
            Household.id == household_id,
            Household.organization_id == org_id
        )
    )
    h = result.scalar_one_or_none()
    if not h:
        raise HTTPException(status_code=404, detail="Household not found")
    if current_user is not None and current_user.role == UserRole.CUSTOMER:
        if household_id != current_user.household_id:
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

@router.post("/import-csv")
async def import_customers_csv(
    file: UploadFile = File(...),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Import customers (and optionally their dogs) from CSV file.

    Recognized columns: display_name, email, first_name, last_name, phone,
    dogs (optional -- one or more dog names separated by ';', e.g. "Rex;Bella").
    """
    import csv, io, uuid, logging
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    logger = logging.getLogger("k9cmd.import")

    content_bytes = await file.read()
    content_str = content_bytes.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content_str))

    created = 0
    skipped = 0
    errors = 0
    dogs_created = 0
    error_details = []

    for row_num, row in enumerate(reader, start=2):
        try:
            async with db.begin_nested():
                display_name = row.get('display_name', '').strip()
                email = row.get('email', '').strip().lower()
                first_name = row.get('first_name', '').strip()
                last_name = row.get('last_name', '').strip()
                phone = row.get('phone', '').strip()
                dogs_raw = row.get('dogs', '').strip()

                if not display_name:
                    display_name = f"{first_name} {last_name}".strip() or email

                if not display_name:
                    errors += 1
                    error_details.append({"row": row_num, "error": "missing display_name/first_name+last_name/email"})
                    continue

                existing = await db.execute(text(
                    "SELECT id FROM households WHERE organization_id = :org_id AND LOWER(display_name) = LOWER(:name)"
                ), {"org_id": current_user.organization_id, "name": display_name})
                if existing.fetchone():
                    skipped += 1
                    continue

                hh_id = str(uuid.uuid4())
                await db.execute(text("""
                    INSERT INTO households (id, organization_id, display_name, status)
                    VALUES (:id, :org_id, :name, 'ACTIVE')
                """), {"id": hh_id, "org_id": current_user.organization_id, "name": display_name})

                if first_name or email:
                    await db.execute(text("""
                        INSERT INTO contacts (id, organization_id, household_id, first_name, last_name, email, phone, is_primary, contact_type)
                        VALUES (:id, :org_id, :hh_id, :fn, :ln, :email, :phone, TRUE, 'PRIMARY')
                    """), {
                        "id": str(uuid.uuid4()),
                        "org_id": current_user.organization_id,
                        "hh_id": hh_id,
                        "fn": first_name or display_name,
                        "ln": last_name or '',
                        "email": email or None,
                        "phone": phone or None,
                    })

                if dogs_raw:
                    dog_names = [d.strip() for d in dogs_raw.split(';') if d.strip()]
                    for dog_name in dog_names:
                        dog_id = str(uuid.uuid4())
                        await db.execute(text("""
                            INSERT INTO dogs (id, organization_id, household_id, name, breed, meet_and_greet_status, boarding_eligible, daycare_eligible)
                            VALUES (:id, :org_id, :hh_id, :name, 'Unknown', 'required', FALSE, FALSE)
                        """), {
                            "id": dog_id, "org_id": current_user.organization_id,
                            "hh_id": hh_id, "name": dog_name,
                        })
                        await db.execute(text("""
                            INSERT INTO behavior_profiles (id, organization_id, dog_id, handlers_required)
                            VALUES (:id, :org_id, :dog_id, 1)
                        """), {
                            "id": str(uuid.uuid4()), "org_id": current_user.organization_id, "dog_id": dog_id,
                        })
                        dogs_created += 1

                created += 1
        except IntegrityError as e:
            errors += 1
            error_details.append({"row": row_num, "error": f"database constraint violation: {e.orig}"})
            logger.warning("CSV import row %s failed: %s", row_num, e)
        except Exception as e:
            errors += 1
            error_details.append({"row": row_num, "error": str(e)})
            logger.warning("CSV import row %s failed: %s", row_num, e)

    await db.commit()
    return {
        "created": created,
        "dogs_created": dogs_created,
        "skipped": skipped,
        "errors": errors,
        "error_details": error_details,
    }


@router.get("/{household_id}/notes")
async def get_household_notes(
    household_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT n.id, n.note_text, n.created_at, u.full_name as created_by_name
        FROM household_notes n
        LEFT JOIN users u ON n.created_by = u.id
        WHERE n.household_id = :hh_id AND n.organization_id = :org_id
        ORDER BY n.created_at DESC
    """), {"hh_id": household_id, "org_id": current_user.organization_id})
    rows = result.fetchall()
    return [{"id": r.id, "note_text": r.note_text,
             "created_by_name": r.created_by_name,
             "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


@router.post("/{household_id}/notes")
async def add_household_note(
    household_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    import uuid
    note_text = data.get("note_text", "").strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text required")
    await db.execute(text("""
        INSERT INTO household_notes (id, organization_id, household_id, note_text, created_by)
        VALUES (:id, :org_id, :hh_id, :note, :user_id)
    """), {
        "id": str(uuid.uuid4()),
        "org_id": current_user.organization_id,
        "hh_id": household_id,
        "note": note_text,
        "user_id": current_user.id
    })
    await db.commit()
    return {"created": True}


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
