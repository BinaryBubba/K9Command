"""
Admin Router - K9Command
Handles admin-specific functions: email templates, staff management, owner functions
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timezone
import uuid

from models import UserRole
from auth import get_current_user
from services.email import EmailService

router = APIRouter(prefix="/api/admin", tags=["Admin"])
security = HTTPBearer()


async def get_db():
    """Get database connection - injected at request time"""
    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    return client[os.environ['DB_NAME']]


# ==================== EMAIL TEMPLATES ====================

@router.get("/email-templates")
async def get_email_templates(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all email templates"""
    db = await get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = EmailService(db)
    templates = await service.get_templates()
    
    return {
        "templates": templates,
        "mock_mode": service.is_mock_mode()
    }


@router.put("/email-templates/{template_name}")
async def update_email_template(
    template_name: str,
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update an email template"""
    db = await get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    subject = data.get("subject")
    body = data.get("body")
    
    if not subject or not body:
        raise HTTPException(status_code=400, detail="subject and body required")
    
    service = EmailService(db)
    template = await service.update_template(template_name, subject, body)
    
    return {"message": "Template updated", "template": template.dict()}


@router.post("/email-templates/{template_name}/test")
async def send_test_email(
    template_name: str,
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Send a test email using a template"""
    db = await get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    
    service = EmailService(db)
    
    try:
        record = await service.send_test_email(template_name, email)
        return {
            "message": "Test email sent" if not service.is_mock_mode() else "Test email added to outbox",
            "email": record.dict(),
            "mock_mode": service.is_mock_mode()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/email-outbox")
async def get_email_outbox(
    limit: int = 50,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get email outbox records"""
    db = await get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = EmailService(db)
    emails = await service.get_outbox(limit)
    
    return {
        "emails": emails,
        "count": len(emails),
        "mock_mode": service.is_mock_mode()
    }


# ==================== STAFF REQUESTS ====================

@router.get("/staff-requests")
async def list_staff_requests(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List all staff account requests"""
    db = await get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    requests = await db.staff_requests.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {"requests": requests, "count": len(requests)}


@router.post("/staff-requests/{request_id}/approve")
async def approve_staff_request(
    request_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Approve a staff account request and create the staff user account"""
    db = await get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    request = await db.staff_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Check if email already taken
    existing = await db.users.find_one({"email": request.get("email")})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create the staff user account
    staff_id = str(uuid.uuid4())
    staff_doc = {
        "id": staff_id,
        "email": request.get("email"),
        "full_name": request.get("full_name"),
        "phone": request.get("phone"),
        "hashed_password": request.get("hashed_password"),
        "role": "staff",
        "is_active": True,
        "staff_approved": True,
        "approved_by": user.id,
        "approved_at": now,
        "created_at": now,
        "updated_at": now,
    }
    await db.users.insert_one(staff_doc)
    
    # Update request status
    await db.staff_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "approved_by": user.id,
            "approved_at": now,
            "user_id": staff_id
        }}
    )
    
    # Send welcome email to new staff member
    try:
        from services.email import EmailService
        email_service = EmailService(db)
        await email_service.send_email(
            to=request.get("email"),
            subject="Welcome to the K9Command Team!",
            body=f"""
Hello {request.get("full_name")},

Your staff account has been approved! You can now log in to K9Command using your email and password.

As a team member, you have access to:
- View and manage bookings
- Clock in/out for your shifts
- Request time off
- View your schedule
- Access daily operations

If you have any questions, please contact your administrator.

Welcome aboard!

Best regards,
K9Command Team
            """.strip(),
            template_name="staff_welcome"
        )
    except Exception as e:
        print(f"Failed to send welcome email: {e}")
    
    return {
        "message": "Staff request approved and account created",
        "request_id": request_id,
        "user_id": staff_id
    }


@router.post("/staff-requests/{request_id}/reject")
async def reject_staff_request(
    request_id: str,
    data: Optional[dict] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Reject a staff account request"""
    db = await get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    request = await db.staff_requests.find_one({"id": request_id})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    reason = data.get("reason", "") if data else ""
    now = datetime.now(timezone.utc).isoformat()
    
    await db.staff_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "reason": reason,
            "rejected_by": user.id,
            "rejected_at": now
        }}
    )
    
    return {"message": "Staff request rejected", "request_id": request_id}


# ==================== OWNER FUNCTIONS ====================

@router.get("/is-owner/{user_id}")
async def check_is_owner(
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Check if a user is the owner (first admin or marked as owner)"""
    db = await get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # First check if user has is_owner flag
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if target_user and target_user.get("is_owner"):
        return {"isOwner": True, "user_id": user_id}
    
    # Fallback: Find the first admin by creation date
    first_admin = await db.users.find_one(
        {"role": "admin"},
        {"_id": 0, "id": 1},
        sort=[("created_at", 1)]
    )
    
    is_owner = first_admin and first_admin.get("id") == user_id
    
    return {"isOwner": is_owner, "user_id": user_id}


@router.post("/create-admin")
async def create_admin_account(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new admin account (owner only)"""
    db = await get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if user is owner
    first_admin = await db.users.find_one(
        {"role": "admin"},
        {"_id": 0, "id": 1},
        sort=[("created_at", 1)]
    )
    
    if not first_admin or first_admin.get("id") != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can create admin accounts")
    
    email = data.get("email")
    full_name = data.get("fullName") or data.get("full_name")
    
    if not email or not full_name:
        raise HTTPException(status_code=400, detail="email and fullName required")
    
    # Check if email already exists
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create admin account (without password - they'll need to set it up)
    now = datetime.now(timezone.utc).isoformat()
    admin_id = str(uuid.uuid4())
    
    admin_doc = {
        "id": admin_id,
        "email": email,
        "full_name": full_name,
        "role": "admin",
        "created_at": now,
        "created_by": user.id,
        "needs_password_setup": True
    }
    
    await db.users.insert_one(admin_doc)
    admin_doc.pop("_id", None)
    
    # TODO: Send email with password setup link
    
    return {"message": "Admin account created", "admin": admin_doc}
