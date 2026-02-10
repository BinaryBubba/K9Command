"""
Automation Service - Handles event-driven automation and notifications
Phase 4 Implementation
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import logging
import re

logger = logging.getLogger(__name__)


class AutomationService:
    """
    Handles event processing and automation rule execution.
    Supports email, SMS, and in-app notifications.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def log_event(
        self,
        event_type: str,
        event_source: str,
        source_id: str = None,
        user_id: str = None,
        data: Dict[str, Any] = None
    ) -> str:
        """Log an event and trigger any matching automation rules"""
        import uuid
        
        event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "event_source": event_source,
            "source_id": source_id,
            "user_id": user_id,
            "data": data or {},
            "triggered_automations": [],
            "processed": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.event_logs.insert_one(event)
        
        # Process automation rules
        triggered = await self.process_automations(event)
        
        if triggered:
            await self.db.event_logs.update_one(
                {"id": event["id"]},
                {"$set": {
                    "triggered_automations": triggered,
                    "processed": True,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        
        return event["id"]
    
    async def process_automations(self, event: Dict[str, Any]) -> List[str]:
        """Find and execute matching automation rules"""
        triggered = []
        
        # Find matching rules
        rules = await self.db.automation_rules.find({
            "active": True,
            "trigger_event": event["event_type"]
        }, {"_id": 0}).sort("priority", 1).to_list(100)
        
        for rule in rules:
            if self._check_conditions(rule.get("conditions", {}), event.get("data", {})):
                try:
                    await self._execute_actions(rule.get("actions", []), event)
                    triggered.append(rule["id"])
                    
                    # Update rule stats
                    await self.db.automation_rules.update_one(
                        {"id": rule["id"]},
                        {"$set": {
                            "last_triggered_at": datetime.now(timezone.utc).isoformat(),
                            "trigger_count": rule.get("trigger_count", 0) + 1
                        }}
                    )
                except Exception as e:
                    logger.error(f"Error executing automation {rule['id']}: {e}")
        
        return triggered
    
    def _check_conditions(self, conditions: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Check if conditions match the event data"""
        if not conditions:
            return True
        
        for key, expected in conditions.items():
            actual = data.get(key)
            
            if isinstance(expected, dict):
                # Handle operators like $lte, $gte, $in
                for op, val in expected.items():
                    if op == "$lte" and not (actual is not None and actual <= val):
                        return False
                    elif op == "$gte" and not (actual is not None and actual >= val):
                        return False
                    elif op == "$eq" and actual != val:
                        return False
                    elif op == "$ne" and actual == val:
                        return False
                    elif op == "$in" and actual not in val:
                        return False
            else:
                if actual != expected:
                    return False
        
        return True
    
    async def _execute_actions(self, actions: List[Dict[str, Any]], event: Dict[str, Any]):
        """Execute automation actions"""
        for action in actions:
            action_type = action.get("type")
            
            if action_type == "send_notification":
                await self._send_notification_action(action, event)
            elif action_type == "create_task":
                await self._create_task_action(action, event)
            elif action_type == "update_booking":
                await self._update_booking_action(action, event)
            elif action_type == "webhook":
                await self._webhook_action(action, event)
    
    async def _send_notification_action(self, action: Dict[str, Any], event: Dict[str, Any]):
        """Send a notification based on template or direct content"""
        import uuid
        
        template_id = action.get("template_id")
        
        if template_id:
            template = await self.db.notification_templates.find_one(
                {"id": template_id, "active": True}, {"_id": 0}
            )
            if not template:
                logger.warning(f"Notification template {template_id} not found")
                return
        else:
            template = {
                "notification_type": action.get("notification_type", "custom"),
                "channel": action.get("channel", "in_app"),
                "subject": action.get("subject", "Notification"),
                "body": action.get("body", "")
            }
        
        # Get recipient
        user_id = action.get("user_id") or event.get("user_id") or event.get("data", {}).get("user_id")
        
        if not user_id and event.get("data", {}).get("household_id"):
            # Find user by household
            user = await self.db.users.find_one(
                {"household_id": event["data"]["household_id"]}, {"_id": 0}
            )
            if user:
                user_id = user["id"]
        
        if not user_id:
            logger.warning("No recipient for notification")
            return
        
        # Render template with event data
        subject = self._render_template(template["subject"], event.get("data", {}))
        body = self._render_template(template["body"], event.get("data", {}))
        
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "household_id": event.get("data", {}).get("household_id"),
            "notification_type": template["notification_type"],
            "channel": template["channel"],
            "subject": subject,
            "body": body,
            "status": "pending",
            "reference_type": event.get("event_source"),
            "reference_id": event.get("source_id"),
            "metadata": {"event_id": event.get("id"), "action": action},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.notifications.insert_one(notification)
        
        # Actually send the notification
        await self._deliver_notification(notification)
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Render template with {{placeholder}} syntax"""
        def replace(match):
            key = match.group(1).strip()
            keys = key.split('.')
            value = data
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k, '')
                else:
                    value = ''
                    break
            return str(value) if value else ''
        
        return re.sub(r'\{\{([^}]+)\}\}', replace, template)
    
    async def _deliver_notification(self, notification: Dict[str, Any]):
        """Actually deliver the notification (email, SMS, in-app)"""
        channel = notification.get("channel", "in_app")
        
        try:
            if channel == "email":
                # TODO: Integrate with email service (SendGrid, SES, etc.)
                # For now, just mark as sent
                logger.info(f"EMAIL would be sent to user {notification['user_id']}: {notification['subject']}")
                status = "sent"
            
            elif channel == "sms":
                # TODO: Integrate with SMS service (Twilio, etc.)
                logger.info(f"SMS would be sent to user {notification['user_id']}: {notification['body'][:100]}")
                status = "sent"
            
            elif channel == "in_app":
                # In-app notifications are already stored, just update status
                status = "delivered"
            
            else:
                status = "sent"
            
            await self.db.notifications.update_one(
                {"id": notification["id"]},
                {"$set": {
                    "status": status,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "delivered_at": datetime.now(timezone.utc).isoformat() if status == "delivered" else None,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        except Exception as e:
            logger.error(f"Failed to deliver notification {notification['id']}: {e}")
            await self.db.notifications.update_one(
                {"id": notification["id"]},
                {"$set": {
                    "status": "failed",
                    "error_message": str(e),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
    
    async def _create_task_action(self, action: Dict[str, Any], event: Dict[str, Any]):
        """Create a task from automation"""
        import uuid
        
        task = {
            "id": str(uuid.uuid4()),
            "title": self._render_template(action.get("title", "Automated Task"), event.get("data", {})),
            "description": self._render_template(action.get("description", ""), event.get("data", {})),
            "assigned_to": action.get("assigned_to"),
            "location_id": event.get("data", {}).get("location_id", "main-kennel"),
            "due_date": None,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Calculate due date if specified
        if action.get("due_in_hours"):
            task["due_date"] = (datetime.now(timezone.utc) + timedelta(hours=action["due_in_hours"])).isoformat()
        
        await self.db.tasks.insert_one(task)
        logger.info(f"Created automated task: {task['id']}")
    
    async def _update_booking_action(self, action: Dict[str, Any], event: Dict[str, Any]):
        """Update booking from automation"""
        booking_id = event.get("source_id") or event.get("data", {}).get("booking_id")
        if not booking_id:
            return
        
        updates = action.get("updates", {})
        if updates:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            await self.db.bookings.update_one(
                {"id": booking_id},
                {"$set": updates}
            )
            logger.info(f"Updated booking {booking_id} via automation")
    
    async def _webhook_action(self, action: Dict[str, Any], event: Dict[str, Any]):
        """Call external webhook"""
        # TODO: Implement webhook calls for external integrations
        url = action.get("url")
        if url:
            logger.info(f"WEBHOOK would be called: {url}")
    
    async def send_notification(
        self,
        user_id: str,
        notification_type: str,
        channel: str,
        subject: str,
        body: str,
        reference_type: str = None,
        reference_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Direct notification send (without automation rule)"""
        import uuid
        
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "notification_type": notification_type,
            "channel": channel,
            "subject": subject,
            "body": body,
            "status": "pending",
            "reference_type": reference_type,
            "reference_id": reference_id,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.notifications.insert_one(notification)
        await self._deliver_notification(notification)
        
        return notification["id"]
    
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        query = {"user_id": user_id}
        if unread_only:
            query["read_at"] = None
        
        notifications = await self.db.notifications.find(
            query, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return notifications
    
    async def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read"""
        result = await self.db.notifications.update_one(
            {"id": notification_id, "user_id": user_id},
            {"$set": {
                "status": "read",
                "read_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return result.modified_count > 0
    
    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications"""
        return await self.db.notifications.count_documents({
            "user_id": user_id,
            "read_at": None
        })


# Pre-defined automation rules
DEFAULT_AUTOMATION_RULES = [
    {
        "name": "Booking Confirmation",
        "description": "Send confirmation when booking is confirmed",
        "trigger_event": "booking.confirmed",
        "conditions": {},
        "actions": [
            {
                "type": "send_notification",
                "notification_type": "booking_confirmed",
                "channel": "in_app",
                "subject": "Booking Confirmed!",
                "body": "Your booking for {{dog_names}} from {{check_in_date}} to {{check_out_date}} has been confirmed. We look forward to seeing you!"
            }
        ],
        "active": True,
        "priority": 1
    },
    {
        "name": "Check-in Reminder (1 day)",
        "description": "Remind customer 1 day before check-in",
        "trigger_event": "scheduled.checkin_reminder",
        "conditions": {"days_until_checkin": 1},
        "actions": [
            {
                "type": "send_notification",
                "notification_type": "check_in_reminder",
                "channel": "in_app",
                "subject": "Check-in Tomorrow!",
                "body": "Reminder: Your check-in for {{dog_names}} is tomorrow at {{check_in_time}}. Please bring vaccination records and any special food/medications."
            }
        ],
        "active": True,
        "priority": 2
    },
    {
        "name": "Payment Received",
        "description": "Confirm payment receipt",
        "trigger_event": "payment.completed",
        "conditions": {},
        "actions": [
            {
                "type": "send_notification",
                "notification_type": "payment_received",
                "channel": "in_app",
                "subject": "Payment Received",
                "body": "We've received your {{payment_type}} payment of ${{amount}}. Thank you!"
            }
        ],
        "active": True,
        "priority": 1
    },
    {
        "name": "Booking Requires Approval Alert",
        "description": "Alert staff when booking needs approval",
        "trigger_event": "booking.requires_approval",
        "conditions": {},
        "actions": [
            {
                "type": "create_task",
                "title": "Review Booking: {{customer_name}}",
                "description": "Booking requires approval. Reason: {{approval_reason}}. Check-in: {{check_in_date}}",
                "due_in_hours": 4
            }
        ],
        "active": True,
        "priority": 1
    }
]


async def seed_default_automations(db):
    """Seed default automation rules if none exist"""
    import uuid
    
    if await db.automation_rules.count_documents({}) == 0:
        for rule in DEFAULT_AUTOMATION_RULES:
            rule["id"] = str(uuid.uuid4())
            rule["trigger_count"] = 0
            rule["created_at"] = datetime.now(timezone.utc).isoformat()
            rule["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.automation_rules.insert_many(DEFAULT_AUTOMATION_RULES)
        logger.info("Seeded default automation rules")
