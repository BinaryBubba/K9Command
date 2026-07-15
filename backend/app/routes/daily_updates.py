"""
Daily Updates API
Staff post photo/note updates about a dog during their stay; customers
see them once sent (no separate draft/approval review sub-workflow for
now -- create-and-send happens in a single staff action).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4

from database import get_db
from db_models import DailyUpdate, UpdateStatus, Booking, User as UserORM, UserRole
from auth import get_current_user, require_role

router = APIRouter(prefix="/daily-updates", tags=["Daily Updates"])


def _media_url(key: str) -> Optional[str]:
    if not key:
        return None
    try:
        from app.storage import get_public_url, BUCKET_DOGS
        return get_public_url(BUCKET_DOGS, key)
    except Exception:
        return None


def _update_dict(u: DailyUpdate) -> dict:
    return {
        "id": u.id,
        "household_id": u.household_id,
        "booking_id": u.booking_id,
        "date": u.date.isoformat() if u.date else None,
        "media_urls": [_media_url(k) for k in (u.media_items or [])],
        "staff_snippets": u.staff_snippets or [],
        "status": u.status.value if u.status else None,
        "sent_at": u.sent_at.isoformat() if u.sent_at else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("")
async def list_daily_updates(
    booking_id: Optional[str] = Query(None),
    household_id: Optional[str] = Query(None),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(DailyUpdate)

    if current_user.role == UserRole.CUSTOMER:
        q = q.where(
            DailyUpdate.household_id == current_user.household_id,
            DailyUpdate.status == UpdateStatus.SENT,
        )
    elif household_id:
        q = q.where(DailyUpdate.household_id == household_id)

    if booking_id:
        q = q.where(DailyUpdate.booking_id == booking_id)

    q = q.order_by(DailyUpdate.date.desc())
    result = await db.execute(q)
    return [_update_dict(u) for u in result.scalars().all()]


@router.post("")
async def create_and_send_daily_update(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Staff/admin/manager only. Creates a daily update and immediately
    emails it to the household's portal accounts."""
    booking_id = data.get("booking_id")
    media_keys = data.get("media_keys", [])
    staff_snippets = data.get("staff_snippets", [])

    if not booking_id:
        raise HTTPException(status_code=400, detail="booking_id is required")
    if not media_keys and not staff_snippets:
        raise HTTPException(status_code=400, detail="At least one photo or note is required")

    booking = (await db.execute(
        select(Booking).where(Booking.id == booking_id, Booking.organization_id == current_user.organization_id)
    )).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    household_id = booking.household_id

    update = DailyUpdate(
        id=str(uuid4()),
        household_id=household_id,
        booking_id=booking_id,
        date=datetime.now(timezone.utc),
        media_items=media_keys,
        staff_snippets=staff_snippets,
        status=UpdateStatus.SENT,
        approved_by=current_user.id,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(update)
    await db.commit()
    await db.refresh(update)

    try:
        from email_service import send_email, is_configured
        if is_configured():
            portal_users = (await db.execute(
                select(UserORM).where(
                    UserORM.household_id == household_id,
                    UserORM.role == UserRole.CUSTOMER,
                )
            )).scalars().all()
            notes_html = "".join(f"<p>{s}</p>" for s in staff_snippets)
            photo_urls = [_media_url(k) for k in media_keys if _media_url(k)]
            photos_html = "".join(
                f'<img src="{url}" style="max-width:300px;margin:4px;border-radius:8px;">'
                for url in photo_urls
            )
            for u in portal_users:
                if not u.email:
                    continue
                try:
                    await send_email(
                        to_email=u.email,
                        subject="A new update about your dog!",
                        html_body=f"""
                            <p>Hi {u.full_name or ''},</p>
                            <p>Here's an update from your dog's stay with us:</p>
                            {notes_html}
                            {photos_html}
                        """,
                    )
                except Exception as e:
                    print(f"Failed to send daily update email to {u.email}: {e}")
    except Exception as e:
        print(f"Daily update email step failed: {e}")

    return _update_dict(update)
