"""
Push Notification Service
Supports Web Push API and Firebase Cloud Messaging (FCM)
"""
import os
import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid

# Web Push imports
try:
    from pywebpush import webpush, WebPushException
    WEB_PUSH_AVAILABLE = True
except ImportError:
    WEB_PUSH_AVAILABLE = False

# Firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


class PushSubscription(BaseModel):
    """Model for storing push subscriptions"""
    id: str
    user_id: str
    subscription_type: str  # 'web_push' or 'fcm'
    endpoint: Optional[str] = None  # For Web Push
    keys: Optional[Dict[str, str]] = None  # For Web Push (p256dh, auth)
    fcm_token: Optional[str] = None  # For FCM
    device_info: Optional[Dict[str, Any]] = None
    created_at: str
    is_active: bool = True


class PushNotificationPayload(BaseModel):
    """Payload for push notifications"""
    title: str
    body: str
    icon: Optional[str] = "/logo192.png"
    badge: Optional[str] = "/badge.png"
    tag: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    action_url: Optional[str] = None
    actions: Optional[List[Dict[str, str]]] = None


class PushNotificationService:
    """
    Unified push notification service supporting both Web Push and FCM
    """
    
    def __init__(self, db):
        self.db = db
        self._init_web_push()
        self._init_firebase()
    
    def _init_web_push(self):
        """Initialize Web Push with VAPID keys"""
        self.vapid_private_key = os.environ.get('VAPID_PRIVATE_KEY')
        self.vapid_public_key = os.environ.get('VAPID_PUBLIC_KEY')
        self.vapid_claims = {
            "sub": os.environ.get('VAPID_SUBJECT', 'mailto:admin@k9command.com')
        }
        
        # Generate VAPID keys if not present (for development)
        if not self.vapid_private_key or not self.vapid_public_key:
            self._generate_vapid_keys()
    
    def _generate_vapid_keys(self):
        """Generate VAPID keys for Web Push (development only)"""
        # In production, these should be set as environment variables
        # Using a deterministic key for development consistency
        seed = "k9command_vapid_dev_key_2025"
        self.vapid_private_key = hashlib.sha256(seed.encode()).hexdigest()[:32]
        self.vapid_public_key = hashlib.sha256((seed + "_public").encode()).hexdigest()[:65]
    
    def _init_firebase(self):
        """Initialize Firebase Admin SDK if credentials are available"""
        self.firebase_initialized = False
        
        if not FIREBASE_AVAILABLE:
            return
        
        # Check for Firebase credentials
        firebase_creds_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
        firebase_creds_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
        
        if firebase_creds_path and os.path.exists(firebase_creds_path):
            try:
                if not firebase_admin._apps:
                    cred = credentials.Certificate(firebase_creds_path)
                    firebase_admin.initialize_app(cred)
                self.firebase_initialized = True
            except Exception as e:
                print(f"Firebase initialization failed: {e}")
        elif firebase_creds_json:
            try:
                if not firebase_admin._apps:
                    cred_dict = json.loads(firebase_creds_json)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                self.firebase_initialized = True
            except Exception as e:
                print(f"Firebase initialization failed: {e}")
    
    def get_vapid_public_key(self) -> str:
        """Get the VAPID public key for client-side subscription"""
        return self.vapid_public_key or ""
    
    async def subscribe_web_push(
        self, 
        user_id: str, 
        subscription_info: Dict[str, Any],
        device_info: Optional[Dict[str, Any]] = None
    ) -> PushSubscription:
        """Register a Web Push subscription"""
        subscription_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        subscription = PushSubscription(
            id=subscription_id,
            user_id=user_id,
            subscription_type="web_push",
            endpoint=subscription_info.get('endpoint'),
            keys=subscription_info.get('keys'),
            device_info=device_info,
            created_at=now,
            is_active=True
        )
        
        # Deactivate existing subscriptions for same endpoint
        await self.db.push_subscriptions.update_many(
            {"user_id": user_id, "endpoint": subscription.endpoint},
            {"$set": {"is_active": False}}
        )
        
        # Save new subscription
        await self.db.push_subscriptions.insert_one(subscription.dict())
        
        return subscription
    
    async def subscribe_fcm(
        self,
        user_id: str,
        fcm_token: str,
        device_info: Optional[Dict[str, Any]] = None
    ) -> PushSubscription:
        """Register an FCM token subscription"""
        subscription_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        subscription = PushSubscription(
            id=subscription_id,
            user_id=user_id,
            subscription_type="fcm",
            fcm_token=fcm_token,
            device_info=device_info,
            created_at=now,
            is_active=True
        )
        
        # Deactivate existing subscriptions for same token
        await self.db.push_subscriptions.update_many(
            {"user_id": user_id, "fcm_token": fcm_token},
            {"$set": {"is_active": False}}
        )
        
        # Save new subscription
        await self.db.push_subscriptions.insert_one(subscription.dict())
        
        return subscription
    
    async def unsubscribe(self, user_id: str, subscription_id: str) -> bool:
        """Unsubscribe from push notifications"""
        result = await self.db.push_subscriptions.update_one(
            {"id": subscription_id, "user_id": user_id},
            {"$set": {"is_active": False}}
        )
        return result.modified_count > 0
    
    async def send_to_user(
        self,
        user_id: str,
        payload: PushNotificationPayload
    ) -> Dict[str, Any]:
        """Send push notification to all active subscriptions for a user"""
        subscriptions = await self.db.push_subscriptions.find(
            {"user_id": user_id, "is_active": True},
            {"_id": 0}
        ).to_list(100)
        
        results = {
            "web_push_sent": 0,
            "web_push_failed": 0,
            "fcm_sent": 0,
            "fcm_failed": 0,
            "errors": []
        }
        
        for sub in subscriptions:
            if sub['subscription_type'] == 'web_push':
                success = await self._send_web_push(sub, payload)
                if success:
                    results["web_push_sent"] += 1
                else:
                    results["web_push_failed"] += 1
            elif sub['subscription_type'] == 'fcm':
                success = await self._send_fcm(sub, payload)
                if success:
                    results["fcm_sent"] += 1
                else:
                    results["fcm_failed"] += 1
        
        return results
    
    async def _send_web_push(
        self,
        subscription: Dict[str, Any],
        payload: PushNotificationPayload
    ) -> bool:
        """Send a Web Push notification"""
        if not WEB_PUSH_AVAILABLE:
            return False
        
        if not subscription.get('endpoint') or not subscription.get('keys'):
            return False
        
        try:
            subscription_info = {
                "endpoint": subscription['endpoint'],
                "keys": subscription['keys']
            }
            
            data = json.dumps({
                "title": payload.title,
                "body": payload.body,
                "icon": payload.icon,
                "badge": payload.badge,
                "tag": payload.tag,
                "data": payload.data,
                "actions": payload.actions
            })
            
            webpush(
                subscription_info=subscription_info,
                data=data,
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims
            )
            return True
        except WebPushException as e:
            # If subscription is invalid, mark as inactive
            if e.response and e.response.status_code in [404, 410]:
                await self.db.push_subscriptions.update_one(
                    {"id": subscription['id']},
                    {"$set": {"is_active": False}}
                )
            return False
        except Exception as e:
            print(f"Web Push error: {e}")
            return False
    
    async def _send_fcm(
        self,
        subscription: Dict[str, Any],
        payload: PushNotificationPayload
    ) -> bool:
        """Send an FCM notification"""
        if not FIREBASE_AVAILABLE or not self.firebase_initialized:
            return False
        
        if not subscription.get('fcm_token'):
            return False
        
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=payload.title,
                    body=payload.body,
                    image=payload.icon
                ),
                data={
                    "click_action": payload.action_url or "/",
                    **(payload.data or {})
                },
                token=subscription['fcm_token']
            )
            
            messaging.send(message)
            return True
        except messaging.UnregisteredError:
            # Token is invalid, mark as inactive
            await self.db.push_subscriptions.update_one(
                {"id": subscription['id']},
                {"$set": {"is_active": False}}
            )
            return False
        except Exception as e:
            print(f"FCM error: {e}")
            return False


# Helper functions for common push notifications
async def send_booking_status_push(
    db,
    user_id: str,
    status: str,
    booking_id: str,
    dog_names: List[str],
    extra_info: Optional[str] = None
):
    """Send push notification for booking status changes"""
    service = PushNotificationService(db)
    
    titles = {
        "confirmed": "Booking Confirmed! 🎉",
        "pending_approval": "Booking Under Review",
        "approved": "Booking Approved! ✅",
        "rejected": "Booking Update",
        "checked_in": "Check-In Complete",
        "checked_out": "Check-Out Complete",
    }
    
    bodies = {
        "confirmed": f"Your stay for {', '.join(dog_names)} has been confirmed.",
        "pending_approval": f"Your booking for {', '.join(dog_names)} is being reviewed by our team.",
        "approved": f"Great news! Your booking for {', '.join(dog_names)} has been approved.",
        "rejected": f"Your booking for {', '.join(dog_names)} could not be approved. {extra_info or ''}",
        "checked_in": f"{', '.join(dog_names)} {'is' if len(dog_names) == 1 else 'are'} now checked in!",
        "checked_out": f"{', '.join(dog_names)} {'is' if len(dog_names) == 1 else 'are'} ready for pickup!",
    }
    
    payload = PushNotificationPayload(
        title=titles.get(status, "Booking Update"),
        body=bodies.get(status, f"Status update for {', '.join(dog_names)}"),
        tag=f"booking-{booking_id}",
        data={"booking_id": booking_id, "status": status},
        action_url=f"/customer/bookings/{booking_id}",
        actions=[
            {"action": "view", "title": "View Details"}
        ]
    )
    
    return await service.send_to_user(user_id, payload)


async def send_admin_alert_push(
    db,
    admin_ids: List[str],
    title: str,
    body: str,
    action_url: str,
    data: Optional[Dict[str, Any]] = None
):
    """Send push notification to admins"""
    service = PushNotificationService(db)
    
    payload = PushNotificationPayload(
        title=title,
        body=body,
        tag="admin-alert",
        data=data,
        action_url=action_url,
        actions=[
            {"action": "view", "title": "Review Now"}
        ]
    )
    
    results = {"total_sent": 0, "total_failed": 0}
    for admin_id in admin_ids:
        result = await service.send_to_user(admin_id, payload)
        results["total_sent"] += result["web_push_sent"] + result["fcm_sent"]
        results["total_failed"] += result["web_push_failed"] + result["fcm_failed"]
    
    return results
