"""
Auto-Reminder Service
Handles scheduling and sending automated appointment reminders
"""
import os
import uuid
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from enum import Enum

from services.notifications import (
    NotificationService,
    NotificationCreate,
    NotificationType,
    NotificationChannel,
    NotificationPriority
)
from services.push_notifications import (
    PushNotificationService,
    PushNotificationPayload,
    send_booking_status_push
)


class ReminderType(str, Enum):
    CHECK_IN_24H = "check_in_24h"
    CHECK_IN_2H = "check_in_2h"
    CHECK_OUT_24H = "check_out_24h"
    CHECK_OUT_2H = "check_out_2h"
    BOOKING_CONFIRMATION = "booking_confirmation"
    PAYMENT_DUE = "payment_due"


class ReminderStatus(str, Enum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledReminder(BaseModel):
    """Model for a scheduled reminder"""
    id: str
    user_id: str
    booking_id: str
    reminder_type: ReminderType
    scheduled_for: datetime
    status: ReminderStatus = ReminderStatus.SCHEDULED
    title: str
    message: str
    channels: List[str] = ["in_app", "push"]
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class ReminderPreferences(BaseModel):
    """User preferences for reminders"""
    user_id: str
    check_in_24h: bool = True
    check_in_2h: bool = True
    check_out_24h: bool = True
    check_out_2h: bool = False
    booking_confirmation: bool = True
    payment_due: bool = True
    channels: List[str] = ["in_app", "push"]
    updated_at: datetime


# Default reminder timings in hours before event
DEFAULT_REMINDER_TIMINGS = {
    ReminderType.CHECK_IN_24H: 24,
    ReminderType.CHECK_IN_2H: 2,
    ReminderType.CHECK_OUT_24H: 24,
    ReminderType.CHECK_OUT_2H: 2,
}


class ReminderService:
    """
    Service for managing auto-reminders for bookings
    """
    
    def __init__(self, db):
        self.db = db
        self.notification_service = NotificationService(db)
        self.push_service = PushNotificationService(db)
    
    async def get_user_preferences(self, user_id: str) -> ReminderPreferences:
        """Get reminder preferences for a user (or return defaults)"""
        prefs = await self.db.reminder_preferences.find_one(
            {"user_id": user_id}, {"_id": 0}
        )
        
        if prefs:
            return ReminderPreferences(**prefs)
        
        # Return default preferences
        return ReminderPreferences(
            user_id=user_id,
            check_in_24h=True,
            check_in_2h=True,
            check_out_24h=True,
            check_out_2h=False,
            booking_confirmation=True,
            payment_due=True,
            channels=["in_app", "push"],
            updated_at=datetime.now(timezone.utc)
        )
    
    async def update_user_preferences(
        self, 
        user_id: str, 
        preferences: Dict[str, Any]
    ) -> ReminderPreferences:
        """Update user's reminder preferences"""
        now = datetime.now(timezone.utc)
        
        update_data = {
            "user_id": user_id,
            "updated_at": now.isoformat(),
            **{k: v for k, v in preferences.items() if k != 'user_id'}
        }
        
        await self.db.reminder_preferences.update_one(
            {"user_id": user_id},
            {"$set": update_data},
            upsert=True
        )
        
        return await self.get_user_preferences(user_id)
    
    async def schedule_booking_reminders(
        self,
        booking_id: str,
        user_id: str,
        dog_names: List[str],
        check_in_date: datetime,
        check_out_date: datetime,
        kennel_name: Optional[str] = None
    ) -> List[ScheduledReminder]:
        """Schedule all applicable reminders for a booking"""
        prefs = await self.get_user_preferences(user_id)
        now = datetime.now(timezone.utc)
        scheduled = []
        
        # Check-in reminders
        if prefs.check_in_24h:
            reminder_time = check_in_date - timedelta(hours=24)
            if reminder_time > now:
                reminder = await self._create_reminder(
                    user_id=user_id,
                    booking_id=booking_id,
                    reminder_type=ReminderType.CHECK_IN_24H,
                    scheduled_for=reminder_time,
                    title="Check-in Tomorrow!",
                    message=f"Reminder: {', '.join(dog_names)} {'is' if len(dog_names) == 1 else 'are'} scheduled to check in tomorrow at {check_in_date.strftime('%I:%M %p')}.",
                    channels=prefs.channels,
                    metadata={"dog_names": dog_names, "kennel_name": kennel_name}
                )
                scheduled.append(reminder)
        
        if prefs.check_in_2h:
            reminder_time = check_in_date - timedelta(hours=2)
            if reminder_time > now:
                reminder = await self._create_reminder(
                    user_id=user_id,
                    booking_id=booking_id,
                    reminder_type=ReminderType.CHECK_IN_2H,
                    scheduled_for=reminder_time,
                    title="Check-in in 2 Hours",
                    message=f"Almost time! {', '.join(dog_names)} {'is' if len(dog_names) == 1 else 'are'} scheduled to check in at {check_in_date.strftime('%I:%M %p')}. See you soon!",
                    channels=prefs.channels,
                    metadata={"dog_names": dog_names, "kennel_name": kennel_name}
                )
                scheduled.append(reminder)
        
        # Check-out reminders
        if prefs.check_out_24h:
            reminder_time = check_out_date - timedelta(hours=24)
            if reminder_time > now:
                reminder = await self._create_reminder(
                    user_id=user_id,
                    booking_id=booking_id,
                    reminder_type=ReminderType.CHECK_OUT_24H,
                    scheduled_for=reminder_time,
                    title="Pick-up Tomorrow!",
                    message=f"Reminder: {', '.join(dog_names)} will be ready for pick-up tomorrow at {check_out_date.strftime('%I:%M %p')}.",
                    channels=prefs.channels,
                    metadata={"dog_names": dog_names, "kennel_name": kennel_name}
                )
                scheduled.append(reminder)
        
        if prefs.check_out_2h:
            reminder_time = check_out_date - timedelta(hours=2)
            if reminder_time > now:
                reminder = await self._create_reminder(
                    user_id=user_id,
                    booking_id=booking_id,
                    reminder_type=ReminderType.CHECK_OUT_2H,
                    scheduled_for=reminder_time,
                    title="Pick-up in 2 Hours",
                    message=f"Almost time! {', '.join(dog_names)} will be ready at {check_out_date.strftime('%I:%M %p')}. We can't wait to tell you about their stay!",
                    channels=prefs.channels,
                    metadata={"dog_names": dog_names, "kennel_name": kennel_name}
                )
                scheduled.append(reminder)
        
        return scheduled
    
    async def _create_reminder(
        self,
        user_id: str,
        booking_id: str,
        reminder_type: ReminderType,
        scheduled_for: datetime,
        title: str,
        message: str,
        channels: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScheduledReminder:
        """Create and store a scheduled reminder"""
        reminder_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        reminder = ScheduledReminder(
            id=reminder_id,
            user_id=user_id,
            booking_id=booking_id,
            reminder_type=reminder_type,
            scheduled_for=scheduled_for,
            status=ReminderStatus.SCHEDULED,
            title=title,
            message=message,
            channels=channels,
            created_at=now,
            metadata=metadata
        )
        
        reminder_doc = reminder.dict()
        reminder_doc['scheduled_for'] = reminder.scheduled_for.isoformat()
        reminder_doc['created_at'] = reminder.created_at.isoformat()
        
        await self.db.scheduled_reminders.insert_one(reminder_doc)
        
        return reminder
    
    async def cancel_booking_reminders(self, booking_id: str) -> int:
        """Cancel all pending reminders for a booking"""
        result = await self.db.scheduled_reminders.update_many(
            {"booking_id": booking_id, "status": ReminderStatus.SCHEDULED.value},
            {"$set": {"status": ReminderStatus.CANCELLED.value}}
        )
        return result.modified_count
    
    async def get_pending_reminders(
        self,
        before: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get reminders that are due to be sent"""
        if before is None:
            before = datetime.now(timezone.utc)
        
        reminders = await self.db.scheduled_reminders.find(
            {
                "status": ReminderStatus.SCHEDULED.value,
                "scheduled_for": {"$lte": before.isoformat()}
            },
            {"_id": 0}
        ).limit(limit).to_list(limit)
        
        return reminders
    
    async def get_user_scheduled_reminders(
        self,
        user_id: str,
        booking_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get scheduled reminders for a user"""
        query = {"user_id": user_id, "status": ReminderStatus.SCHEDULED.value}
        if booking_id:
            query["booking_id"] = booking_id
        
        reminders = await self.db.scheduled_reminders.find(
            query, {"_id": 0}
        ).sort("scheduled_for", 1).to_list(100)
        
        return reminders
    
    async def send_reminder(self, reminder: Dict[str, Any]) -> bool:
        """Send a reminder through configured channels"""
        reminder_id = reminder['id']
        user_id = reminder['user_id']
        channels = reminder.get('channels', ['in_app', 'push'])
        
        try:
            # Send in-app notification
            if 'in_app' in channels:
                await self.notification_service.send_notification(NotificationCreate(
                    user_id=user_id,
                    type=NotificationType.BOOKING_REMINDER,
                    title=reminder['title'],
                    message=reminder['message'],
                    priority=NotificationPriority.HIGH,
                    channels=[NotificationChannel.IN_APP],
                    data={
                        "booking_id": reminder['booking_id'],
                        "reminder_type": reminder['reminder_type']
                    },
                    action_url=f"/customer/bookings/{reminder['booking_id']}"
                ))
            
            # Send push notification
            if 'push' in channels:
                payload = PushNotificationPayload(
                    title=reminder['title'],
                    body=reminder['message'],
                    tag=f"reminder-{reminder['booking_id']}",
                    data={
                        "booking_id": reminder['booking_id'],
                        "reminder_type": reminder['reminder_type']
                    },
                    action_url=f"/customer/bookings/{reminder['booking_id']}",
                    actions=[{"action": "view", "title": "View Booking"}]
                )
                await self.push_service.send_to_user(user_id, payload)
            
            # Mark as sent
            await self.db.scheduled_reminders.update_one(
                {"id": reminder_id},
                {"$set": {
                    "status": ReminderStatus.SENT.value,
                    "sent_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            return True
            
        except Exception as e:
            # Mark as failed
            await self.db.scheduled_reminders.update_one(
                {"id": reminder_id},
                {"$set": {
                    "status": ReminderStatus.FAILED.value,
                    "error_message": str(e)
                }}
            )
            return False
    
    async def process_due_reminders(self) -> Dict[str, int]:
        """Process all reminders that are due to be sent"""
        reminders = await self.get_pending_reminders()
        
        results = {
            "processed": 0,
            "sent": 0,
            "failed": 0
        }
        
        for reminder in reminders:
            results["processed"] += 1
            success = await self.send_reminder(reminder)
            if success:
                results["sent"] += 1
            else:
                results["failed"] += 1
        
        return results


# Background task for processing reminders
async def reminder_processor_task(db, interval_seconds: int = 60):
    """
    Background task that periodically processes due reminders.
    Should be run as an asyncio task.
    """
    service = ReminderService(db)
    
    while True:
        try:
            results = await service.process_due_reminders()
            if results["processed"] > 0:
                print(f"Reminder processor: Sent {results['sent']}, Failed {results['failed']}")
        except Exception as e:
            print(f"Reminder processor error: {e}")
        
        await asyncio.sleep(interval_seconds)


# Helper function to schedule reminders when booking is confirmed
async def schedule_reminders_for_booking(
    db,
    booking: Dict[str, Any],
    dog_names: List[str]
):
    """
    Helper to schedule reminders when a booking is confirmed.
    Called from booking confirmation flow.
    """
    service = ReminderService(db)
    
    # Get customer ID
    customer_id = booking.get('customer_id') or booking.get('household_id')
    if not customer_id:
        # Try to get from household
        household = await db.users.find_one(
            {"household_id": booking.get('household_id')},
            {"_id": 0, "id": 1}
        )
        if household:
            customer_id = household['id']
    
    if not customer_id:
        return []
    
    # Parse dates
    check_in = booking['check_in_date']
    check_out = booking['check_out_date']
    
    if isinstance(check_in, str):
        check_in = datetime.fromisoformat(check_in.replace('Z', '+00:00'))
    if isinstance(check_out, str):
        check_out = datetime.fromisoformat(check_out.replace('Z', '+00:00'))
    
    # Schedule reminders
    return await service.schedule_booking_reminders(
        booking_id=booking['id'],
        user_id=customer_id,
        dog_names=dog_names,
        check_in_date=check_in,
        check_out_date=check_out
    )
