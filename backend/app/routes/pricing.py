"""
Pricing / service rates. Admins edit them (Settings); every logged-in user can
read the active ones. The welcome email builds its rate list from here, so a
price change in Settings changes the email too.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import html as _html
import uuid

from database import get_db
from auth import get_current_user, require_role
from db_models import User as UserORM, UserRole

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


def _row(r) -> dict:
    return {"id": r.id, "category": r.category, "label": r.label, "value": r.value,
            "sort_order": r.sort_order, "is_active": r.is_active}


def _clean(v, field: str, max_len: int):
    v = str(v if v is not None else "").strip()
    if not v:
        raise HTTPException(status_code=400, detail=f"{field} cannot be empty")
    if len(v) > max_len:
        raise HTTPException(status_code=400, detail=f"{field} is too long")
    return v


async def load_rate_groups(db: AsyncSession, org_id: str):
    """[(category, ["Label: value", ...]), ...] in display order, HTML-escaped,
    for building email bodies. Returns [] if there are no active rates."""
    rows = (await db.execute(text("""
        SELECT category, label, value FROM service_rates
        WHERE organization_id = :org AND is_active = TRUE
        ORDER BY sort_order, created_at
    """), {"org": org_id})).fetchall()
    groups = {}
    for r in rows:
        groups.setdefault(_html.escape(r.category), []).append(_html.escape(f"{r.label}: {r.value}"))
    return list(groups.items())


@router.get("")
async def list_rates(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sql = "SELECT id, category, label, value, sort_order, is_active FROM service_rates WHERE organization_id = :org"
    if current_user.role != UserRole.ADMIN:
        sql += " AND is_active = TRUE"
    sql += " ORDER BY sort_order, created_at"
    rows = (await db.execute(text(sql), {"org": current_user.organization_id})).fetchall()
    return [_row(r) for r in rows]


@router.post("")
async def create_rate(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    category = _clean(data.get("category"), "category", 80)
    label = _clean(data.get("label"), "label", 120)
    value = _clean(data.get("value"), "value", 160)
    max_order = (await db.execute(text(
        "SELECT COALESCE(MAX(sort_order), 0) FROM service_rates WHERE organization_id = :org"
    ), {"org": current_user.organization_id})).scalar()
    new_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO service_rates (id, organization_id, category, label, value, sort_order)
        VALUES (:id, :org, :category, :label, :value, :sort_order)
    """), {"id": new_id, "org": current_user.organization_id, "category": category,
           "label": label, "value": value, "sort_order": max_order + 10})
    await db.commit()
    return {"id": new_id, "created": True}


@router.patch("/{rate_id}")
async def update_rate(
    rate_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    sets, params = [], {"id": rate_id, "org": current_user.organization_id}
    for field, max_len in (("category", 80), ("label", 120), ("value", 160)):
        if field in data:
            params[field] = _clean(data[field], field, max_len)
            sets.append(f"{field} = :{field}")
    if "is_active" in data:
        params["is_active"] = bool(data["is_active"])
        sets.append("is_active = :is_active")
    if "sort_order" in data:
        try:
            params["sort_order"] = int(data["sort_order"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="sort_order must be a number")
        sets.append("sort_order = :sort_order")
    if not sets:
        raise HTTPException(status_code=400, detail="Nothing to update")
    sets.append("updated_at = now()")
    result = await db.execute(text(
        f"UPDATE service_rates SET {', '.join(sets)} WHERE id = :id AND organization_id = :org"
    ), params)
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Rate not found")
    return {"updated": True}


@router.delete("/{rate_id}")
async def delete_rate(
    rate_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text(
        "DELETE FROM service_rates WHERE id = :id AND organization_id = :org"
    ), {"id": rate_id, "org": current_user.organization_id})
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Rate not found")
    return {"deleted": True}
