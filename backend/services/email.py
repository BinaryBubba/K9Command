"""
Email Service - K9Command
Handles email sending via SMTP (API mode) or mock outbox
"""
import os
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class EmailTemplate(BaseModel):
    subject: str
    body: str
    updated_at: Optional[str] = None


class EmailRecord(BaseModel):
    id: str
    to: str
    subject: str
    body: str
    type: str
    status: str
    sent_at: str
    booking_id: Optional[str] = None
    error: Optional[str] = None


class EmailService:
    """
    Email service that handles both SMTP and mock modes.
    In mock mode, emails are stored in MongoDB instead of being sent.
    """
    
    def __init__(self, db):
        self.db = db
        self.smtp_host = os.environ.get('SMTP_HOST')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_user = os.environ.get('SMTP_USER')
        self.smtp_pass = os.environ.get('SMTP_PASS')
        self.smtp_from = os.environ.get('SMTP_FROM', 'noreply@k9command.com')
        self.mock_mode = not all([self.smtp_host, self.smtp_user, self.smtp_pass])
    
    def is_mock_mode(self) -> bool:
        return self.mock_mode
    
    async def get_templates(self) -> Dict[str, EmailTemplate]:
        """Get all email templates"""
        templates_doc = await self.db.email_templates.find_one({"type": "templates"}, {"_id": 0})
        
        if templates_doc and "templates" in templates_doc:
            return templates_doc["templates"]
        
        # Return defaults
        return {
            "booking_confirmation": {
                "subject": "Booking Confirmation - K9Command",
                "body": "Hello,\n\nYour booking has been {{status}}!\n\nDetails:\n- Check-in: {{startDate}}\n- Check-out: {{endDate}}\n- Dogs: {{dogs}}\n\nThank you for choosing K9Command!\n\nBest regards,\nThe K9Command Team"
            },
            "booking_reminder": {
                "subject": "Booking Reminder - K9Command",
                "body": "Hello,\n\nThis is a reminder about your upcoming stay.\n\nDetails:\n- Check-in: {{startDate}}\n- Check-out: {{endDate}}\n- Dogs: {{dogs}}\n\nWe look forward to seeing you!\n\nBest regards,\nThe K9Command Team"
            },
            "check_in_reminder": {
                "subject": "Check-in Tomorrow - K9Command",
                "body": "Hello,\n\nJust a reminder that {{dogs}} is scheduled to check in tomorrow at {{startDate}}.\n\nPlease remember to bring:\n- Vaccination records\n- Favorite toys\n- Special food (if applicable)\n\nSee you soon!\n\nBest regards,\nThe K9Command Team"
            },
            "check_out_reminder": {
                "subject": "Pick-up Tomorrow - K9Command",
                "body": "Hello,\n\n{{dogs}} will be ready for pick-up tomorrow at {{endDate}}.\n\nWe've had a wonderful time with your furry friend!\n\nBest regards,\nThe K9Command Team"
            }
        }
    
    async def update_template(self, template_name: str, subject: str, body: str) -> EmailTemplate:
        """Update an email template"""
        templates = await self.get_templates()
        templates[template_name] = {
            "subject": subject,
            "body": body,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.email_templates.update_one(
            {"type": "templates"},
            {"$set": {"templates": templates}},
            upsert=True
        )
        
        return EmailTemplate(**templates[template_name])
    
    def _render_template(self, template: Dict[str, str], data: Dict[str, Any]) -> tuple:
        """Render a template with data substitution"""
        subject = template.get("subject", "")
        body = template.get("body", "")
        
        for key, value in data.items():
            placeholder = "{{" + key + "}}"
            str_value = str(value) if value is not None else ""
            subject = subject.replace(placeholder, str_value)
            body = body.replace(placeholder, str_value)
        
        return subject, body
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        email_type: str = "general",
        booking_id: Optional[str] = None
    ) -> EmailRecord:
        """Send an email (SMTP) or store in mock outbox"""
        email_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        record = {
            "id": email_id,
            "to": to,
            "subject": subject,
            "body": body,
            "type": email_type,
            "booking_id": booking_id,
            "sent_at": now,
            "status": "pending",
            "error": None
        }
        
        if self.mock_mode:
            # Store in mock outbox
            record["status"] = "sent"
            record["mock"] = True
            await self.db.email_outbox.insert_one(record)
            return EmailRecord(**record)
        
        # Send via SMTP
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_from
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            record["status"] = "sent"
        except Exception as e:
            record["status"] = "failed"
            record["error"] = str(e)
        
        # Store record in outbox
        await self.db.email_outbox.insert_one(record)
        return EmailRecord(**record)
    
    async def send_booking_confirmation(
        self,
        to: str,
        booking: Dict[str, Any],
        dog_names: List[str]
    ) -> EmailRecord:
        """Send booking confirmation email"""
        templates = await self.get_templates()
        template = templates.get("booking_confirmation", {})
        
        data = {
            "startDate": booking.get("check_in_date") or booking.get("startDate", ""),
            "endDate": booking.get("check_out_date") or booking.get("endDate", ""),
            "dogs": ", ".join(dog_names) if dog_names else "Your pet",
            "status": booking.get("status", "received"),
            "total": str(booking.get("total", 0))
        }
        
        subject, body = self._render_template(template, data)
        
        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            email_type="booking_confirmation",
            booking_id=booking.get("id")
        )
    
    async def send_test_email(self, template_name: str, to: str) -> EmailRecord:
        """Send a test email using a template"""
        templates = await self.get_templates()
        template = templates.get(template_name)
        
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Use sample data for test
        data = {
            "startDate": "2024-03-15",
            "endDate": "2024-03-20",
            "dogs": "Buddy, Max",
            "status": "confirmed",
            "total": "275.00"
        }
        
        subject, body = self._render_template(template, data)
        
        return await self.send_email(
            to=to,
            subject=f"[TEST] {subject}",
            body=body,
            email_type="test"
        )
    
    async def get_outbox(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get email outbox records"""
        emails = await self.db.email_outbox.find(
            {}, {"_id": 0}
        ).sort("sent_at", -1).limit(limit).to_list(limit)
        
        return emails
