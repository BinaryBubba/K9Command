"""Meet & greet gate for bookings.

A booking can only be confirmed once every dog on it has completed its meet & greet
(pass or conditional) or been waived by an admin. When a dog becomes cleared, any
pending booking whose dogs are all cleared is confirmed automatically and the
household is emailed."""
from sqlalchemy import select
from db_models import Booking, BookingDog, BookingStatus, Dog as DogORM, User as UserORM, UserRole


def _val(x):
    return str(getattr(x, "value", x) or "").lower()


def dog_is_cleared(dog) -> bool:
    status = _val(dog.meet_and_greet_status)
    outcome = _val(dog.meet_and_greet_outcome)
    if status == "waived":
        return True
    return status == "completed" and outcome in ("pass", "conditional")


async def blocking_dogs(db, booking_id):
    """Names of dogs on this booking that have not cleared their meet & greet."""
    dogs = (await db.execute(
        select(DogORM).join(BookingDog, BookingDog.dog_id == DogORM.id).where(BookingDog.booking_id == booking_id)
    )).scalars().all()
    return [d.name for d in dogs if not dog_is_cleared(d)]


async def _send_confirmation(db, booking_id):
    try:
        from email_service import send_email, is_configured
        if not is_configured():
            return
        from app.routes.email_templates import load_template, fill_template
        b = (await db.execute(select(Booking).where(Booking.id == booking_id))).scalar_one_or_none()
        if not b:
            return
        org_id, household_id = b.organization_id, b.household_id
        check_in = b.check_in_date.strftime("%A, %B %-d, %Y") if b.check_in_date else "TBD"
        check_out = b.check_out_date.strftime("%A, %B %-d, %Y") if b.check_out_date else "TBD"
        dogs = (await db.execute(
            select(DogORM).join(BookingDog, BookingDog.dog_id == DogORM.id).where(BookingDog.booking_id == booking_id)
        )).scalars().all()
        dog_list = ", ".join(d.name for d in dogs) or "your dog(s)"
        users = (await db.execute(
            select(UserORM).where(UserORM.household_id == household_id, UserORM.role == UserRole.CUSTOMER)
        )).scalars().all()
        for u in users:
            if not u.email:
                continue
            try:
                subj, body = await load_template(db, org_id, "booking_confirmed")
                subj, body = fill_template("booking_confirmed", subj, body, {
                    "first_name": ((u.full_name or "").split(" ")[0] or "there"),
                    "dog_list": dog_list, "check_in": check_in, "check_out": check_out,
                })
                await send_email(to_email=u.email, subject=subj, html_body=body)
            except Exception as e:
                print(f"Failed to send booking confirmation email to {u.email}: {e}")
    except Exception as e:
        print(f"Booking confirmation email step failed: {e}")


async def auto_confirm_ready_bookings(db, dog_ids, acting_user=None):
    """After dogs are cleared, confirm pending bookings whose dogs are now all cleared
    and email the household. Never raises."""
    try:
        if not dog_ids:
            return []
        booking_ids = (await db.execute(
            select(BookingDog.booking_id).where(BookingDog.dog_id.in_(list(dog_ids))).distinct()
        )).scalars().all()
        confirmed = []
        for bid in booking_ids:
            b = (await db.execute(select(Booking).where(Booking.id == bid))).scalar_one_or_none()
            if not b or _val(b.status) != "pending":
                continue
            if await blocking_dogs(db, bid):
                continue
            b.status = BookingStatus.CONFIRMED
            confirmed.append(bid)
        if not confirmed:
            return []
        await db.commit()
        for bid in confirmed:
            await _send_confirmation(db, bid)
            if acting_user is not None:
                from audit_service import log_audit
                await log_audit(db, acting_user, "update", "booking", bid, "Booking confirmed automatically after meet & greet was cleared")
        return confirmed
    except Exception as e:
        print(f"auto-confirm failed: {e}")
        try:
            await db.rollback()
        except Exception:
            pass
        return []
