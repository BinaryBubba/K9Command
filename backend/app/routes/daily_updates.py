from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from database import get_db
from db_models import DailyUpdate, UserRole
from auth import get_current_user, require_role

router = APIRouter(prefix="/daily-updates", tags=["Daily Updates"])


@router.get("")
async def list_daily_updates(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(DailyUpdate).order_by(DailyUpdate.created_at.desc())
    )
    return result.scalars().all()


@router.post("")
async def create_daily_update(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    update = DailyUpdate(**payload)
    db.add(update)
    await db.commit()
    await db.refresh(update)
    return update


@router.post("/{update_id}/approve")
async def approve_daily_update(
    update_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
):
    result = await db.execute(
        select(DailyUpdate).where(DailyUpdate.id == update_id)
    )
    update = result.scalar_one_or_none()

    if not update:
        raise HTTPException(status_code=404, detail="Daily update not found")

    update.status = "approved" if hasattr(update, "status") else getattr(update, "status", None)
    if hasattr(update, "approved"):
        update.approved = True

    await db.commit()
    await db.refresh(update)
    return update
