"""
Notifications Router - K9Command
Handles in-app notifications and push notification subscriptions
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timezone

from models import UserRole
from auth import get_current_user
from services.notifications import NotificationService
from services.push_notifications import PushNotificationService, PushNotificationPayload

router = APIRouter(prefix="/api/k9", tags=["Notifications"])
security = HTTPBearer()


def get_db():
    """Get database connection"""
    from server import db
    return db


# ==================== IN-APP NOTIFICATIONS ====================

@router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get notifications for the current user"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    service = NotificationService(db)
    notifications = await service.get_user_notifications(
        user.id, unread_only=unread_only, limit=limit
    )
    
    return [n.dict() for n in notifications]


@router.get("/notifications/unread-count")
async def get_unread_notification_count(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get count of unread notifications"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    service = NotificationService(db)
    count = await service.get_unread_count(user.id)
    
    return {"unread_count": count}


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Mark a notification as read"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    service = NotificationService(db)
    success = await service.mark_as_read(notification_id, user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification marked as read"}


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Mark all notifications as read"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    service = NotificationService(db)
    count = await service.mark_all_as_read(user.id)
    
    return {"message": f"Marked {count} notifications as read"}


# ==================== PUSH NOTIFICATIONS ====================

@router.get("/push/vapid-key")
async def get_vapid_public_key():
    """Get VAPID public key for Web Push subscription"""
    from services.push_notifications import PushNotificationService
    service = PushNotificationService(get_db())
    return {"vapid_public_key": service.get_vapid_public_key()}


@router.post("/push/subscribe/web")
async def subscribe_web_push(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Subscribe to Web Push notifications"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    subscription_info = data.get("subscription")
    device_info = data.get("device_info")
    
    if not subscription_info:
        raise HTTPException(status_code=400, detail="subscription required")
    
    service = PushNotificationService(db)
    subscription = await service.subscribe_web_push(
        user.id, subscription_info, device_info
    )
    
    return {
        "message": "Subscribed to Web Push notifications",
        "subscription_id": subscription.id
    }


@router.post("/push/subscribe/fcm")
async def subscribe_fcm(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Subscribe to Firebase Cloud Messaging notifications"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    fcm_token = data.get("fcm_token")
    device_info = data.get("device_info")
    
    if not fcm_token:
        raise HTTPException(status_code=400, detail="fcm_token required")
    
    service = PushNotificationService(db)
    subscription = await service.subscribe_fcm(user.id, fcm_token, device_info)
    
    return {
        "message": "Subscribed to FCM notifications",
        "subscription_id": subscription.id
    }


@router.delete("/push/unsubscribe/{subscription_id}")
async def unsubscribe_push(
    subscription_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Unsubscribe from push notifications"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    service = PushNotificationService(db)
    success = await service.unsubscribe(user.id, subscription_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"message": "Unsubscribed from push notifications"}


@router.get("/push/subscriptions")
async def get_push_subscriptions(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all push subscriptions for current user"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    subscriptions = await db.push_subscriptions.find(
        {"user_id": user.id, "is_active": True},
        {"_id": 0, "id": 1, "subscription_type": 1, "device_info": 1, "created_at": 1}
    ).to_list(20)
    
    return {"subscriptions": subscriptions}


@router.post("/push/test")
async def test_push_notification(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Send a test push notification to current user"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    service = PushNotificationService(db)
    
    payload = PushNotificationPayload(
        title="Test Notification",
        body="This is a test push notification from K9Command!",
        tag="test",
        data={"test": True}
    )
    
    results = await service.send_to_user(user.id, payload)
    
    return {
        "message": "Test notification sent",
        "results": results
    }
