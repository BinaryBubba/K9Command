"""
Users/Staff management API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from auth import get_current_user, require_role, hash_password
from db_models import User as UserORM, UserRole
import uuid, secrets, string

router = APIRouter(prefix="/api/users", tags=["users"])


def _get_avatar_url(key):
    if not key:
        return None
    try:
        from app.storage import get_public_url, BUCKET_DOGS
        return get_public_url(BUCKET_DOGS, key)
    except Exception:
        return None

def _user_dict(u: UserORM) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "phone": u.phone,
        "role": u.role.value if hasattr(u.role, 'value') else u.role,
        "is_active": u.is_active,
        "is_owner": u.is_owner,
        "organization_id": u.organization_id,
        "emergency_contact_name": u.emergency_contact_name,
        "emergency_contact_phone": u.emergency_contact_phone,
        "notes": u.notes,
        "hire_date": u.hire_date,
        "address": u.address,
        "birthday": u.birthday,
        "avatar_key": u.avatar_key,
        "avatar_url": _get_avatar_url(u.avatar_key),
        "first_name": u.first_name,
        "last_name": u.last_name,
        "manager_pin": u.manager_pin,
        "connecteam_user_id": u.connecteam_user_id,
        "household_id": u.household_id,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("")
async def list_users(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(UserORM).where(UserORM.organization_id == current_user.organization_id)
    if role:
        q = q.where(UserORM.role == role.lower())
    if is_active is not None:
        q = q.where(UserORM.is_active == is_active)
    q = q.order_by(UserORM.full_name).limit(limit)
    result = await db.execute(q)
    return [_user_dict(u) for u in result.scalars().all()]


@router.get("/me")
async def get_me(current_user: UserORM = Depends(get_current_user)):
    return _user_dict(current_user)


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user_or_404(user_id, current_user.organization_id, db)
    return _user_dict(user)


@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user_or_404(user_id, current_user.organization_id, db)
    is_admin = current_user.role in [UserRole.ADMIN, 'admin', UserRole.ADMIN.value]
    is_self = current_user.id == user_id

    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Fields anyone can update on themselves
    self_fields = ["full_name", "first_name", "last_name", "phone", "address", "birthday",
                   "emergency_contact_name", "emergency_contact_phone", "avatar_key", "manager_pin"]
    # Admin-only fields
    admin_fields = ["role", "is_active", "notes", "hire_date", "address", "birthday", "connecteam_user_id"]

    for field in self_fields:
        if field in data:
            setattr(user, field, data[field])

    if is_admin:
        for field in admin_fields:
            if field in data:
                if field == "role":
                    setattr(user, field, data[field].lower())
                else:
                    setattr(user, field, data[field])

    await db.commit()
    await db.refresh(user)
    return _user_dict(user)


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user_or_404(user_id, current_user.organization_id, db)

    # Generate temp password
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    temp_password = temp_password[0].upper() + temp_password[1:] + "!"

    user.hashed_password = hash_password(temp_password)
    await db.commit()

    return {
        "message": f"Password reset for {user.full_name}",
        "temp_password": temp_password,
        "note": "Share this with the staff member — they should change it on next login"
    }


@router.get("/{user_id}/activity")
async def get_user_activity(
    user_id: str,
    limit: int = Query(20),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_or_404(user_id, current_user.organization_id, db)
    is_admin = current_user.role in [UserRole.ADMIN, 'admin', UserRole.ADMIN.value]
    is_self = current_user.id == user_id
    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get check-ins performed by this staff member
    checkins = await db.execute(text("""
        SELECT s.id, s.checked_in_at, d.name as dog_name, r.name as room_name,
               'check_in' as action_type
        FROM stays s
        JOIN dogs d ON s.dog_id = d.id
        LEFT JOIN rooms r ON s.room_id = r.id
        WHERE s.checked_in_by = :user_id
        AND s.checked_in_at IS NOT NULL
        ORDER BY s.checked_in_at DESC LIMIT :limit
    """), {"user_id": user_id, "limit": limit})

    checkouts = await db.execute(text("""
        SELECT s.id, s.checked_out_at as action_at, d.name as dog_name,
               NULL as room_name, 'check_out' as action_type
        FROM stays s
        JOIN dogs d ON s.dog_id = d.id
        WHERE s.checked_out_by = :user_id
        AND s.checked_out_at IS NOT NULL
        ORDER BY s.checked_out_at DESC LIMIT :limit
    """), {"user_id": user_id, "limit": limit})

    activity = []
    for row in checkins.fetchall():
        activity.append({
            "type": "check_in",
            "dog_name": row[2],
            "room_name": row[3],
            "timestamp": row[1].isoformat() if row[1] else None,
        })
    for row in checkouts.fetchall():
        activity.append({
            "type": "check_out",
            "dog_name": row[2],
            "timestamp": row[1].isoformat() if row[1] else None,
        })

    activity.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    return activity[:limit]


@router.post("")
async def create_user(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    email = data.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    existing = await db.execute(select(UserORM).where(UserORM.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already in use")

    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    temp_password = temp_password[0].upper() + temp_password[1:] + "!"

    user = UserORM(
        id=str(uuid.uuid4()),
        email=email,
        full_name=data.get("full_name", "").strip(),
        hashed_password=hash_password(temp_password),
        role=data.get("role", "STAFF").upper(),
        phone=data.get("phone"),
        organization_id=current_user.organization_id,
        is_active=True,
        is_owner=False,
        hire_date=data.get("hire_date"),
        notes=data.get("notes"),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        address=data.get("address"),
        birthday=data.get("birthday"),
        emergency_contact_name=data.get("emergency_contact_name"),
        emergency_contact_phone=data.get("emergency_contact_phone"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    result = _user_dict(user)
    result["temp_password"] = temp_password
    return result


async def _get_user_or_404(user_id: str, org_id: str, db: AsyncSession) -> UserORM:
    result = await db.execute(
        select(UserORM).where(
            UserORM.id == user_id,
            UserORM.organization_id == org_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/verify-pin")
async def verify_manager_pin(
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a manager/admin PIN for override actions."""
    pin = data.get("pin", "").strip()
    user_id = data.get("user_id")  # optional - verify specific user's pin
    
    if user_id:
        result = await db.execute(
            select(UserORM).where(
                UserORM.id == user_id,
                UserORM.organization_id == current_user.organization_id,
            )
        )
        user = result.scalar_one_or_none()
    else:
        # Verify against any manager/admin in the org
        result = await db.execute(
            text("""SELECT id FROM users 
                    WHERE organization_id = :org_id 
                    AND manager_pin = :pin 
                    AND LOWER(role::text) IN ('manager', 'admin')
                    AND is_active = TRUE
                    LIMIT 1"""),
            {"org_id": current_user.organization_id, "pin": pin}
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=403, detail="Invalid PIN")
        user_result = await db.execute(select(UserORM).where(UserORM.id == row[0]))
        user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=403, detail="Invalid PIN")
    
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return {"verified": True, "user_name": user.full_name, "role": role}


@router.get("/org/settings")
async def get_org_settings(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT name, contact_phone, contact_email, contact_address
        FROM organizations WHERE id = :org_id
    """), {"org_id": current_user.organization_id})
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Org not found")
    return {"name": row.name, "contact_phone": row.contact_phone,
            "contact_email": row.contact_email, "contact_address": row.contact_address}


@router.patch("/org/settings")
async def update_org_settings(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    await db.execute(text("""
        UPDATE organizations SET
            contact_phone = COALESCE(:phone, contact_phone),
            contact_email = COALESCE(:email, contact_email),
            contact_address = COALESCE(:address, contact_address)
        WHERE id = :org_id
    """), {"phone": data.get("contact_phone"), "email": data.get("contact_email"),
           "address": data.get("contact_address"), "org_id": current_user.organization_id})
    await db.commit()
    return {"updated": True}


@router.post("/shift/clock-in")
async def clock_in(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark current user as on shift."""
    from datetime import datetime, timezone
    from sqlalchemy import text
    await db.execute(text("""
        UPDATE users SET is_on_shift = TRUE, shift_started_at = NOW()
        WHERE id = :user_id
    """), {"user_id": current_user.id})
    await db.commit()
    return {"on_shift": True, "started_at": datetime.now(timezone.utc).isoformat()}


@router.post("/shift/clock-out")
async def clock_out(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark current user as off shift."""
    from sqlalchemy import text
    await db.execute(text("""
        UPDATE users SET is_on_shift = FALSE, shift_started_at = NULL
        WHERE id = :user_id
    """), {"user_id": current_user.id})
    await db.commit()
    return {"on_shift": False}


@router.get("/shift/active")
async def get_active_staff(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all staff currently on shift."""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT id, full_name, role, shift_started_at, avatar_key
        FROM users
        WHERE organization_id = :org_id
        AND is_on_shift = TRUE
        AND is_active = TRUE
        ORDER BY shift_started_at ASC
    """), {"org_id": current_user.organization_id})
    rows = result.fetchall()
    return [{
        "id": r.id,
        "full_name": r.full_name,
        "role": r.role,
        "shift_started_at": r.shift_started_at.isoformat() if r.shift_started_at else None,
    } for r in rows]
