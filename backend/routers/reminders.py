"""
Reminders Router - K9Command
Handles auto-reminders for bookings
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timezone

from models import UserRole
from auth import get_current_user
from services.reminders import ReminderService, schedule_reminders_for_booking

router = APIRouter(prefix="/api/k9", tags=["Reminders"])
security = HTTPBearer()


def get_db():
    """Get database connection"""
    from server import db
    return db


@router.get("/reminders/preferences")
async def get_reminder_preferences(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get current user's reminder preferences"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    service = ReminderService(db)
    prefs = await service.get_user_preferences(user.id)
    
    return {
        "user_id": prefs.user_id,
        "check_in_24h": prefs.check_in_24h,
        "check_in_2h": prefs.check_in_2h,
        "check_out_24h": prefs.check_out_24h,
        "check_out_2h": prefs.check_out_2h,
        "booking_confirmation": prefs.booking_confirmation,
        "payment_due": prefs.payment_due,
        "channels": prefs.channels,
        "updated_at": prefs.updated_at.isoformat() if hasattr(prefs.updated_at, 'isoformat') else str(prefs.updated_at)
    }


@router.put("/reminders/preferences")
async def update_reminder_preferences(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update current user's reminder preferences"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    service = ReminderService(db)
    prefs = await service.update_user_preferences(user.id, data)
    
    return {
        "message": "Preferences updated",
        "preferences": {
            "user_id": prefs.user_id,
            "check_in_24h": prefs.check_in_24h,
            "check_in_2h": prefs.check_in_2h,
            "check_out_24h": prefs.check_out_24h,
            "check_out_2h": prefs.check_out_2h,
            "booking_confirmation": prefs.booking_confirmation,
            "payment_due": prefs.payment_due,
            "channels": prefs.channels
        }
    }


@router.get("/reminders/scheduled")
async def get_scheduled_reminders(
    booking_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get scheduled reminders for current user"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    service = ReminderService(db)
    reminders = await service.get_user_scheduled_reminders(user.id, booking_id)
    
    return {"reminders": reminders, "count": len(reminders)}


@router.post("/reminders/schedule/{booking_id}")
async def schedule_reminders_for_specific_booking(
    booking_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Manually schedule reminders for a booking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    is_owner = booking.get('customer_id') == user.id or booking.get('household_id') == user.household_id
    if not is_owner and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    dog_names = []
    for dog_id in booking.get('dog_ids', []):
        dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
        if dog:
            dog_names.append(dog['name'])
    
    if not dog_names:
        dog_names = ["Your pet"]
    
    scheduled = await schedule_reminders_for_booking(db, booking, dog_names)
    
    return {
        "message": f"Scheduled {len(scheduled)} reminders",
        "reminders": [
            {
                "id": r.id,
                "type": r.reminder_type.value,
                "scheduled_for": r.scheduled_for.isoformat(),
                "title": r.title
            }
            for r in scheduled
        ]
    }


@router.delete("/reminders/cancel/{booking_id}")
async def cancel_booking_reminders(
    booking_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Cancel all pending reminders for a booking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    is_owner = booking.get('customer_id') == user.id or booking.get('household_id') == user.household_id
    if not is_owner and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    service = ReminderService(db)
    cancelled_count = await service.cancel_booking_reminders(booking_id)
    
    return {"message": f"Cancelled {cancelled_count} reminders"}


@router.post("/reminders/process")
async def process_due_reminders(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Manually trigger processing of due reminders (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = ReminderService(db)
    results = await service.process_due_reminders()
    
    return {
        "message": "Reminder processing complete",
        "results": results
    }


@router.get("/reminders/pending")
async def get_pending_reminders(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all pending reminders (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = ReminderService(db)
    reminders = await service.get_pending_reminders(limit=200)
    
    return {"reminders": reminders, "count": len(reminders)}
