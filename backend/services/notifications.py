"""
Notification Service Framework
Supports in-app, email (future), and SMS (future) notifications
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid


class NotificationType(str, Enum):
    BOOKING_CREATED = "booking_created"
    BOOKING_AUTO_BLOCKED = "booking_auto_blocked"
    BOOKING_APPROVED = "booking_approved"
    BOOKING_REJECTED = "booking_rejected"
    BOOKING_REMINDER = "booking_reminder"
    CHECK_IN_REMINDER = "check_in_reminder"
    CHECK_OUT_REMINDER = "check_out_reminder"
    PAYMENT_DUE = "payment_due"
    ADMIN_ALERT = "admin_alert"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationCreate(BaseModel):
    user_id: str
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channels: List[NotificationChannel] = [NotificationChannel.IN_APP]
    data: Optional[Dict[str, Any]] = None
    action_url: Optional[str] = None


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: str  # Store as string for flexibility
    title: str
    message: str
    priority: str  # Store as string for flexibility
    channels: List[str]  # Store as strings for flexibility
    data: Optional[Dict[str, Any]] = None
    action_url: Optional[str] = None
    is_read: bool
    created_at: str


class NotificationService:
    """
    Notification service that handles routing notifications to appropriate channels.
    Currently only in-app is implemented. Email and SMS are stubbed for future implementation.
    """
    
    def __init__(self, db):
        self.db = db
        # Future: Initialize email client (SendGrid, Resend)
        # self.email_client = None
        # Future: Initialize SMS client (Twilio)
        # self.sms_client = None
    
    async def send_notification(self, notification: NotificationCreate) -> NotificationResponse:
        """Send notification through specified channels"""
        notification_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        notification_doc = {
            "id": notification_id,
            "user_id": notification.user_id,
            "type": notification.type.value if hasattr(notification.type, 'value') else notification.type,
            "title": notification.title,
            "message": notification.message,
            "priority": notification.priority.value if hasattr(notification.priority, 'value') else notification.priority,
            "channels": [c.value for c in notification.channels],
            "data": notification.data,
            "action_url": notification.action_url,
            "is_read": False,
            "created_at": now,
        }
        
        # Store in database for in-app notifications
        if NotificationChannel.IN_APP in notification.channels:
            await self.db.notifications.insert_one(notification_doc)
        
        # Future: Send email
        if NotificationChannel.EMAIL in notification.channels:
            await self._send_email(notification)
        
        # Future: Send SMS
        if NotificationChannel.SMS in notification.channels:
            await self._send_sms(notification)
        
        notification_doc.pop('_id', None)
        return NotificationResponse(**notification_doc)
    
    async def _send_email(self, notification: NotificationCreate):
        """
        Future implementation: Send email notification
        Will integrate with SendGrid or Resend
        """
        # Placeholder for email sending logic
        # Example implementation:
        # user = await self.db.users.find_one({"id": notification.user_id})
        # if user and user.get("email"):
        #     await self.email_client.send(
        #         to=user["email"],
        #         subject=notification.title,
        #         body=notification.message
        #     )
        pass
    
    async def _send_sms(self, notification: NotificationCreate):
        """
        Future implementation: Send SMS notification
        Will integrate with Twilio
        """
        # Placeholder for SMS sending logic
        # Example implementation:
        # user = await self.db.users.find_one({"id": notification.user_id})
        # if user and user.get("phone"):
        #     await self.sms_client.messages.create(
        #         to=user["phone"],
        #         body=notification.message
        #     )
        pass
    
    async def get_user_notifications(
        self, 
        user_id: str, 
        unread_only: bool = False,
        limit: int = 50
    ) -> List[NotificationResponse]:
        """Get notifications for a user"""
        query = {"user_id": user_id}
        if unread_only:
            query["is_read"] = False
        
        notifications = await self.db.notifications.find(
            query, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        # Normalize notifications to handle both old and new schema
        result = []
        for n in notifications:
            # Handle old schema (notification_type, channel, subject, body)
            if 'notification_type' in n and 'type' not in n:
                n['type'] = n.get('notification_type', 'custom')
            if 'channel' in n and 'channels' not in n:
                n['channels'] = [n.get('channel', 'in_app')]
            if 'subject' in n and 'title' not in n:
                n['title'] = n.get('subject', 'Notification')
            if 'body' in n and 'message' not in n:
                n['message'] = n.get('body', '')
            if 'priority' not in n:
                n['priority'] = 'medium'
            if 'is_read' not in n:
                n['is_read'] = n.get('status') == 'read'
            if 'data' not in n:
                n['data'] = n.get('metadata')
            if 'action_url' not in n:
                n['action_url'] = None
            
            try:
                result.append(NotificationResponse(**n))
            except Exception as e:
                # Skip malformed notifications
                print(f"Skipping malformed notification: {e}")
                continue
        
        return result
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read"""
        result = await self.db.notifications.update_one(
            {"id": notification_id, "user_id": user_id},
            {"$set": {"is_read": True}}
        )
        return result.modified_count > 0
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user"""
        result = await self.db.notifications.update_many(
            {"user_id": user_id, "is_read": False},
            {"$set": {"is_read": True}}
        )
        return result.modified_count
    
    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications"""
        return await self.db.notifications.count_documents({
            "user_id": user_id,
            "is_read": False
        })


# Helper functions for common notification types
async def notify_booking_auto_blocked(
    db,
    customer_id: str,
    customer_name: str,
    booking_id: str,
    dog_names: List[str],
    errors: List[Dict]
):
    """Notify customer that their booking was auto-blocked"""
    service = NotificationService(db)
    
    error_summary = "; ".join([f"{e['dog_name']}: {e['message']}" for e in errors[:3]])
    if len(errors) > 3:
        error_summary += f" (+{len(errors) - 3} more)"
    
    await service.send_notification(NotificationCreate(
        user_id=customer_id,
        type=NotificationType.BOOKING_AUTO_BLOCKED,
        title="Booking Requires Review",
        message=f"Your booking for {', '.join(dog_names)} requires admin approval. Reason: {error_summary}",
        priority=NotificationPriority.HIGH,
        channels=[NotificationChannel.IN_APP],  # Future: Add EMAIL, SMS
        data={
            "booking_id": booking_id,
            "errors": errors
        },
        action_url=f"/customer/bookings/{booking_id}"
    ))


async def notify_admin_pending_approval(
    db,
    admin_ids: List[str],
    booking_id: str,
    customer_name: str,
    dog_names: List[str],
    error_count: int
):
    """Notify admins about a new booking pending approval"""
    service = NotificationService(db)
    
    for admin_id in admin_ids:
        await service.send_notification(NotificationCreate(
            user_id=admin_id,
            type=NotificationType.ADMIN_ALERT,
            title="New Booking Requires Approval",
            message=f"Booking from {customer_name} for {', '.join(dog_names)} has {error_count} eligibility issue(s) and requires your review.",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.IN_APP],  # Future: Add EMAIL
            data={
                "booking_id": booking_id,
                "customer_name": customer_name,
                "error_count": error_count
            },
            action_url="/admin/booking-approvals"
        ))


async def notify_booking_approved(
    db,
    customer_id: str,
    booking_id: str,
    check_in_date: str,
    dog_names: List[str]
):
    """Notify customer that their booking was approved"""
    service = NotificationService(db)
    
    await service.send_notification(NotificationCreate(
        user_id=customer_id,
        type=NotificationType.BOOKING_APPROVED,
        title="Booking Approved!",
        message=f"Great news! Your booking for {', '.join(dog_names)} on {check_in_date} has been approved.",
        priority=NotificationPriority.MEDIUM,
        channels=[NotificationChannel.IN_APP],
        data={"booking_id": booking_id},
        action_url=f"/customer/bookings/{booking_id}"
    ))


async def notify_booking_rejected(
    db,
    customer_id: str,
    booking_id: str,
    reason: str,
    dog_names: List[str]
):
    """Notify customer that their booking was rejected"""
    service = NotificationService(db)
    
    await service.send_notification(NotificationCreate(
        user_id=customer_id,
        type=NotificationType.BOOKING_REJECTED,
        title="Booking Update",
        message=f"Your booking for {', '.join(dog_names)} could not be approved. Reason: {reason}",
        priority=NotificationPriority.HIGH,
        channels=[NotificationChannel.IN_APP],
        data={"booking_id": booking_id, "reason": reason},
        action_url=f"/customer/bookings/{booking_id}"
    ))
