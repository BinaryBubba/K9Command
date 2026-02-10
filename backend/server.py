from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import base64
import uuid

from models import (
    User, UserCreate, UserResponse, LoginRequest, LoginResponse,
    Location, LocationCreate, LocationResponse,
    Dog, DogCreate, DogResponse,
    Booking, BookingCreate, BookingResponse, BookingStatus,
    DailyUpdate, DailyUpdateCreate, DailyUpdateResponse, MediaItem, UpdateStatus,
    Task, TaskCreate, TaskResponse, TaskStatus,
    TimeEntry, TimeEntryCreate, TimeEntryResponse,
    AuditLog, AuditLogResponse, AuditAction,
    Incident, IncidentCreate, IncidentResponse,
    Review, ReviewCreate, ReviewResponse,
    UserRole,
    # Phase 1 models
    ServiceType, ServiceTypeCreate, ServiceTypeResponse,
    AddOn, AddOnCreate, AddOnResponse,
    CapacityRule, CapacityRuleCreate, CapacityRuleResponse,
    PricingRule, PricingRuleCreate, PricingRuleResponse,
    CancellationPolicy, CancellationPolicyCreate, CancellationPolicyResponse,
    SystemSetting,
    Payment, PaymentCreate, PaymentResponse,
    Invoice, InvoiceResponse,
    PriceCalculationRequest, PriceBreakdown,
    PaymentType, PaymentProvider as PaymentProviderEnum,
    # Phase 2 models
    StaffAssignment, StaffAssignmentCreate, StaffAssignmentResponse,
    PlayGroup, PlayGroupCreate, PlayGroupResponse,
    FeedingSchedule, FeedingScheduleCreate, FeedingScheduleResponse,
    DogOnSite, ArrivalDeparture, CapacitySnapshot, ApprovalQueueItem,
    # Phase 4 models
    NotificationTemplate, NotificationTemplateCreate, NotificationTemplateResponse,
    Notification, NotificationResponse,
    AutomationRule, AutomationRuleCreate, AutomationRuleResponse,
    EventLog, EventLogResponse,
    NotificationType, NotificationChannel
)
from auth import hash_password, verify_password, create_access_token, get_current_user, require_role, security
from ai_service import generate_daily_summary
from pricing_engine import PricingEngine
from payment_service import PaymentService
from automation_service import AutomationService, seed_default_automations

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dependency to get database
async def get_db():
    return db

# Helper function to log audit
async def create_audit_log(user_id: str, action: AuditAction, resource_type: str, resource_id: str = None, details: dict = {}):
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details
    )
    doc = audit.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.audit_logs.insert_one(doc)

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=LoginResponse)
async def register(user_data: UserCreate, database=Depends(get_db)):
    # Check if user exists
    existing_user = await database.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Account Governance Rules
    role = user_data.role
    
    # Rule 1: Admin registration - only allowed if no admins exist (first admin becomes owner)
    if role == UserRole.ADMIN:
        existing_admin = await database.users.find_one({"role": "admin"}, {"_id": 0})
        if existing_admin:
            raise HTTPException(
                status_code=403, 
                detail="Admin registration is not allowed. Contact the owner to create admin accounts."
            )
        # First admin - they become the owner
        is_owner = True
    else:
        is_owner = False
    
    # Rule 2: Staff registration requires approval (create request, don't create user yet)
    if role == UserRole.STAFF:
        # Create a staff request instead of direct registration
        from uuid import uuid4
        request_id = str(uuid4())
        request_doc = {
            "id": request_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "phone": user_data.phone,
            "hashed_password": hash_password(user_data.password),
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await database.staff_requests.insert_one(request_doc)
        
        # Return a response indicating pending approval
        raise HTTPException(
            status_code=202,  # Accepted
            detail="Staff registration submitted. Awaiting admin approval."
        )
    
    # Rule 3: Customers can register freely
    # Create household for customers
    household_id = None
    if user_data.role == UserRole.CUSTOMER:
        from uuid import uuid4
        household_id = str(uuid4())
    
    # Create user
    hashed_pwd = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_pwd,
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=user_data.role,
        household_id=household_id
    )
    
    user_doc = user.model_dump()
    user_doc['created_at'] = user_doc['created_at'].isoformat()
    user_doc['updated_at'] = user_doc['updated_at'].isoformat()
    if is_owner:
        user_doc['is_owner'] = True
    
    await database.users.insert_one(user_doc)
    
    # Create token
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    
    # Audit log
    await create_audit_log(user.id, AuditAction.CREATE, "user", user.id)
    
    user_response = UserResponse(**user.model_dump())
    return LoginResponse(token=token, user=user_response)

@api_router.post("/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, database=Depends(get_db)):
    user_doc = await database.users.find_one({"email": login_data.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**user_doc)
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")
    
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    
    # Audit log
    await create_audit_log(user.id, AuditAction.LOGIN, "user", user.id)
    
    user_response = UserResponse(**user.model_dump())
    return LoginResponse(token=token, user=user_response)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    return UserResponse(**user.model_dump())

@api_router.post("/auth/forgot-password")
async def forgot_password(email: EmailStr, database=Depends(get_db)):
    """Generate password reset token"""
    user_doc = await database.users.find_one({"email": email}, {"_id": 0})
    if not user_doc:
        # Return success even if user doesn't exist (security best practice)
        return {"message": "If this email exists, a reset link has been sent"}
    
    # Generate reset token
    import secrets
    reset_token = secrets.token_urlsafe(32)
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    
    await database.users.update_one(
        {"email": email},
        {"$set": {
            "reset_token": reset_token,
            "reset_token_expiry": expiry.isoformat()
        }}
    )
    
    # In production, send email with reset link
    # For now, return the token (ONLY FOR DEMO)
    return {
        "message": "Password reset token generated",
        "reset_token": reset_token,
        "note": "In production, this would be sent via email"
    }

@api_router.post("/auth/reset-password")
async def reset_password(
    request_data: dict,
    database=Depends(get_db)
):
    """Reset password using token"""
    reset_token = request_data.get('reset_token')
    new_password = request_data.get('new_password')
    
    if not reset_token or not new_password:
        raise HTTPException(status_code=400, detail="reset_token and new_password are required")
    
    user_doc = await database.users.find_one({
        "reset_token": reset_token
    }, {"_id": 0})
    
    if not user_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Check if token is expired
    if user_doc.get('reset_token_expiry'):
        expiry = datetime.fromisoformat(user_doc['reset_token_expiry'])
        if datetime.now(timezone.utc) > expiry:
            raise HTTPException(status_code=400, detail="Reset token has expired")
    
    # Update password
    hashed_pwd = hash_password(new_password)
    await database.users.update_one(
        {"email": user_doc['email']},
        {"$set": {
            "hashed_password": hashed_pwd,
            "reset_token": None,
            "reset_token_expiry": None
        }}
    )
    
    return {"message": "Password reset successful"}

# ==================== LOCATION ROUTES ====================

@api_router.post("/locations", response_model=LocationResponse)
async def create_location(location_data: LocationCreate, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    location = Location(**location_data.model_dump())
    doc = location.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.locations.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "location", location.id)
    
    return LocationResponse(**location.model_dump())

@api_router.get("/locations", response_model=List[LocationResponse])
async def get_locations(database=Depends(get_db)):
    locations = await database.locations.find({}, {"_id": 0}).to_list(100)
    return [LocationResponse(**loc) for loc in locations]

@api_router.get("/locations/{location_id}/availability")
async def check_availability(
    location_id: str,
    check_in: str,
    check_out: str,
    database=Depends(get_db)
):
    """Check real-time availability for rooms and crates"""
    check_in_date = datetime.fromisoformat(check_in)
    check_out_date = datetime.fromisoformat(check_out)
    
    # Get all bookings that overlap with requested dates
    overlapping_bookings = await database.bookings.find({
        "location_id": location_id,
        "status": {"$in": [BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]},
        "$or": [
            {
                "check_in_date": {"$lt": check_out_date.isoformat()},
                "check_out_date": {"$gt": check_in_date.isoformat()}
            }
        ]
    }, {"_id": 0}).to_list(1000)
    
    # Count occupied rooms and crates
    rooms_occupied = sum(1 for b in overlapping_bookings if b.get('accommodation_type') == 'room')
    crates_occupied = sum(1 for b in overlapping_bookings if b.get('accommodation_type') == 'crate')
    
    total_rooms = 7
    total_crates = 4
    
    return {
        "rooms_available": total_rooms - rooms_occupied,
        "crates_available": total_crates - crates_occupied,
        "total_rooms": total_rooms,
        "total_crates": total_crates,
        "check_in_date": check_in,
        "check_out_date": check_out
    }

# ==================== DOG ROUTES ====================

@api_router.post("/dogs", response_model=DogResponse)
async def create_dog(dog_data: DogCreate, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Only customers can add dogs")
    
    dog = Dog(**dog_data.model_dump(), household_id=user.household_id)
    doc = dog.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    # Serialize vaccination dates
    if doc.get('vaccinations'):
        for vac in doc['vaccinations']:
            if 'date_administered' in vac and isinstance(vac['date_administered'], datetime):
                vac['date_administered'] = vac['date_administered'].isoformat()
            if 'expiry_date' in vac and vac['expiry_date'] and isinstance(vac['expiry_date'], datetime):
                vac['expiry_date'] = vac['expiry_date'].isoformat()
    
    await database.dogs.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "dog", dog.id)
    
    return DogResponse(**dog.model_dump())

@api_router.get("/dogs", response_model=List[DogResponse])
async def get_dogs(credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    
    query = {}
    if user.role == UserRole.CUSTOMER:
        query = {"household_id": user.household_id}
    
    dogs = await database.dogs.find(query, {"_id": 0}).to_list(1000)
    return [DogResponse(**dog) for dog in dogs]

@api_router.get("/dogs/{dog_id}", response_model=DogResponse)
async def get_dog(dog_id: str, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    
    dog_doc = await database.dogs.find_one({"id": dog_id}, {"_id": 0})
    if not dog_doc:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    if user.role == UserRole.CUSTOMER and dog_doc['household_id'] != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return DogResponse(**dog_doc)

@api_router.patch("/dogs/{dog_id}", response_model=DogResponse)
async def update_dog(
    dog_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update dog profile - customers can only update their own dogs"""
    user = await get_current_user(credentials, database)
    
    dog_doc = await database.dogs.find_one({"id": dog_id}, {"_id": 0})
    if not dog_doc:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    # Access check
    if user.role == UserRole.CUSTOMER and dog_doc.get('household_id') != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Allowed fields for update
    allowed_fields = [
        'name', 'breed', 'age', 'birthday', 'weight', 'size',
        'feeding_instructions', 'feedingInstructions',
        'medications', 'behavior_notes', 'behaviorNotes',
        'special_needs', 'specialNeeds', 'notes'
    ]
    
    update_doc = {"updated_at": datetime.now(timezone.utc).isoformat()}
    for field in allowed_fields:
        if field in update_data and update_data[field] is not None:
            # Normalize field names to snake_case
            normalized_field = field
            if field == 'feedingInstructions':
                normalized_field = 'feeding_instructions'
            elif field == 'behaviorNotes':
                normalized_field = 'behavior_notes'
            elif field == 'specialNeeds':
                normalized_field = 'special_needs'
            update_doc[normalized_field] = update_data[field]
    
    result = await database.dogs.update_one(
        {"id": dog_id},
        {"$set": update_doc}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    # Return updated dog
    updated_dog = await database.dogs.find_one({"id": dog_id}, {"_id": 0})
    await create_audit_log(user.id, AuditAction.UPDATE, "dog", dog_id)
    
    return DogResponse(**updated_dog)

@api_router.post("/dogs/{dog_id}/upload-photo")
async def upload_dog_photo(
    dog_id: str,
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Upload dog profile photo"""
    user = await get_current_user(credentials, database)
    
    # Verify dog ownership
    dog_doc = await database.dogs.find_one({"id": dog_id}, {"_id": 0})
    if not dog_doc:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    if user.role == UserRole.CUSTOMER and dog_doc['household_id'] != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Read file
    content = await file.read()
    
    # Store as base64 (production: upload to S3)
    import base64
    file_data = base64.b64encode(content).decode('utf-8')
    photo_url = f"data:{file.content_type};base64,{file_data}"
    
    # Update dog
    await database.dogs.update_one(
        {"id": dog_id},
        {"$set": {"photo_url": photo_url}}
    )
    
    return {"message": "Photo uploaded successfully", "photo_url": photo_url[:100] + "..."}

@api_router.post("/dogs/{dog_id}/upload-vaccination")
async def upload_vaccination_file(
    dog_id: str,
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Upload vaccination documents"""
    user = await get_current_user(credentials, database)
    
    # Verify dog ownership
    dog_doc = await database.dogs.find_one({"id": dog_id}, {"_id": 0})
    if not dog_doc:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    if user.role == UserRole.CUSTOMER and dog_doc['household_id'] != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Read file
    content = await file.read()
    
    # Store as base64 (production: upload to S3)
    import base64
    file_data = base64.b64encode(content).decode('utf-8')
    file_url = f"data:{file.content_type};base64,{file_data}"
    
    # Update dog
    await database.dogs.update_one(
        {"id": dog_id},
        {"$set": {"vaccination_file_url": file_url}}
    )
    
    return {"message": "Vaccination file uploaded successfully"}

# ==================== BOOKING ROUTES ====================

@api_router.post("/bookings", response_model=BookingResponse)
async def create_booking(booking_data: BookingCreate, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Only customers can create bookings. Staff should use /bookings/admin endpoint")
    
    # Calculate nights
    nights = (booking_data.check_out_date - booking_data.check_in_date).days
    if nights <= 0:
        raise HTTPException(status_code=400, detail="Invalid date range")
    
    # Check if dates include holidays
    is_holiday = False
    holidays = ["2025-12-25", "2025-12-31", "2025-07-04", "2025-11-28", "2026-12-25", "2026-12-31", "2026-07-04", "2026-11-28"]
    for holiday_date in holidays:
        holiday = datetime.fromisoformat(holiday_date)
        if booking_data.check_in_date.date() <= holiday.date() < booking_data.check_out_date.date():
            is_holiday = True
            break
    
    # Pricing calculation
    base_price = 50.0  # per night per dog
    total_price = base_price * nights * len(booking_data.dog_ids)
    
    # Holiday surcharge (20%)
    if is_holiday:
        total_price *= 1.20
    
    # Separate playtime fee
    separate_playtime_fee = 0.0
    if booking_data.needs_separate_playtime:
        separate_playtime_fee = 6.0 * nights  # $6 per day
        total_price += separate_playtime_fee
    
    booking = Booking(
        **booking_data.model_dump(),
        household_id=user.household_id,
        status=BookingStatus.PENDING,
        total_price=total_price,
        is_holiday_pricing=is_holiday,
        separate_playtime_fee=separate_playtime_fee
    )
    
    doc = booking.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['check_in_date'] = doc['check_in_date'].isoformat()
    doc['check_out_date'] = doc['check_out_date'].isoformat()
    
    await database.bookings.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "booking", booking.id)
    
    return BookingResponse(**booking.model_dump())

@api_router.post("/bookings/admin", response_model=BookingResponse)
async def create_booking_admin(
    booking_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create booking on behalf of customer (staff/admin only)"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff or Admin access required")
    
    # Get customer by ID
    customer_id = booking_data.get('customer_id')
    if not customer_id:
        raise HTTPException(status_code=400, detail="Customer ID is required")
    
    customer = await database.users.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Parse dates
    check_in_date = datetime.fromisoformat(booking_data['check_in_date'].replace('Z', '+00:00')) if isinstance(booking_data['check_in_date'], str) else booking_data['check_in_date']
    check_out_date = datetime.fromisoformat(booking_data['check_out_date'].replace('Z', '+00:00')) if isinstance(booking_data['check_out_date'], str) else booking_data['check_out_date']
    
    # Calculate nights
    nights = (check_out_date - check_in_date).days
    if nights <= 0:
        raise HTTPException(status_code=400, detail="Invalid date range")
    
    dog_ids = booking_data.get('dog_ids', [])
    if not dog_ids:
        raise HTTPException(status_code=400, detail="At least one dog is required")
    
    # Check if dates include holidays
    is_holiday = False
    holidays = ["2025-12-25", "2025-12-31", "2025-07-04", "2025-11-28", "2026-12-25", "2026-12-31", "2026-07-04", "2026-11-28"]
    for holiday_date in holidays:
        holiday = datetime.fromisoformat(holiday_date)
        if check_in_date.date() <= holiday.date() < check_out_date.date():
            is_holiday = True
            break
    
    # Pricing calculation
    base_price = 50.0
    total_price = base_price * nights * len(dog_ids)
    
    if is_holiday:
        total_price *= 1.20
    
    separate_playtime_fee = 0.0
    needs_separate_playtime = booking_data.get('needs_separate_playtime', False)
    if needs_separate_playtime:
        separate_playtime_fee = 6.0 * nights
        total_price += separate_playtime_fee
    
    # Payment type: immediate or invoice
    payment_type = booking_data.get('payment_type', 'invoice')  # 'immediate' or 'invoice'
    payment_status = 'pending'
    
    # Get location (default to main kennel)
    location_id = booking_data.get('location_id')
    if not location_id:
        location = await database.locations.find_one({}, {"_id": 0})
        location_id = location['id'] if location else 'main-kennel'
    
    booking = Booking(
        dog_ids=dog_ids,
        location_id=location_id,
        accommodation_type=booking_data.get('accommodation_type', 'room'),
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        notes=booking_data.get('notes', ''),
        special_request=booking_data.get('special_request', ''),
        needs_separate_playtime=needs_separate_playtime,
        household_id=customer['household_id'],
        customer_id=customer_id,
        status=BookingStatus.PENDING if payment_type == 'invoice' else BookingStatus.PENDING,
        payment_status=payment_status,
        payment_type=payment_type,
        total_price=round(total_price, 2),
        is_holiday_pricing=is_holiday,
        separate_playtime_fee=separate_playtime_fee,
        created_by=user.id
    )
    
    doc = booking.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['check_in_date'] = doc['check_in_date'].isoformat()
    doc['check_out_date'] = doc['check_out_date'].isoformat()
    
    await database.bookings.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "booking", booking.id, {
        "customer_id": customer_id,
        "payment_type": payment_type,
        "created_by_staff": True
    })
    
    return BookingResponse(**booking.model_dump())

@api_router.get("/bookings", response_model=List[BookingResponse])
async def get_bookings(credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    
    query = {}
    if user.role == UserRole.CUSTOMER:
        query = {"household_id": user.household_id}
    elif user.role == UserRole.STAFF:
        query = {"location_id": user.location_id}
    
    bookings = await database.bookings.find(query, {"_id": 0}).to_list(1000)
    
    # Deserialize dates
    for booking in bookings:
        if isinstance(booking['check_in_date'], str):
            booking['check_in_date'] = datetime.fromisoformat(booking['check_in_date'])
        if isinstance(booking['check_out_date'], str):
            booking['check_out_date'] = datetime.fromisoformat(booking['check_out_date'])
    
    return [BookingResponse(**booking) for booking in bookings]

@api_router.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: str, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    """Get a single booking by ID"""
    user = await get_current_user(credentials, database)
    
    booking = await database.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check access - customers can only see their own bookings
    if user.role == UserRole.CUSTOMER and booking.get("household_id") != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Deserialize dates
    if isinstance(booking.get('check_in_date'), str):
        booking['check_in_date'] = datetime.fromisoformat(booking['check_in_date'])
    if isinstance(booking.get('check_out_date'), str):
        booking['check_out_date'] = datetime.fromisoformat(booking['check_out_date'])
    
    return BookingResponse(**booking)

@api_router.patch("/bookings/{booking_id}/status")
async def update_booking_status(booking_id: str, status: BookingStatus, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff or Admin access required")
    
    update_data = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    
    # Track check-in/check-out timestamps
    if status == BookingStatus.CHECKED_IN:
        update_data["checked_in_at"] = datetime.now(timezone.utc).isoformat()
        await create_audit_log(user.id, AuditAction.CHECK_IN, "booking", booking_id)
    elif status == BookingStatus.CHECKED_OUT:
        update_data["checked_out_at"] = datetime.now(timezone.utc).isoformat()
        await create_audit_log(user.id, AuditAction.CHECK_OUT, "booking", booking_id)
    
    result = await database.bookings.update_one(
        {"id": booking_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "booking", booking_id, {"status": status})
    
    return {"message": "Status updated", "status": status}

@api_router.patch("/bookings/{booking_id}")
async def update_booking(
    booking_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update booking details (staff/admin only)"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff or Admin access required")
    
    # Get existing booking
    booking = await database.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Build update document
    allowed_fields = ['dog_ids', 'location_id', 'accommodation_type', 'check_in_date', 
                      'check_out_date', 'notes', 'special_request', 'needs_separate_playtime',
                      'status', 'modification_reason']
    
    update_doc = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    for field in allowed_fields:
        if field in update_data:
            update_doc[field] = update_data[field]
    
    # Recalculate price if dates changed
    if 'check_in_date' in update_doc or 'check_out_date' in update_doc:
        check_in = update_doc.get('check_in_date', booking['check_in_date'])
        check_out = update_doc.get('check_out_date', booking['check_out_date'])
        
        if isinstance(check_in, str):
            check_in = datetime.fromisoformat(check_in.replace('Z', '+00:00'))
        if isinstance(check_out, str):
            check_out = datetime.fromisoformat(check_out.replace('Z', '+00:00'))
        
        nights = (check_out - check_in).days
        dog_count = len(update_doc.get('dog_ids', booking.get('dog_ids', [])))
        base_price = 50.0
        total = base_price * nights * dog_count
        
        # Check for holiday pricing
        holidays = ['2025-12-25', '2025-12-31', '2025-07-04', '2025-11-28', '2026-12-25', '2026-12-31']
        is_holiday = any(check_in.date() <= datetime.strptime(h, '%Y-%m-%d').date() < check_out.date() for h in holidays)
        if is_holiday:
            total *= 1.20
            update_doc['is_holiday_pricing'] = True
        
        # Separate playtime fee
        if update_doc.get('needs_separate_playtime', booking.get('needs_separate_playtime', False)):
            update_doc['separate_playtime_fee'] = 6.0 * nights
            total += update_doc['separate_playtime_fee']
        
        update_doc['total_price'] = round(total, 2)
    
    result = await database.bookings.update_one(
        {"id": booking_id},
        {"$set": update_doc}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "booking", booking_id, {
        "fields_updated": list(update_doc.keys()),
        "reason": update_data.get('modification_reason', '')
    })
    
    return {"message": "Booking updated successfully"}

@api_router.delete("/bookings/{booking_id}")
async def delete_booking(
    booking_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Delete/Cancel a booking (staff/admin only)"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff or Admin access required")
    
    # Soft delete - mark as cancelled
    result = await database.bookings.update_one(
        {"id": booking_id},
        {"$set": {"status": BookingStatus.CANCELLED, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "booking", booking_id)
    
    return {"message": "Booking cancelled"}

@api_router.patch("/bookings/{booking_id}/items")
async def update_items_checklist(
    booking_id: str,
    items: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff or Admin access required")
    
    result = await database.bookings.update_one(
        {"id": booking_id},
        {"$set": {"items_checklist": items, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "booking", booking_id, {"items_updated": True})
    
    return {"message": "Items checklist updated", "items": items}

class ConfirmPaymentRequest(BaseModel):
    payment_method: str
    source_id: Optional[str] = None  # Square payment token

@api_router.post("/bookings/{booking_id}/confirm-payment")
async def confirm_payment(
    booking_id: str,
    request: ConfirmPaymentRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Process payment - uses Square if configured, otherwise mock mode"""
    user = await get_current_user(credentials, database)
    payment_method = request.payment_method
    source_id = request.source_id
    import uuid
    
    # Get booking details
    booking = await database.bookings.find_one({"id": booking_id, "household_id": user.household_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    square_token = os.environ.get('SQUARE_ACCESS_TOKEN', '')
    
    if square_token and source_id:
        # Real Square payment processing
        try:
            from square import Square
            
            square_client = Square(
                access_token=square_token,
                environment=os.environ.get('SQUARE_ENVIRONMENT', 'sandbox')
            )
            
            # Create payment
            idempotency_key = f"{booking_id}:{str(uuid.uuid4())}"
            payment_result = square_client.payments.create_payment({
                "source_id": source_id,
                "amount_money": {
                    "amount": int(booking['total_price'] * 100),  # Convert to cents
                    "currency": "USD"
                },
                "idempotency_key": idempotency_key,
                "reference_id": booking_id,
            })
            
            if payment_result.is_success:
                payment = payment_result.body.get('payment', {})
                payment_id = payment.get('id', '')
                payment_status = payment.get('status', 'COMPLETED')
                
                await database.bookings.update_one(
                    {"id": booking_id},
                    {"$set": {
                        "payment_status": "completed" if payment_status == "COMPLETED" else "pending",
                        "payment_intent_id": payment_id,
                        "status": BookingStatus.CONFIRMED if payment_status == "COMPLETED" else BookingStatus.PENDING,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                
                await create_audit_log(user.id, AuditAction.PAYMENT, "booking", booking_id, {
                    "payment_id": payment_id,
                    "method": "square",
                    "amount": booking['total_price']
                })
                
                return {
                    "message": "Payment processed successfully via Square",
                    "payment_id": payment_id,
                    "status": payment_status.lower()
                }
            else:
                errors = payment_result.errors
                error_msg = errors[0].get('detail', 'Payment failed') if errors else 'Payment failed'
                raise HTTPException(status_code=400, detail=error_msg)
                
        except ImportError:
            logging.warning("Square SDK not installed, falling back to mock")
        except Exception as e:
            logging.error(f"Square payment error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Payment processing failed: {str(e)}")
    
    # Mock payment fallback
    mock_payment_id = f"mock_pay_{str(uuid.uuid4())[:8]}"
    
    result = await database.bookings.update_one(
        {"id": booking_id, "household_id": user.household_id},
        {"$set": {
            "payment_status": "completed",
            "payment_intent_id": mock_payment_id,
            "status": BookingStatus.CONFIRMED,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    await create_audit_log(user.id, AuditAction.PAYMENT, "booking", booking_id, {
        "payment_id": mock_payment_id,
        "method": payment_method,
        "mode": "mock"
    })
    
    return {
        "message": "Payment processed successfully (mock mode - configure Square keys for real payments)",
        "payment_id": mock_payment_id,
        "status": "completed",
        "mock": True
    }

# ==================== DAILY UPDATES ROUTES ====================

@api_router.post("/daily-updates", response_model=DailyUpdateResponse)
async def create_daily_update(update_data: DailyUpdateCreate, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    update = DailyUpdate(
        **update_data.model_dump(),
        date=datetime.now(timezone.utc),
        status=UpdateStatus.DRAFT
    )
    
    doc = update.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['date'] = doc['date'].isoformat()
    
    await database.daily_updates.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "daily_update", update.id)
    
    return DailyUpdateResponse(**update.model_dump())

@api_router.post("/daily-updates/{update_id}/snippets")
async def add_staff_snippet(
    update_id: str,
    snippet_text: str = Form(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    snippet = {
        "staff_id": user.id,
        "staff_name": user.full_name,
        "text": snippet_text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    result = await database.daily_updates.update_one(
        {"id": update_id},
        {"$push": {"staff_snippets": snippet}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Update not found")
    
    return {"message": "Snippet added", "snippet": snippet}

@api_router.post("/daily-updates/{update_id}/media")
async def add_media_to_update(
    update_id: str,
    dog_ids: str = Form(...),
    caption: Optional[str] = Form(None),
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    # Read file content
    content = await file.read()
    
    # In production, upload to S3/Cloud Storage
    # For now, store as base64 in database (NOT RECOMMENDED for production)
    file_data = base64.b64encode(content).decode('utf-8')
    file_url = f"data:{file.content_type};base64,{file_data[:100]}..."  # Truncated for demo
    
    # Parse dog IDs
    tagged_dogs = dog_ids.split(',') if dog_ids else []
    
    media_item = MediaItem(
        url=file_url,
        type="photo" if file.content_type.startswith("image") else "video",
        caption=caption,
        uploaded_by=user.id,
        dog_ids=tagged_dogs,
        watermarked=True,
        purchased=False
    )
    
    media_doc = media_item.model_dump()
    media_doc['uploaded_at'] = media_doc['uploaded_at'].isoformat()
    
    result = await database.daily_updates.update_one(
        {"id": update_id},
        {"$push": {"media_items": media_doc}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Update not found")
    
    return {"message": "Media added successfully", "media": media_doc}

@api_router.post("/daily-updates/{update_id}/reactions")
async def add_reaction(
    update_id: str,
    reaction: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    user = await get_current_user(credentials, database)
    
    reaction_doc = {
        "user_id": user.id,
        "reaction": reaction,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    result = await database.daily_updates.update_one(
        {"id": update_id},
        {"$push": {"reactions": reaction_doc}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Update not found")
    
    return {"message": "Reaction added", "reaction": reaction_doc}

@api_router.post("/daily-updates/{update_id}/comments")
async def add_comment(
    update_id: str,
    text: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    user = await get_current_user(credentials, database)
    
    comment_doc = {
        "user_id": user.id,
        "user_name": user.full_name,
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    result = await database.daily_updates.update_one(
        {"id": update_id},
        {"$push": {"comments": comment_doc}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Update not found")
    
    return {"message": "Comment added", "comment": comment_doc}

@api_router.post("/daily-updates/{update_id}/purchase-photos")
async def purchase_photos(
    update_id: str,
    payment_method: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Purchase photos to remove watermark (mock payment)"""
    user = await get_current_user(credentials, database)
    
    update_doc = await database.daily_updates.find_one({"id": update_id}, {"_id": 0})
    if not update_doc:
        raise HTTPException(status_code=404, detail="Update not found")
    
    if user.role == UserRole.CUSTOMER and update_doc['household_id'] != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Mock payment
    import uuid
    payment_id = f"photo_purchase_{str(uuid.uuid4())[:8]}"
    
    # Mark all media as purchased
    await database.daily_updates.update_one(
        {"id": update_id},
        {"$set": {"media_items.$[].purchased": True, "media_items.$[].watermarked": False}}
    )
    
    await create_audit_log(user.id, AuditAction.PAYMENT, "photo_purchase", update_id, {
        "payment_id": payment_id,
        "amount": 9.99
    })
    
    return {
        "message": "Photos purchased successfully! Watermarks removed.",
        "payment_id": payment_id,
        "amount": 9.99
    }

@api_router.post("/daily-updates/{update_id}/generate-summary")
async def generate_summary(update_id: str, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    update_doc = await database.daily_updates.find_one({"id": update_id}, {"_id": 0})
    if not update_doc:
        raise HTTPException(status_code=404, detail="Update not found")
    
    # Get dog names from booking
    booking_doc = await database.bookings.find_one({"id": update_doc['booking_id']}, {"_id": 0})
    if not booking_doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    dog_names = []
    for dog_id in booking_doc['dog_ids']:
        dog = await database.dogs.find_one({"id": dog_id}, {"_id": 0})
        if dog:
            dog_names.append(dog['name'])
    
    # Generate AI summary from staff snippets
    staff_snippets = update_doc.get('staff_snippets', [])
    if not staff_snippets:
        raise HTTPException(status_code=400, detail="No staff snippets to summarize")
    
    summary = await generate_daily_summary(
        dog_names=dog_names,
        staff_snippets=staff_snippets,
        media_count=len(update_doc.get('media_items', []))
    )
    
    # Update document
    await database.daily_updates.update_one(
        {"id": update_id},
        {"$set": {"ai_summary": summary, "status": UpdateStatus.PENDING_APPROVAL}}
    )
    
    return {"message": "Summary generated", "summary": summary}

@api_router.post("/daily-updates/{update_id}/approve")
async def approve_and_send_update(
    update_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    result = await database.daily_updates.update_one(
        {"id": update_id},
        {"$set": {
            "status": UpdateStatus.SENT,
            "approved_by": user.id,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Update not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "daily_update", update_id, {"action": "approved_and_sent"})
    
    return {"message": "Update approved and sent to customer"}

@api_router.get("/daily-updates", response_model=List[DailyUpdateResponse])
async def get_daily_updates(credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    
    query = {}
    if user.role == UserRole.CUSTOMER:
        query = {"household_id": user.household_id}
    
    updates = await database.daily_updates.find(query, {"_id": 0}).to_list(1000)
    
    # Deserialize dates
    for update in updates:
        if isinstance(update['date'], str):
            update['date'] = datetime.fromisoformat(update['date'])
        if update.get('sent_at') and isinstance(update['sent_at'], str):
            update['sent_at'] = datetime.fromisoformat(update['sent_at'])
        for media in update.get('media_items', []):
            if isinstance(media['uploaded_at'], str):
                media['uploaded_at'] = datetime.fromisoformat(media['uploaded_at'])
    
    return [DailyUpdateResponse(**update) for update in updates]

# ==================== TASK ROUTES ====================

@api_router.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    task = Task(**task_data.model_dump(), status=TaskStatus.PENDING)
    doc = task.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('due_date'):
        doc['due_date'] = doc['due_date'].isoformat()
    
    await database.tasks.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "task", task.id)
    
    return TaskResponse(**task.model_dump())

@api_router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    
    query = {}
    if user.role == UserRole.STAFF:
        query = {"$or": [{"assigned_to": user.id}, {"location_id": user.location_id}]}
    
    tasks = await database.tasks.find(query, {"_id": 0}).to_list(1000)
    
    # Deserialize dates
    for task in tasks:
        if task.get('due_date') and isinstance(task['due_date'], str):
            task['due_date'] = datetime.fromisoformat(task['due_date'])
        if task.get('completed_at') and isinstance(task['completed_at'], str):
            task['completed_at'] = datetime.fromisoformat(task['completed_at'])
    
    return [TaskResponse(**task) for task in tasks]

@api_router.patch("/tasks/{task_id}/complete")
async def complete_task(task_id: str, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    
    result = await database.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "status": TaskStatus.COMPLETED, 
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "completed_by": user.id,
            "completed_by_name": user.full_name
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "task", task_id, {"status": "completed"})
    
    return {"message": "Task completed"}

@api_router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update a task - Admin only"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    task = await database.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_doc = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    allowed_fields = ['title', 'description', 'priority', 'status', 'assigned_to', 'location_id', 'due_date', 'notes']
    for field in allowed_fields:
        if field in update_data and update_data[field] is not None:
            if field == 'due_date' and update_data[field]:
                update_doc[field] = update_data[field] if isinstance(update_data[field], str) else update_data[field].isoformat()
            else:
                update_doc[field] = update_data[field]
    
    await database.tasks.update_one({"id": task_id}, {"$set": update_doc})
    await create_audit_log(user.id, AuditAction.UPDATE, "task", task_id, update_doc)
    
    updated_task = await database.tasks.find_one({"id": task_id}, {"_id": 0})
    if updated_task.get('due_date') and isinstance(updated_task['due_date'], str):
        updated_task['due_date'] = datetime.fromisoformat(updated_task['due_date'])
    
    return TaskResponse(**updated_task)

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await database.tasks.delete_one({"id": task_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "task", task_id)
    
    return {"message": "Task deleted"}

# ==================== TIME TRACKING ROUTES ====================

@api_router.get("/time-entries", response_model=List[TimeEntryResponse])
async def get_time_entries(
    staff_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get time entries - staff see their own, admins see all"""
    user = await get_current_user(credentials, database)
    
    query = {}
    if user.role == UserRole.STAFF:
        query = {"staff_id": user.id}
    elif user.role == UserRole.ADMIN and staff_id:
        query = {"staff_id": staff_id}
    elif user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    
    entries = await database.time_entries.find(query, {"_id": 0}).sort("clock_in", -1).to_list(1000)
    
    # Deserialize dates
    for entry in entries:
        if isinstance(entry['clock_in'], str):
            entry['clock_in'] = datetime.fromisoformat(entry['clock_in'])
        if entry.get('clock_out') and isinstance(entry['clock_out'], str):
            entry['clock_out'] = datetime.fromisoformat(entry['clock_out'])
    
    return [TimeEntryResponse(**entry) for entry in entries]

@api_router.get("/time-entries/current")
async def get_current_time_entry(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Check if user is currently clocked in"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff access only")
    
    active_entry = await database.time_entries.find_one({
        "staff_id": user.id,
        "clock_out": None
    }, {"_id": 0})
    
    if active_entry:
        if isinstance(active_entry['clock_in'], str):
            active_entry['clock_in'] = datetime.fromisoformat(active_entry['clock_in'])
        return {"clocked_in": True, "entry": TimeEntryResponse(**active_entry)}
    
    return {"clocked_in": False, "entry": None}

@api_router.post("/time-entries/clock-in", response_model=TimeEntryResponse)
async def clock_in(entry_data: TimeEntryCreate, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff access only")
    
    # Check if already clocked in
    active_entry = await database.time_entries.find_one({
        "staff_id": user.id,
        "clock_out": None
    }, {"_id": 0})
    
    if active_entry:
        raise HTTPException(status_code=400, detail="Already clocked in")
    
    # Use authenticated user's ID, not the one from request body
    entry = TimeEntry(
        staff_id=user.id,
        location_id=entry_data.location_id,
        clock_in=datetime.now(timezone.utc)
    )
    doc = entry.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['clock_in'] = doc['clock_in'].isoformat()
    
    await database.time_entries.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "time_entry", entry.id, {"action": "clock_in"})
    
    return TimeEntryResponse(**entry.model_dump())

@api_router.post("/time-entries/clock-out")
async def clock_out(credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff access only")
    
    result = await database.time_entries.update_one(
        {"staff_id": user.id, "clock_out": None},
        {"$set": {"clock_out": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Not clocked in")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "time_entry", user.id, {"action": "clock_out"})
    
    return {"message": "Clocked out successfully"}

# ==================== TIMESHEET MODIFICATION REQUESTS ====================

from models import TimeModificationRequest, TimeModificationRequestCreate, TimeModificationRequestResponse, TimeModificationStatus, Shift, ShiftCreate, ShiftResponse

@api_router.post("/time-entries/modification-request")
async def create_modification_request(
    request_data: TimeModificationRequestCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Staff request modification to a time entry"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff access only")
    
    # Get the original time entry
    entry = await database.time_entries.find_one({"id": request_data.time_entry_id, "staff_id": user.id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    mod_request = TimeModificationRequest(
        time_entry_id=request_data.time_entry_id,
        staff_id=user.id,
        staff_name=user.full_name,
        original_clock_in=datetime.fromisoformat(entry['clock_in']) if isinstance(entry['clock_in'], str) else entry['clock_in'],
        original_clock_out=datetime.fromisoformat(entry['clock_out']) if entry.get('clock_out') and isinstance(entry['clock_out'], str) else entry.get('clock_out'),
        requested_clock_in=request_data.requested_clock_in,
        requested_clock_out=request_data.requested_clock_out,
        reason=request_data.reason
    )
    
    doc = mod_request.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['original_clock_in'] = doc['original_clock_in'].isoformat()
    if doc['original_clock_out']:
        doc['original_clock_out'] = doc['original_clock_out'].isoformat()
    doc['requested_clock_in'] = doc['requested_clock_in'].isoformat()
    if doc['requested_clock_out']:
        doc['requested_clock_out'] = doc['requested_clock_out'].isoformat()
    
    await database.time_modification_requests.insert_one(doc)
    
    return {"message": "Modification request submitted", "request_id": mod_request.id}

@api_router.get("/time-entries/modification-requests")
async def get_modification_requests(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get modification requests - staff see their own, admins see all"""
    user = await get_current_user(credentials, database)
    
    query = {}
    if user.role == UserRole.STAFF:
        query = {"staff_id": user.id}
    elif user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    
    requests = await database.time_modification_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return requests

@api_router.patch("/time-entries/modification-requests/{request_id}")
async def review_modification_request(
    request_id: str,
    action: str,  # approve or reject
    review_notes: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Admin approve/reject modification request"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    mod_request = await database.time_modification_requests.find_one({"id": request_id}, {"_id": 0})
    if not mod_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    new_status = TimeModificationStatus.APPROVED if action == "approve" else TimeModificationStatus.REJECTED
    
    # Update the request
    await database.time_modification_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": new_status,
            "reviewed_by": user.id,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_notes": review_notes
        }}
    )
    
    # If approved, update the original time entry
    if action == "approve":
        update_doc = {
            "clock_in": mod_request['requested_clock_in'],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if mod_request.get('requested_clock_out'):
            update_doc["clock_out"] = mod_request['requested_clock_out']
        
        await database.time_entries.update_one(
            {"id": mod_request['time_entry_id']},
            {"$set": update_doc}
        )
    
    await create_audit_log(user.id, AuditAction.UPDATE, "time_modification_request", request_id, {"action": action})
    
    return {"message": f"Request {action}d", "status": new_status}

@api_router.post("/time-entries", response_model=TimeEntryResponse)
async def create_time_entry(
    entry_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Admin create time entry"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    entry = TimeEntry(
        staff_id=entry_data['staff_id'],
        location_id=entry_data.get('location_id', 'main-kennel'),
        clock_in=datetime.fromisoformat(entry_data['clock_in']),
        clock_out=datetime.fromisoformat(entry_data['clock_out']) if entry_data.get('clock_out') else None,
        notes=entry_data.get('notes')
    )
    
    doc = entry.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['clock_in'] = doc['clock_in'].isoformat()
    if doc.get('clock_out'):
        doc['clock_out'] = doc['clock_out'].isoformat()
    
    await database.time_entries.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "time_entry", entry.id)
    
    return TimeEntryResponse(**entry.model_dump())

@api_router.patch("/time-entries/{entry_id}")
async def update_time_entry(
    entry_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Admin update time entry"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_doc = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if 'clock_in' in update_data:
        update_doc['clock_in'] = update_data['clock_in']
    if 'clock_out' in update_data:
        update_doc['clock_out'] = update_data['clock_out']
    if 'notes' in update_data:
        update_doc['notes'] = update_data['notes']
    
    result = await database.time_entries.update_one({"id": entry_id}, {"$set": update_doc})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "time_entry", entry_id)
    
    return {"message": "Time entry updated"}

@api_router.delete("/time-entries/{entry_id}")
async def delete_time_entry(
    entry_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Admin delete time entry"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await database.time_entries.delete_one({"id": entry_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "time_entry", entry_id)
    
    return {"message": "Time entry deleted"}

# ==================== SHIFT SCHEDULING ====================

@api_router.post("/shifts", response_model=ShiftResponse)
async def create_shift(
    shift_data: ShiftCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create a shift (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get staff name
    staff = await database.users.find_one({"id": shift_data.staff_id}, {"_id": 0})
    staff_name = staff['full_name'] if staff else "Unknown"
    
    shift = Shift(**shift_data.model_dump(), staff_name=staff_name)
    doc = shift.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['start_time'] = doc['start_time'].isoformat()
    doc['end_time'] = doc['end_time'].isoformat()
    
    await database.shifts.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "shift", shift.id)
    
    return ShiftResponse(**shift.model_dump())

@api_router.get("/shifts", response_model=List[ShiftResponse])
async def get_shifts(
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get shifts - staff see their own, admins see all"""
    user = await get_current_user(credentials, database)
    
    query = {}
    if user.role == UserRole.STAFF:
        query["staff_id"] = user.id
    elif user.role == UserRole.ADMIN and staff_id:
        query["staff_id"] = staff_id
    elif user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if start_date:
        query["start_time"] = {"$gte": start_date}
    if end_date:
        if "start_time" in query:
            query["start_time"]["$lte"] = end_date
        else:
            query["start_time"] = {"$lte": end_date}
    
    shifts = await database.shifts.find(query, {"_id": 0}).sort("start_time", 1).to_list(1000)
    
    for shift in shifts:
        if isinstance(shift['start_time'], str):
            shift['start_time'] = datetime.fromisoformat(shift['start_time'])
        if isinstance(shift['end_time'], str):
            shift['end_time'] = datetime.fromisoformat(shift['end_time'])
    
    return [ShiftResponse(**s) for s in shifts]

@api_router.patch("/shifts/{shift_id}")
async def update_shift(
    shift_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update shift (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_doc = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    allowed_fields = ['staff_id', 'start_time', 'end_time', 'notes', 'location_id']
    for field in allowed_fields:
        if field in update_data:
            update_doc[field] = update_data[field]
    
    # Update staff name if staff_id changed
    if 'staff_id' in update_doc:
        staff = await database.users.find_one({"id": update_doc['staff_id']}, {"_id": 0})
        update_doc['staff_name'] = staff['full_name'] if staff else "Unknown"
    
    result = await database.shifts.update_one({"id": shift_id}, {"$set": update_doc})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "shift", shift_id)
    
    return {"message": "Shift updated"}

@api_router.delete("/shifts/{shift_id}")
async def delete_shift(
    shift_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Delete shift (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await database.shifts.delete_one({"id": shift_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "shift", shift_id)
    
    return {"message": "Shift deleted"}

# ==================== INCIDENT ROUTES ====================

@api_router.post("/incidents", response_model=IncidentResponse)
async def create_incident(incident_data: IncidentCreate, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    incident = Incident(**incident_data.model_dump(), reported_by=user.id)
    doc = incident.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.incidents.insert_one(doc)
    await create_audit_log(user.id, AuditAction.INCIDENT, "incident", incident.id)
    
    return IncidentResponse(**incident.model_dump())

@api_router.get("/incidents", response_model=List[IncidentResponse])
async def get_incidents(credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    incidents = await database.incidents.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [IncidentResponse(**inc) for inc in incidents]

@api_router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    incident = await database.incidents.find_one({"id": incident_id}, {"_id": 0})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return IncidentResponse(**incident)

@api_router.patch("/incidents/{incident_id}")
async def update_incident(
    incident_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    update_doc = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    allowed_fields = ['description', 'severity', 'dog_ids', 'resolution', 'status']
    for field in allowed_fields:
        if field in update_data:
            update_doc[field] = update_data[field]
    
    result = await database.incidents.update_one({"id": incident_id}, {"$set": update_doc})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "incident", incident_id)
    
    return {"message": "Incident updated"}

@api_router.delete("/incidents/{incident_id}")
async def delete_incident(
    incident_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await database.incidents.delete_one({"id": incident_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "incident", incident_id)
    
    return {"message": "Incident deleted"}

# ==================== ADMIN CUSTOMER MANAGEMENT ====================

@api_router.post("/admin/customers")
async def create_customer(
    customer_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Admin create a customer"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if email exists
    existing = await database.users.find_one({"email": customer_data['email']}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    import uuid
    household_id = str(uuid.uuid4())
    
    new_user = User(
        email=customer_data['email'],
        hashed_password=hash_password(customer_data.get('password', 'TempPass123!')),
        full_name=customer_data['full_name'],
        role=UserRole.CUSTOMER,
        household_id=household_id,
        phone=customer_data.get('phone'),
        is_active=customer_data.get('is_active', True),
        address=customer_data.get('address'),
        city=customer_data.get('city'),
        state=customer_data.get('state'),
        zip_code=customer_data.get('zip_code'),
        emergency_contact=customer_data.get('emergency_contact'),
        emergency_phone=customer_data.get('emergency_phone'),
        notes=customer_data.get('notes')
    )
    
    doc = new_user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.users.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "customer", new_user.id)
    
    return {"message": "Customer created", "id": new_user.id, "temp_password": customer_data.get('password', 'TempPass123!')}

@api_router.patch("/admin/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Admin update a customer"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_doc = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    allowed_fields = ['full_name', 'email', 'phone', 'is_active', 'notes', 'address', 'city', 'state', 'zip_code', 'emergency_contact', 'emergency_phone']
    for field in allowed_fields:
        if field in update_data:
            update_doc[field] = update_data[field]
    
    # Handle password update separately
    if 'password' in update_data and update_data['password']:
        update_doc['hashed_password'] = hash_password(update_data['password'])
    
    result = await database.users.update_one({"id": customer_id, "role": UserRole.CUSTOMER}, {"$set": update_doc})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "customer", customer_id)
    
    return {"message": "Customer updated"}

@api_router.delete("/admin/customers/{customer_id}")
async def delete_customer(
    customer_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Admin delete/deactivate a customer"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Soft delete - deactivate
    result = await database.users.update_one(
        {"id": customer_id, "role": UserRole.CUSTOMER},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "customer", customer_id)
    
    return {"message": "Customer deactivated"}

# ==================== REVIEW ROUTES ====================

@api_router.post("/reviews", response_model=ReviewResponse)
async def create_review(review_data: ReviewCreate, credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Customers only")
    
    review = Review(**review_data.model_dump(), household_id=user.household_id)
    doc = review.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.reviews.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "review", review.id)
    
    return ReviewResponse(**review.model_dump())

@api_router.get("/reviews", response_model=List[ReviewResponse])
async def get_reviews(database=Depends(get_db)):
    reviews = await database.reviews.find({"approved": True}, {"_id": 0}).to_list(100)
    return [ReviewResponse(**rev) for rev in reviews]

# ==================== AUDIT LOG ROUTES ====================

@api_router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    logs = await database.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).limit(1000).to_list(1000)
    
    # Deserialize dates
    for log in logs:
        if isinstance(log['created_at'], str):
            log['created_at'] = datetime.fromisoformat(log['created_at'])
    
    return [AuditLogResponse(**log) for log in logs]

# ==================== ADMIN USER MANAGEMENT ====================

@api_router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(
    role: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get all users (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if role:
        query["role"] = role
    
    users = await database.users.find(query, {"_id": 0, "hashed_password": 0, "reset_token": 0, "reset_token_expiry": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]

@api_router.patch("/admin/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Enable/disable user account (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await database.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": is_active, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "user", user_id, {"is_active": is_active})
    
    return {"message": f"User {'activated' if is_active else 'deactivated'}"}

# ==================== DASHBOARD STATS ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(credentials: HTTPAuthorizationCredentials = Depends(security), database=Depends(get_db)):
    user = await get_current_user(credentials, database)
    
    stats = {}
    
    if user.role == UserRole.ADMIN:
        stats['total_customers'] = await database.users.count_documents({"role": UserRole.CUSTOMER})
        stats['total_dogs'] = await database.dogs.count_documents({})
        stats['total_bookings'] = await database.bookings.count_documents({})
        stats['active_bookings'] = await database.bookings.count_documents({"status": BookingStatus.CHECKED_IN})
        stats['total_staff'] = await database.users.count_documents({"role": UserRole.STAFF})
        
    elif user.role == UserRole.STAFF:
        stats['todays_tasks'] = await database.tasks.count_documents({
            "assigned_to": user.id,
            "status": {"$ne": TaskStatus.COMPLETED}
        })
        stats['active_bookings'] = await database.bookings.count_documents({
            "location_id": user.location_id,
            "status": BookingStatus.CHECKED_IN
        })
        
    elif user.role == UserRole.CUSTOMER:
        stats['my_dogs'] = await database.dogs.count_documents({"household_id": user.household_id})
        stats['my_bookings'] = await database.bookings.count_documents({"household_id": user.household_id})
        stats['upcoming_bookings'] = await database.bookings.count_documents({
            "household_id": user.household_id,
            "status": BookingStatus.CONFIRMED
        })
    
    return stats

# ==================== REVENUE ANALYTICS ====================

@api_router.get("/admin/revenue/summary")
async def get_revenue_summary(
    period: str = "month",  # week, month, year
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get revenue summary for dashboard"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    
    # Calculate date ranges
    if period == "week":
        start_date = now - timedelta(days=7)
        prev_start = start_date - timedelta(days=7)
        prev_end = start_date
    elif period == "year":
        start_date = now - timedelta(days=365)
        prev_start = start_date - timedelta(days=365)
        prev_end = start_date
    else:  # month (default)
        start_date = now - timedelta(days=30)
        prev_start = start_date - timedelta(days=30)
        prev_end = start_date
    
    # Get confirmed/completed bookings in current period
    current_bookings = await database.bookings.find({
        "status": {"$in": [BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]},
        "created_at": {"$gte": start_date.isoformat()}
    }, {"_id": 0}).to_list(10000)
    
    # Get previous period bookings for comparison
    prev_bookings = await database.bookings.find({
        "status": {"$in": [BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]},
        "created_at": {"$gte": prev_start.isoformat(), "$lt": prev_end.isoformat()}
    }, {"_id": 0}).to_list(10000)
    
    # Calculate totals
    current_revenue = sum(float(b.get('total_price', 0)) for b in current_bookings)
    prev_revenue = sum(float(b.get('total_price', 0)) for b in prev_bookings)
    
    # Calculate average stay duration
    total_nights = 0
    for b in current_bookings:
        try:
            check_in = datetime.fromisoformat(b['check_in_date'].replace('Z', '+00:00')) if isinstance(b['check_in_date'], str) else b['check_in_date']
            check_out = datetime.fromisoformat(b['check_out_date'].replace('Z', '+00:00')) if isinstance(b['check_out_date'], str) else b['check_out_date']
            total_nights += (check_out - check_in).days
        except (ValueError, KeyError, TypeError):
            pass
    
    avg_stay = total_nights / len(current_bookings) if current_bookings else 0
    
    # Revenue change percentage
    revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    
    return {
        "current_revenue": round(current_revenue, 2),
        "prev_revenue": round(prev_revenue, 2),
        "revenue_change_percent": round(revenue_change, 1),
        "total_bookings": len(current_bookings),
        "prev_bookings": len(prev_bookings),
        "avg_stay_nights": round(avg_stay, 1),
        "period": period,
        "period_start": start_date.isoformat(),
        "period_end": now.isoformat()
    }

@api_router.get("/admin/revenue/trends")
async def get_revenue_trends(
    period: str = "month",  # week, month, year
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get daily/weekly revenue trends for charting"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    
    # Determine grouping and range
    if period == "week":
        days = 7
        group_by = "day"
    elif period == "year":
        days = 365
        group_by = "month"
    else:  # month
        days = 30
        group_by = "day"
    
    start_date = now - timedelta(days=days)
    
    # Get all bookings in period
    bookings = await database.bookings.find({
        "status": {"$in": [BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]},
        "created_at": {"$gte": start_date.isoformat()}
    }, {"_id": 0}).to_list(10000)
    
    # Group by date
    trends = {}
    for b in bookings:
        try:
            created = b.get('created_at', '')
            if isinstance(created, str):
                date = datetime.fromisoformat(created.replace('Z', '+00:00'))
            else:
                date = created
            
            if group_by == "month":
                key = date.strftime("%Y-%m")
            else:
                key = date.strftime("%Y-%m-%d")
            
            if key not in trends:
                trends[key] = {"date": key, "revenue": 0, "bookings": 0}
            
            trends[key]["revenue"] += float(b.get('total_price', 0))
            trends[key]["bookings"] += 1
        except (ValueError, KeyError, TypeError):
            pass
    
    # Sort by date and return as list
    sorted_trends = sorted(trends.values(), key=lambda x: x["date"])
    
    # Round revenue values
    for t in sorted_trends:
        t["revenue"] = round(t["revenue"], 2)
    
    return sorted_trends

@api_router.get("/admin/revenue/by-accommodation")
async def get_revenue_by_accommodation(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get revenue breakdown by accommodation type"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all confirmed bookings
    bookings = await database.bookings.find({
        "status": {"$in": [BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]}
    }, {"_id": 0}).to_list(10000)
    
    # Group by accommodation type
    breakdown = {"room": {"count": 0, "revenue": 0}, "crate": {"count": 0, "revenue": 0}}
    
    for b in bookings:
        acc_type = b.get('accommodation_type', 'room')
        if acc_type in breakdown:
            breakdown[acc_type]["count"] += 1
            breakdown[acc_type]["revenue"] += float(b.get('total_price', 0))
    
    # Round values
    for key in breakdown:
        breakdown[key]["revenue"] = round(breakdown[key]["revenue"], 2)
    
    return breakdown

# ==================== CHAT ROUTES ====================

from models import Chat, ChatCreate, ChatResponse, ChatMessage, ChatMessageCreate, ChatMessageResponse, ChatType

@api_router.get("/chats", response_model=List[ChatResponse])
async def get_chats(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get all chats for current user"""
    user = await get_current_user(credentials, database)
    
    chats = await database.chats.find(
        {"participants": user.id},
        {"_id": 0}
    ).sort("last_message_at", -1).to_list(100)
    
    # Deserialize dates
    for chat in chats:
        if chat.get('last_message_at') and isinstance(chat['last_message_at'], str):
            chat['last_message_at'] = datetime.fromisoformat(chat['last_message_at'])
    
    return [ChatResponse(**chat) for chat in chats]

@api_router.post("/chats", response_model=ChatResponse)
async def create_chat(
    chat_data: ChatCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create a new chat or return existing one"""
    user = await get_current_user(credentials, database)
    
    # Get other participant
    other_user = await database.users.find_one({"id": chat_data.participant_id}, {"_id": 0})
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if chat already exists
    existing_chat = await database.chats.find_one({
        "participants": {"$all": [user.id, chat_data.participant_id]},
        "chat_type": chat_data.chat_type
    }, {"_id": 0})
    
    if existing_chat:
        if existing_chat.get('last_message_at') and isinstance(existing_chat['last_message_at'], str):
            existing_chat['last_message_at'] = datetime.fromisoformat(existing_chat['last_message_at'])
        return ChatResponse(**existing_chat)
    
    # Create new chat
    chat = Chat(
        chat_type=chat_data.chat_type,
        participants=[user.id, chat_data.participant_id],
        participant_names={user.id: user.full_name, chat_data.participant_id: other_user['full_name']},
        unread_count={user.id: 0, chat_data.participant_id: 0}
    )
    
    doc = chat.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.chats.insert_one(doc)
    
    return ChatResponse(**chat.model_dump())

@api_router.get("/chats/{chat_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    chat_id: str,
    limit: int = 50,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get messages for a chat"""
    user = await get_current_user(credentials, database)
    
    # Verify user is participant
    chat = await database.chats.find_one({"id": chat_id, "participants": user.id}, {"_id": 0})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    messages = await database.chat_messages.find(
        {"chat_id": chat_id},
        {"_id": 0}
    ).sort("created_at", 1).limit(limit).to_list(limit)
    
    # Mark messages as read
    await database.chat_messages.update_many(
        {"chat_id": chat_id, "sender_id": {"$ne": user.id}, "read": False},
        {"$set": {"read": True}}
    )
    
    # Reset unread count for this user
    await database.chats.update_one(
        {"id": chat_id},
        {"$set": {f"unread_count.{user.id}": 0}}
    )
    
    # Deserialize dates
    for msg in messages:
        if isinstance(msg['created_at'], str):
            msg['created_at'] = datetime.fromisoformat(msg['created_at'])
    
    return [ChatMessageResponse(**msg) for msg in messages]

@api_router.post("/chats/{chat_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    chat_id: str,
    message_data: ChatMessageCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Send a message in a chat"""
    user = await get_current_user(credentials, database)
    
    # Verify user is participant
    chat = await database.chats.find_one({"id": chat_id, "participants": user.id}, {"_id": 0})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    message = ChatMessage(
        chat_id=chat_id,
        sender_id=user.id,
        sender_name=user.full_name,
        sender_role=user.role,
        content=message_data.content
    )
    
    doc = message.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.chat_messages.insert_one(doc)
    
    # Update chat with last message and increment unread for other participants
    other_participant = [p for p in chat['participants'] if p != user.id][0]
    
    await database.chats.update_one(
        {"id": chat_id},
        {
            "$set": {
                "last_message": message.content[:100],
                "last_message_at": datetime.now(timezone.utc).isoformat()
            },
            "$inc": {f"unread_count.{other_participant}": 1}
        }
    )
    
    return ChatMessageResponse(**message.model_dump())

@api_router.get("/chat/users")
async def get_chat_users(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get users available for chat based on role"""
    user = await get_current_user(credentials, database)
    
    if user.role == UserRole.ADMIN:
        # Admins can chat with staff and customers
        users = await database.users.find(
            {"role": {"$in": [UserRole.STAFF, UserRole.CUSTOMER]}, "is_active": True},
            {"_id": 0, "hashed_password": 0}
        ).to_list(1000)
    elif user.role == UserRole.STAFF:
        # Staff can chat with admins
        users = await database.users.find(
            {"role": UserRole.ADMIN, "is_active": True},
            {"_id": 0, "hashed_password": 0}
        ).to_list(100)
    elif user.role == UserRole.CUSTOMER:
        # Customers can chat with admins (kennel)
        users = await database.users.find(
            {"role": UserRole.ADMIN, "is_active": True},
            {"_id": 0, "hashed_password": 0}
        ).to_list(100)
    else:
        users = []
    
    return [{"id": u['id'], "full_name": u['full_name'], "role": u['role'], "email": u['email']} for u in users]

# Include the router in the main app - MOVED TO END OF FILE

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    """Initialize database and seed default data"""
    # Initialize collections
    await db.service_types.create_index("id", unique=True)
    await db.add_ons.create_index("id", unique=True)
    await db.capacity_rules.create_index("id", unique=True)
    await db.pricing_rules.create_index("id", unique=True)
    await db.cancellation_policies.create_index("id", unique=True)
    await db.system_settings.create_index("key", unique=True)
    await db.payments.create_index("id", unique=True)
    await db.invoices.create_index("id", unique=True)
    
    # Seed default service types if none exist
    if await db.service_types.count_documents({}) == 0:
        default_services = [
            {
                "id": str(uuid.uuid4()),
                "name": "Standard Boarding",
                "description": "Overnight boarding in private rooms",
                "base_price": 50.0,
                "price_type": "per_dog_per_day",
                "is_overnight": True,
                "min_duration_days": 1,
                "requires_vaccination": True,
                "active": True,
                "sort_order": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Daycare",
                "description": "Full-day supervised play and socialization",
                "base_price": 35.0,
                "price_type": "per_dog",
                "is_overnight": False,
                "min_duration_days": 1,
                "max_duration_days": 1,
                "requires_vaccination": True,
                "active": True,
                "sort_order": 2,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        await db.service_types.insert_many(default_services)
        logger.info("Seeded default service types")
    
    # Seed default add-ons if none exist
    if await db.add_ons.count_documents({}) == 0:
        default_addons = [
            {
                "id": str(uuid.uuid4()),
                "name": "Extra Playtime",
                "description": "30 minutes of one-on-one play with staff",
                "price": 6.0,
                "price_type": "per_day",
                "category": "playtime",
                "max_quantity": 3,
                "active": True,
                "sort_order": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Bath & Grooming",
                "description": "Full bath and basic grooming before pickup",
                "price": 40.0,
                "price_type": "flat",
                "category": "grooming",
                "max_quantity": 1,
                "active": True,
                "sort_order": 2,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Transportation (Round Trip)",
                "description": "Pickup and drop-off service",
                "price": 25.0,
                "price_type": "flat",
                "category": "transport",
                "max_quantity": 1,
                "active": True,
                "sort_order": 3,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Feeding Assistance",
                "description": "Special feeding schedule and portion management",
                "price": 6.0,
                "price_type": "per_day",
                "category": "feeding",
                "max_quantity": 1,
                "active": True,
                "sort_order": 4,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        await db.add_ons.insert_many(default_addons)
        logger.info("Seeded default add-ons")
    
    # Seed default system settings if none exist
    if await db.system_settings.count_documents({}) == 0:
        default_settings = [
            {"key": "deposit_percentage", "value": "50", "value_type": "number", "category": "payments", "description": "Default deposit percentage required", "editable": True},
            {"key": "tax_rate", "value": "0", "value_type": "number", "category": "payments", "description": "Tax rate percentage", "editable": True},
            {"key": "rooms_capacity", "value": "7", "value_type": "number", "category": "capacity", "description": "Default room capacity", "editable": True},
            {"key": "crates_capacity", "value": "4", "value_type": "number", "category": "capacity", "description": "Default crate capacity", "editable": True},
            {"key": "booking_requires_approval", "value": "false", "value_type": "boolean", "category": "bookings", "description": "Require staff approval for all bookings", "editable": True},
            {"key": "base_room_rate", "value": "45", "value_type": "number", "category": "pricing", "description": "Base room rate per dog per night", "editable": True},
            {"key": "base_crate_rate", "value": "35", "value_type": "number", "category": "pricing", "description": "Base crate rate per dog per night", "editable": True},
            {"key": "base_daycare_rate", "value": "30", "value_type": "number", "category": "pricing", "description": "Base daycare rate per dog per day", "editable": True},
            {"key": "separate_playtime_rate", "value": "6", "value_type": "number", "category": "pricing", "description": "Separate playtime add-on rate", "editable": True},
            {"key": "multi_dog_discount", "value": "10", "value_type": "number", "category": "pricing", "description": "Multi-dog discount percentage", "editable": True},
            {"key": "meet_greet_settings", "value": '{"required_for_new_customers":true,"duration_minutes":30,"price":0,"available_days":["monday","tuesday","wednesday","thursday","friday"],"available_times":["10:00","14:00","16:00"]}', "value_type": "json", "category": "bookings", "description": "Meet & Greet settings", "editable": True},
        ]
        for setting in default_settings:
            setting["id"] = str(uuid.uuid4())
            setting["created_at"] = datetime.now(timezone.utc).isoformat()
            setting["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.system_settings.insert_many(default_settings)
        logger.info("Seeded default system settings")
    
    # Seed default cancellation policy if none exists
    if await db.cancellation_policies.count_documents({}) == 0:
        default_policies = [
            {
                "id": str(uuid.uuid4()),
                "name": "Standard - 7 Day",
                "days_before_checkin": 7,
                "refund_percentage": 100.0,
                "refund_deposit_only": False,
                "active": True,
                "is_default": True,
                "description": "Full refund if cancelled 7+ days before check-in",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Partial - 3 Day",
                "days_before_checkin": 3,
                "refund_percentage": 50.0,
                "refund_deposit_only": False,
                "active": True,
                "is_default": False,
                "description": "50% refund if cancelled 3-6 days before check-in",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Last Minute - Under 3 Days",
                "days_before_checkin": 0,
                "refund_percentage": 0.0,
                "refund_deposit_only": False,
                "active": True,
                "is_default": False,
                "description": "No refund if cancelled less than 3 days before check-in",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        await db.cancellation_policies.insert_many(default_policies)
        logger.info("Seeded default cancellation policies")
    
    # Seed default pricing rules (weekend surcharge)
    if await db.pricing_rules.count_documents({}) == 0:
        default_pricing_rules = [
            {
                "id": str(uuid.uuid4()),
                "name": "Weekend Surcharge",
                "rule_type": "weekend",
                "multiplier": 1.15,
                "flat_adjustment": 0.0,
                "days_of_week": [5, 6],  # Saturday, Sunday
                "priority": 1,
                "active": True,
                "description": "15% surcharge for weekend stays",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        await db.pricing_rules.insert_many(default_pricing_rules)
        logger.info("Seeded default pricing rules")


# ==================== PHASE 1: SERVICE TYPES ====================

@api_router.get("/service-types", response_model=List[ServiceTypeResponse])
async def get_service_types(database=Depends(get_db)):
    """Get all active service types"""
    services = await database.service_types.find({"active": True}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    return [ServiceTypeResponse(**s) for s in services]

@api_router.get("/service-types/{service_id}", response_model=ServiceTypeResponse)
async def get_service_type(service_id: str, database=Depends(get_db)):
    """Get a specific service type"""
    service = await database.service_types.find_one({"id": service_id}, {"_id": 0})
    if not service:
        raise HTTPException(status_code=404, detail="Service type not found")
    return ServiceTypeResponse(**service)

@api_router.post("/admin/service-types", response_model=ServiceTypeResponse)
async def create_service_type(
    service_data: ServiceTypeCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create a new service type (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = ServiceType(**service_data.model_dump())
    doc = service.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.service_types.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "service_type", service.id)
    
    return ServiceTypeResponse(**service.model_dump())

@api_router.patch("/admin/service-types/{service_id}", response_model=ServiceTypeResponse)
async def update_service_type(
    service_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update a service type (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    result = await database.service_types.update_one(
        {"id": service_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Service type not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "service_type", service_id, update_data)
    
    service = await database.service_types.find_one({"id": service_id}, {"_id": 0})
    return ServiceTypeResponse(**service)

@api_router.delete("/admin/service-types/{service_id}")
async def delete_service_type(
    service_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Soft delete a service type (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await database.service_types.update_one(
        {"id": service_id},
        {"$set": {"active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Service type not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "service_type", service_id)
    
    return {"message": "Service type deactivated"}


# ==================== PHASE 1: ADD-ONS ====================

@api_router.get("/add-ons", response_model=List[AddOnResponse])
async def get_add_ons(
    location_id: Optional[str] = None,
    service_type_id: Optional[str] = None,
    database=Depends(get_db)
):
    """Get all active add-ons, optionally filtered"""
    query = {"active": True}
    if location_id:
        query["$or"] = [{"location_id": None}, {"location_id": location_id}]
    
    add_ons = await database.add_ons.find(query, {"_id": 0}).sort("sort_order", 1).to_list(100)
    
    # Filter by service type if specified
    if service_type_id:
        add_ons = [
            a for a in add_ons 
            if not a.get('service_type_ids') or service_type_id in a.get('service_type_ids', [])
        ]
    
    return [AddOnResponse(**a) for a in add_ons]

@api_router.post("/admin/add-ons", response_model=AddOnResponse)
async def create_add_on(
    add_on_data: AddOnCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create a new add-on (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    add_on = AddOn(**add_on_data.model_dump())
    doc = add_on.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.add_ons.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "add_on", add_on.id)
    
    return AddOnResponse(**add_on.model_dump())

@api_router.patch("/admin/add-ons/{add_on_id}", response_model=AddOnResponse)
async def update_add_on(
    add_on_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update an add-on (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    result = await database.add_ons.update_one(
        {"id": add_on_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Add-on not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "add_on", add_on_id, update_data)
    
    add_on = await database.add_ons.find_one({"id": add_on_id}, {"_id": 0})
    return AddOnResponse(**add_on)

@api_router.delete("/admin/add-ons/{add_on_id}")
async def delete_add_on(
    add_on_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Soft delete an add-on (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await database.add_ons.update_one(
        {"id": add_on_id},
        {"$set": {"active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Add-on not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "add_on", add_on_id)
    
    return {"message": "Add-on deactivated"}


# ==================== PHASE 1: CAPACITY RULES ====================

@api_router.get("/admin/capacity-rules", response_model=List[CapacityRuleResponse])
async def get_capacity_rules(
    location_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get capacity rules (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {"active": True}
    if location_id:
        query["location_id"] = location_id
    
    rules = await database.capacity_rules.find(query, {"_id": 0}).to_list(100)
    return [CapacityRuleResponse(**r) for r in rules]

@api_router.post("/admin/capacity-rules", response_model=CapacityRuleResponse)
async def create_capacity_rule(
    rule_data: CapacityRuleCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create a capacity rule (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rule = CapacityRule(**rule_data.model_dump())
    doc = rule.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('effective_date'):
        doc['effective_date'] = doc['effective_date'].isoformat()
    if doc.get('expiry_date'):
        doc['expiry_date'] = doc['expiry_date'].isoformat()
    
    await database.capacity_rules.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "capacity_rule", rule.id)
    
    return CapacityRuleResponse(**rule.model_dump())

@api_router.patch("/admin/capacity-rules/{rule_id}", response_model=CapacityRuleResponse)
async def update_capacity_rule(
    rule_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update a capacity rule (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    result = await database.capacity_rules.update_one(
        {"id": rule_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Capacity rule not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "capacity_rule", rule_id, update_data)
    
    rule = await database.capacity_rules.find_one({"id": rule_id}, {"_id": 0})
    return CapacityRuleResponse(**rule)

@api_router.delete("/admin/capacity-rules/{rule_id}")
async def delete_capacity_rule(
    rule_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Delete a capacity rule (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await database.capacity_rules.delete_one({"id": rule_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Capacity rule not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "capacity_rule", rule_id)
    
    return {"message": "Capacity rule deleted"}


# ==================== PHASE 1: PRICING RULES ====================

@api_router.get("/admin/pricing-rules", response_model=List[PricingRuleResponse])
async def get_pricing_rules(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get all pricing rules (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rules = await database.pricing_rules.find({"active": True}, {"_id": 0}).sort("priority", 1).to_list(100)
    return [PricingRuleResponse(**r) for r in rules]

@api_router.post("/admin/pricing-rules", response_model=PricingRuleResponse)
async def create_pricing_rule(
    rule_data: PricingRuleCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create a pricing rule (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rule = PricingRule(**rule_data.model_dump())
    doc = rule.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('start_date'):
        doc['start_date'] = doc['start_date'].isoformat()
    if doc.get('end_date'):
        doc['end_date'] = doc['end_date'].isoformat()
    
    await database.pricing_rules.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "pricing_rule", rule.id)
    
    return PricingRuleResponse(**rule.model_dump())

@api_router.patch("/admin/pricing-rules/{rule_id}", response_model=PricingRuleResponse)
async def update_pricing_rule(
    rule_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update a pricing rule (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    result = await database.pricing_rules.update_one(
        {"id": rule_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "pricing_rule", rule_id, update_data)
    
    rule = await database.pricing_rules.find_one({"id": rule_id}, {"_id": 0})
    return PricingRuleResponse(**rule)

@api_router.delete("/admin/pricing-rules/{rule_id}")
async def delete_pricing_rule(
    rule_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Soft delete a pricing rule (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await database.pricing_rules.update_one(
        {"id": rule_id},
        {"$set": {"active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "pricing_rule", rule_id)
    
    return {"message": "Pricing rule deactivated"}


# ==================== PHASE 1: CANCELLATION POLICIES ====================

@api_router.get("/cancellation-policies", response_model=List[CancellationPolicyResponse])
async def get_cancellation_policies(database=Depends(get_db)):
    """Get all active cancellation policies (public)"""
    policies = await database.cancellation_policies.find({"active": True}, {"_id": 0}).sort("days_before_checkin", -1).to_list(100)
    return [CancellationPolicyResponse(**p) for p in policies]

@api_router.post("/admin/cancellation-policies", response_model=CancellationPolicyResponse)
async def create_cancellation_policy(
    policy_data: CancellationPolicyCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create a cancellation policy (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    policy = CancellationPolicy(**policy_data.model_dump())
    doc = policy.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.cancellation_policies.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "cancellation_policy", policy.id)
    
    return CancellationPolicyResponse(**policy.model_dump())

@api_router.patch("/admin/cancellation-policies/{policy_id}", response_model=CancellationPolicyResponse)
async def update_cancellation_policy(
    policy_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update a cancellation policy (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    result = await database.cancellation_policies.update_one(
        {"id": policy_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cancellation policy not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "cancellation_policy", policy_id, update_data)
    
    policy = await database.cancellation_policies.find_one({"id": policy_id}, {"_id": 0})
    return CancellationPolicyResponse(**policy)

@api_router.delete("/admin/cancellation-policies/{policy_id}")
async def delete_cancellation_policy(
    policy_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Soft delete a cancellation policy (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await database.cancellation_policies.update_one(
        {"id": policy_id},
        {"$set": {"active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cancellation policy not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "cancellation_policy", policy_id)
    
    return {"message": "Cancellation policy deactivated"}


# ==================== PHASE 1: SYSTEM SETTINGS ====================

@api_router.get("/admin/settings")
async def get_system_settings(
    category: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get system settings (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if category:
        query["category"] = category
    
    settings = await database.system_settings.find(query, {"_id": 0}).to_list(100)
    
    # Convert to dict for easier use
    return {s['key']: {
        "value": s['value'],
        "value_type": s.get('value_type', 'string'),
        "category": s.get('category', 'general'),
        "description": s.get('description', ''),
        "editable": s.get('editable', True)
    } for s in settings}

@api_router.patch("/admin/settings/{key}")
async def update_system_setting(
    key: str,
    value: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update a system setting (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    setting = await database.system_settings.find_one({"key": key}, {"_id": 0})
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    if not setting.get('editable', True):
        raise HTTPException(status_code=403, detail="This setting cannot be modified")
    
    result = await database.system_settings.update_one(
        {"key": key},
        {"$set": {"value": str(value), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    await create_audit_log(user.id, AuditAction.UPDATE, "system_setting", key, {"old_value": setting['value'], "new_value": value})
    
    return {"message": "Setting updated", "key": key, "value": value}


# ==================== SCHEDULING CONVENIENCE ENDPOINTS ====================

@api_router.get("/schedules")
async def list_schedules(
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get staff schedules (admin sees all, staff sees own)"""
    user = await get_current_user(credentials, database)
    
    query = {}
    if user.role == UserRole.STAFF:
        query["staff_id"] = user.id
    elif staff_id:
        query["staff_id"] = staff_id
    
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        if "date" not in query:
            query["date"] = {}
        query["date"]["$lte"] = end_date
    
    schedules = await database.staff_schedules.find(query, {"_id": 0}).sort("date", 1).to_list(500)
    return schedules

@api_router.get("/schedules/my-schedule")
async def get_my_schedule(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get current staff member's schedule"""
    user = await get_current_user(credentials, database)
    
    schedules = await database.staff_schedules.find(
        {"staff_id": user.id},
        {"_id": 0}
    ).sort("date", 1).to_list(100)
    return schedules

@api_router.get("/time-off/requests")
async def list_all_time_off_requests(
    status: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """List time off requests (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if status:
        query["status"] = status
    
    requests = await database.time_off_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return requests

@api_router.get("/time-off/my-requests")
async def get_my_time_off_requests(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get current user's time off requests"""
    user = await get_current_user(credentials, database)
    
    requests = await database.time_off_requests.find(
        {"staff_id": user.id},
        {"_id": 0}
    ).sort("start_date", -1).to_list(100)
    return requests

@api_router.post("/time-off/requests")
async def create_time_off_request(
    request_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Submit a new time off request"""
    user = await get_current_user(credentials, database)
    
    request_id = str(uuid.uuid4())
    doc = {
        "id": request_id,
        "staff_id": user.id,
        "leave_type": request_data.get("leave_type", "vacation"),
        "start_date": request_data.get("start_date"),
        "end_date": request_data.get("end_date"),
        "reason": request_data.get("reason", ""),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await database.time_off_requests.insert_one(doc)
    await create_audit_log(user.id, AuditAction.CREATE, "time_off_request", request_id)
    
    return {"message": "Time off request submitted", "id": request_id}

@api_router.post("/time-off/requests/{request_id}/approve")
async def approve_time_off_request(
    request_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Approve a time off request (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    request = await database.time_off_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    await database.time_off_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "approved_by": user.id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await create_audit_log(user.id, AuditAction.UPDATE, "time_off_request", request_id, {"action": "approve"})
    
    return {"message": "Time off request approved"}

@api_router.post("/time-off/requests/{request_id}/reject")
async def reject_time_off_request(
    request_id: str,
    data: Optional[dict] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Reject a time off request (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    request = await database.time_off_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    reason = data.get("reason", "") if data else ""
    
    await database.time_off_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": user.id,
            "rejection_reason": reason,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await create_audit_log(user.id, AuditAction.UPDATE, "time_off_request", request_id, {"action": "reject"})
    
    return {"message": "Time off request rejected"}

@api_router.get("/time-off/balances")
async def get_time_off_balances(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get current user's time off balances"""
    user = await get_current_user(credentials, database)
    
    balance = await database.time_off_balances.find_one({"staff_id": user.id}, {"_id": 0})
    if not balance:
        # Return default balances
        return {"vacation": 10, "sick": 5, "personal": 3}
    
    return balance

# ==================== PHASE 1: PRICE CALCULATION ====================

@api_router.post("/pricing/calculate", response_model=PriceBreakdown)
async def calculate_price(
    request: PriceCalculationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Calculate price breakdown for a booking (authenticated)"""
    user = await get_current_user(credentials, database)
    
    pricing_engine = PricingEngine(database)
    
    try:
        breakdown = await pricing_engine.calculate_price(
            service_type_id=request.service_type_id,
            location_id=request.location_id,
            dog_ids=request.dog_ids,
            check_in=request.check_in_date,
            check_out=request.check_out_date,
            accommodation_type=request.accommodation_type,
            add_on_ids=request.add_on_ids,
            add_on_quantities=request.add_on_quantities,
            promo_code=request.promo_code
        )
        return PriceBreakdown(**breakdown)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Price calculation error: {e}")
        raise HTTPException(status_code=500, detail="Error calculating price")


# ==================== PHASE 1: PAYMENT ENDPOINTS ====================

@api_router.get("/payments/providers")
async def get_payment_providers(database=Depends(get_db)):
    """Get available payment providers"""
    payment_service = PaymentService(database)
    providers = payment_service.get_available_providers()
    
    return {
        "providers": [
            {"name": "square", "available": providers.get("square", False), "display_name": "Card Payment (Square)"},
            {"name": "crypto", "available": providers.get("crypto", False), "display_name": "Crypto (USDC) - Coming Soon"},
        ],
        "default": "square"
    }

@api_router.post("/payments/deposit")
async def pay_deposit(
    booking_id: str,
    provider: str = "square",
    source_id: Optional[str] = None,  # Required for Square
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Pay deposit for a booking"""
    user = await get_current_user(credentials, database)
    
    # Get booking
    booking = await database.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Verify ownership
    if user.role == UserRole.CUSTOMER and booking.get('household_id') != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if deposit already paid
    if booking.get('deposit_paid'):
        raise HTTPException(status_code=400, detail="Deposit already paid")
    
    deposit_amount = booking.get('deposit_amount', 0)
    if deposit_amount <= 0:
        raise HTTPException(status_code=400, detail="No deposit required")
    
    # Process payment
    payment_service = PaymentService(database)
    result = await payment_service.process_payment(
        provider_name=provider,
        amount=deposit_amount,
        currency="USD",
        booking_id=booking_id,
        payment_type="deposit",
        source_id=source_id,
        metadata={"household_id": booking.get('household_id')}
    )
    
    if result.get('success'):
        # Update booking
        await database.bookings.update_one(
            {"id": booking_id},
            {"$set": {
                "deposit_paid": True,
                "deposit_paid_at": datetime.now(timezone.utc).isoformat(),
                "payment_status": "deposit_paid",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        await create_audit_log(user.id, AuditAction.PAYMENT, "booking", booking_id, {
            "payment_type": "deposit",
            "amount": deposit_amount,
            "provider": provider
        })
        
        return {
            "success": True,
            "message": "Deposit paid successfully",
            "amount": deposit_amount,
            "payment_id": result.get('payment_id'),
            "receipt_url": result.get('receipt_url')
        }
    else:
        raise HTTPException(status_code=400, detail=result.get('error', 'Payment failed'))

@api_router.post("/payments/balance")
async def pay_balance(
    booking_id: str,
    provider: str = "square",
    source_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Pay remaining balance for a booking"""
    user = await get_current_user(credentials, database)
    
    # Get booking
    booking = await database.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Verify ownership
    if user.role == UserRole.CUSTOMER and booking.get('household_id') != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if balance already paid
    if booking.get('balance_paid'):
        raise HTTPException(status_code=400, detail="Balance already paid")
    
    balance_due = booking.get('balance_due', 0)
    if balance_due <= 0:
        raise HTTPException(status_code=400, detail="No balance due")
    
    # Process payment
    payment_service = PaymentService(database)
    result = await payment_service.process_payment(
        provider_name=provider,
        amount=balance_due,
        currency="USD",
        booking_id=booking_id,
        payment_type="balance",
        source_id=source_id,
        metadata={"household_id": booking.get('household_id')}
    )
    
    if result.get('success'):
        # Update booking
        await database.bookings.update_one(
            {"id": booking_id},
            {"$set": {
                "balance_paid": True,
                "balance_paid_at": datetime.now(timezone.utc).isoformat(),
                "payment_status": "paid",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        await create_audit_log(user.id, AuditAction.PAYMENT, "booking", booking_id, {
            "payment_type": "balance",
            "amount": balance_due,
            "provider": provider
        })
        
        return {
            "success": True,
            "message": "Balance paid successfully",
            "amount": balance_due,
            "payment_id": result.get('payment_id'),
            "receipt_url": result.get('receipt_url')
        }
    else:
        raise HTTPException(status_code=400, detail=result.get('error', 'Payment failed'))

@api_router.get("/payments/history", response_model=List[PaymentResponse])
async def get_payment_history(
    booking_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get payment history for customer or all (admin)"""
    user = await get_current_user(credentials, database)
    
    query = {}
    if user.role == UserRole.CUSTOMER:
        query["household_id"] = user.household_id
    
    if booking_id:
        query["booking_id"] = booking_id
    
    payments = await database.payments.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [PaymentResponse(**p) for p in payments]


# ==================== PHASE 1: BOOKING CANCELLATION ====================

@api_router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: str,
    reason: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Cancel a booking with policy-aware refund calculation"""
    user = await get_current_user(credentials, database)
    
    # Get booking
    booking = await database.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Verify ownership (customers can only cancel their own)
    if user.role == UserRole.CUSTOMER and booking.get('household_id') != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if already cancelled
    if booking.get('status') == 'cancelled':
        raise HTTPException(status_code=400, detail="Booking already cancelled")
    
    # Calculate refund
    pricing_engine = PricingEngine(database)
    refund_info = await pricing_engine.calculate_refund(booking)
    
    # Update booking status
    await database.bookings.update_one(
        {"id": booking_id},
        {"$set": {
            "status": "cancelled",
            "modification_reason": reason or "Customer requested cancellation",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Process refund if applicable
    refund_result = None
    if refund_info['refund_amount'] > 0 and refund_info['total_paid'] > 0:
        # TODO: Process actual refund through payment provider
        # For now, just record it
        refund_record = {
            "id": str(uuid.uuid4()),
            "booking_id": booking_id,
            "household_id": booking.get('household_id'),
            "amount": refund_info['refund_amount'],
            "currency": "USD",
            "payment_type": "refund",
            "provider": "pending",  # Will be updated when processed
            "status": "pending",
            "metadata": {
                "policy_applied": refund_info['policy_applied'],
                "refund_percentage": refund_info['refund_percentage'],
                "reason": reason
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await database.payments.insert_one(refund_record)
        refund_result = refund_record
    
    await create_audit_log(user.id, AuditAction.UPDATE, "booking", booking_id, {
        "action": "cancelled",
        "reason": reason,
        "refund_amount": refund_info['refund_amount'],
        "policy_applied": refund_info['policy_applied']
    })
    
    return {
        "success": True,
        "message": "Booking cancelled",
        "refund_info": refund_info,
        "refund_status": "pending" if refund_result else "none"
    }


# ==================== PHASE 1: INVOICES ====================

@api_router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    booking_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get invoices for customer or all (admin)"""
    user = await get_current_user(credentials, database)
    
    query = {}
    if user.role == UserRole.CUSTOMER:
        query["household_id"] = user.household_id
    
    if booking_id:
        query["booking_id"] = booking_id
    
    invoices = await database.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [InvoiceResponse(**inv) for inv in invoices]

@api_router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get a specific invoice"""
    user = await get_current_user(credentials, database)
    
    invoice = await database.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Verify access
    if user.role == UserRole.CUSTOMER and invoice.get('household_id') != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return InvoiceResponse(**invoice)


# ==================== PHASE 2: STAFF OPERATIONS DASHBOARD ====================

@api_router.get("/ops/dashboard")
async def get_ops_dashboard(
    date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get staff operations dashboard data"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    # Parse date or use today
    if date:
        target_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
    else:
        target_date = datetime.now(timezone.utc)
    
    target_date_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    target_date_end = target_date_start + timedelta(days=1)
    
    # Get dogs currently on site
    dogs_on_site_bookings = await database.bookings.find({
        "status": {"$in": ["confirmed", "checked_in"]},
        "check_in_date": {"$lte": target_date_end.isoformat()},
        "check_out_date": {"$gt": target_date_start.isoformat()}
    }, {"_id": 0}).to_list(500)
    
    dogs_on_site = []
    for booking in dogs_on_site_bookings:
        # Get dog details
        for dog_id in booking.get('dog_ids', []):
            dog = await database.dogs.find_one({"id": dog_id}, {"_id": 0})
            if dog:
                # Get owner info
                owner = await database.users.find_one({"household_id": booking.get('household_id')}, {"_id": 0})
                
                check_out = datetime.fromisoformat(booking['check_out_date'].replace('Z', '+00:00')) if isinstance(booking['check_out_date'], str) else booking['check_out_date']
                days_remaining = (check_out - target_date).days
                
                dogs_on_site.append({
                    "dog_id": dog['id'],
                    "dog_name": dog.get('name', 'Unknown'),
                    "breed": dog.get('breed', 'Unknown'),
                    "photo_url": dog.get('photo_url'),
                    "household_id": booking.get('household_id'),
                    "owner_name": owner.get('full_name', 'Unknown') if owner else 'Unknown',
                    "booking_id": booking['id'],
                    "check_in_date": booking['check_in_date'],
                    "check_out_date": booking['check_out_date'],
                    "accommodation_type": booking.get('accommodation_type', 'room'),
                    "special_needs": dog.get('medical_flags', []),
                    "days_remaining": max(0, days_remaining),
                    "notes": dog.get('behavioral_notes')
                })
    
    # Get today's arrivals
    arrivals = await database.bookings.find({
        "status": {"$in": ["confirmed", "pending"]},
        "check_in_date": {"$gte": target_date_start.isoformat(), "$lt": target_date_end.isoformat()}
    }, {"_id": 0}).to_list(100)
    
    arrivals_list = []
    for booking in arrivals:
        dog_names = []
        for dog_id in booking.get('dog_ids', []):
            dog = await database.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
            if dog:
                dog_names.append(dog.get('name', 'Unknown'))
        
        owner = await database.users.find_one({"household_id": booking.get('household_id')}, {"_id": 0})
        
        arrivals_list.append({
            "booking_id": booking['id'],
            "dog_ids": booking.get('dog_ids', []),
            "dog_names": dog_names,
            "owner_name": owner.get('full_name', 'Unknown') if owner else 'Unknown',
            "owner_phone": owner.get('phone') if owner else None,
            "scheduled_time": booking['check_in_date'],
            "accommodation_type": booking.get('accommodation_type', 'room'),
            "type": "arrival",
            "status": "pending" if booking['status'] != 'checked_in' else "completed",
            "special_instructions": booking.get('special_request')
        })
    
    # Get today's departures
    departures = await database.bookings.find({
        "status": {"$in": ["checked_in", "confirmed"]},
        "check_out_date": {"$gte": target_date_start.isoformat(), "$lt": target_date_end.isoformat()}
    }, {"_id": 0}).to_list(100)
    
    departures_list = []
    for booking in departures:
        dog_names = []
        for dog_id in booking.get('dog_ids', []):
            dog = await database.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
            if dog:
                dog_names.append(dog.get('name', 'Unknown'))
        
        owner = await database.users.find_one({"household_id": booking.get('household_id')}, {"_id": 0})
        
        departures_list.append({
            "booking_id": booking['id'],
            "dog_ids": booking.get('dog_ids', []),
            "dog_names": dog_names,
            "owner_name": owner.get('full_name', 'Unknown') if owner else 'Unknown',
            "owner_phone": owner.get('phone') if owner else None,
            "scheduled_time": booking['check_out_date'],
            "accommodation_type": booking.get('accommodation_type', 'room'),
            "type": "departure",
            "status": "pending" if booking['status'] != 'checked_out' else "completed",
            "items_checklist": booking.get('items_checklist')
        })
    
    # Capacity snapshot
    rooms_capacity = 7
    crates_capacity = 4
    
    # Get capacity from settings
    rooms_setting = await database.system_settings.find_one({"key": "rooms_capacity"}, {"_id": 0})
    crates_setting = await database.system_settings.find_one({"key": "crates_capacity"}, {"_id": 0})
    if rooms_setting:
        rooms_capacity = int(rooms_setting.get('value', 7))
    if crates_setting:
        crates_capacity = int(crates_setting.get('value', 4))
    
    rooms_occupied = len([d for d in dogs_on_site if d.get('accommodation_type') == 'room'])
    crates_occupied = len([d for d in dogs_on_site if d.get('accommodation_type') == 'crate'])
    
    # Approval queue count
    approval_count = await database.bookings.count_documents({
        "status": "pending",
        "requires_approval": True
    })
    
    capacity_snapshot = {
        "date": target_date_start.strftime('%Y-%m-%d'),
        "total_capacity": rooms_capacity + crates_capacity,
        "rooms_capacity": rooms_capacity,
        "crates_capacity": crates_capacity,
        "total_occupied": len(dogs_on_site),
        "rooms_occupied": rooms_occupied,
        "crates_occupied": crates_occupied,
        "total_available": (rooms_capacity + crates_capacity) - len(dogs_on_site),
        "rooms_available": rooms_capacity - rooms_occupied,
        "crates_available": crates_capacity - crates_occupied,
        "arrivals_today": len(arrivals_list),
        "departures_today": len(departures_list),
        "requires_approval_count": approval_count
    }
    
    return {
        "date": target_date_start.strftime('%Y-%m-%d'),
        "dogs_on_site": dogs_on_site,
        "arrivals": arrivals_list,
        "departures": departures_list,
        "capacity": capacity_snapshot
    }


@api_router.get("/ops/approval-queue", response_model=List[ApprovalQueueItem])
async def get_approval_queue(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get bookings requiring approval"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    bookings = await database.bookings.find({
        "status": "pending",
        "requires_approval": True
    }, {"_id": 0}).sort("created_at", 1).to_list(100)
    
    queue = []
    for booking in bookings:
        # Get customer info
        customer = await database.users.find_one({"household_id": booking.get('household_id')}, {"_id": 0})
        
        # Get dog names
        dog_names = []
        for dog_id in booking.get('dog_ids', []):
            dog = await database.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
            if dog:
                dog_names.append(dog.get('name', 'Unknown'))
        
        queue.append(ApprovalQueueItem(
            booking_id=booking['id'],
            household_id=booking.get('household_id', ''),
            customer_name=customer.get('full_name', 'Unknown') if customer else 'Unknown',
            customer_email=customer.get('email', '') if customer else '',
            dog_names=dog_names,
            check_in_date=booking['check_in_date'],
            check_out_date=booking['check_out_date'],
            accommodation_type=booking.get('accommodation_type', 'room'),
            total_price=booking.get('total_price', 0),
            reason="over_capacity",  # TODO: Store actual reason
            submitted_at=booking.get('created_at', datetime.now(timezone.utc).isoformat()),
            notes=booking.get('notes')
        ))
    
    return queue


@api_router.post("/ops/bookings/{booking_id}/approve")
async def approve_booking(
    booking_id: str,
    notes: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Approve a pending booking"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    booking = await database.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get('status') != 'pending':
        raise HTTPException(status_code=400, detail="Booking is not pending approval")
    
    await database.bookings.update_one(
        {"id": booking_id},
        {"$set": {
            "status": "confirmed",
            "requires_approval": False,
            "approved_by": user.id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "modification_reason": notes,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await create_audit_log(user.id, AuditAction.UPDATE, "booking", booking_id, {
        "action": "approved",
        "notes": notes
    })
    
    # Trigger automation
    automation = AutomationService(database)
    await automation.log_event(
        "booking.confirmed",
        "booking",
        booking_id,
        booking.get('customer_id'),
        {
            "booking_id": booking_id,
            "household_id": booking.get('household_id'),
            "dog_names": ", ".join(booking.get('dog_ids', [])),
            "check_in_date": booking.get('check_in_date'),
            "check_out_date": booking.get('check_out_date')
        }
    )
    
    return {"message": "Booking approved", "status": "confirmed"}


@api_router.post("/ops/bookings/{booking_id}/reject")
async def reject_booking(
    booking_id: str,
    reason: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Reject a pending booking"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    booking = await database.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    await database.bookings.update_one(
        {"id": booking_id},
        {"$set": {
            "status": "cancelled",
            "requires_approval": False,
            "modification_reason": f"Rejected: {reason}",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await create_audit_log(user.id, AuditAction.UPDATE, "booking", booking_id, {
        "action": "rejected",
        "reason": reason
    })
    
    return {"message": "Booking rejected", "status": "cancelled"}


# ==================== PHASE 2: STAFF ASSIGNMENTS ====================

@api_router.get("/ops/staff-assignments", response_model=List[StaffAssignmentResponse])
async def get_staff_assignments(
    date: Optional[str] = None,
    staff_id: Optional[str] = None,
    dog_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get staff assignments"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    query = {"active": True}
    
    if date:
        target_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        date_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        query["assignment_date"] = {"$gte": date_start.isoformat(), "$lt": date_end.isoformat()}
    
    if staff_id:
        query["staff_id"] = staff_id
    
    if dog_id:
        query["dog_id"] = dog_id
    
    assignments = await database.staff_assignments.find(query, {"_id": 0}).to_list(500)
    return [StaffAssignmentResponse(**a) for a in assignments]


@api_router.post("/ops/staff-assignments", response_model=StaffAssignmentResponse)
async def create_staff_assignment(
    assignment_data: StaffAssignmentCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create a staff assignment"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    # Get staff and dog names
    staff = await database.users.find_one({"id": assignment_data.staff_id}, {"_id": 0})
    dog = await database.dogs.find_one({"id": assignment_data.dog_id}, {"_id": 0})
    
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    assignment = StaffAssignment(
        **assignment_data.model_dump(),
        staff_name=staff.get('full_name', 'Unknown'),
        dog_name=dog.get('name', 'Unknown')
    )
    
    doc = assignment.model_dump()
    doc['assignment_date'] = doc['assignment_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.staff_assignments.insert_one(doc)
    
    await create_audit_log(user.id, AuditAction.CREATE, "staff_assignment", assignment.id)
    
    return StaffAssignmentResponse(**assignment.model_dump())


@api_router.delete("/ops/staff-assignments/{assignment_id}")
async def delete_staff_assignment(
    assignment_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Remove a staff assignment"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    result = await database.staff_assignments.update_one(
        {"id": assignment_id},
        {"$set": {"active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return {"message": "Assignment removed"}


# ==================== PHASE 2: PLAY GROUPS ====================

@api_router.get("/ops/play-groups", response_model=List[PlayGroupResponse])
async def get_play_groups(
    date: Optional[str] = None,
    status: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get play groups"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    query = {}
    
    if date:
        target_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        date_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        query["scheduled_date"] = {"$gte": date_start.isoformat(), "$lt": date_end.isoformat()}
    
    if status:
        query["status"] = status
    
    groups = await database.play_groups.find(query, {"_id": 0}).sort("scheduled_time", 1).to_list(100)
    return [PlayGroupResponse(**g) for g in groups]


@api_router.post("/ops/play-groups", response_model=PlayGroupResponse)
async def create_play_group(
    group_data: PlayGroupCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create a play group"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    # Get dog names
    dog_names = []
    for dog_id in group_data.dog_ids:
        dog = await database.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
        if dog:
            dog_names.append(dog.get('name', 'Unknown'))
    
    # Get supervisor name
    supervisor_name = None
    if group_data.supervisor_id:
        supervisor = await database.users.find_one({"id": group_data.supervisor_id}, {"_id": 0})
        if supervisor:
            supervisor_name = supervisor.get('full_name')
    
    group = PlayGroup(
        **group_data.model_dump(),
        dog_names=dog_names,
        supervisor_name=supervisor_name
    )
    
    doc = group.model_dump()
    doc['scheduled_date'] = doc['scheduled_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.play_groups.insert_one(doc)
    
    await create_audit_log(user.id, AuditAction.CREATE, "play_group", group.id)
    
    return PlayGroupResponse(**group.model_dump())


@api_router.patch("/ops/play-groups/{group_id}")
async def update_play_group(
    group_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update a play group"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # If status is being set to completed
    if update_data.get('status') == 'completed':
        update_data['completed_at'] = datetime.now(timezone.utc).isoformat()
    
    # Update dog_names if dog_ids changed
    if 'dog_ids' in update_data:
        dog_names = []
        for dog_id in update_data['dog_ids']:
            dog = await database.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
            if dog:
                dog_names.append(dog.get('name', 'Unknown'))
        update_data['dog_names'] = dog_names
    
    result = await database.play_groups.update_one(
        {"id": group_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Play group not found")
    
    return {"message": "Play group updated"}


@api_router.post("/ops/play-groups/{group_id}/add-dog")
async def add_dog_to_play_group(
    group_id: str,
    dog_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Add a dog to a play group"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    group = await database.play_groups.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Play group not found")
    
    if len(group.get('dog_ids', [])) >= group.get('max_dogs', 6):
        raise HTTPException(status_code=400, detail="Play group is full")
    
    if dog_id in group.get('dog_ids', []):
        raise HTTPException(status_code=400, detail="Dog already in group")
    
    # Get dog name
    dog = await database.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    await database.play_groups.update_one(
        {"id": group_id},
        {
            "$push": {"dog_ids": dog_id, "dog_names": dog.get('name', 'Unknown')},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Dog added to play group"}


# ==================== PHASE 2: FEEDING SCHEDULES ====================

@api_router.get("/ops/feeding-schedules", response_model=List[FeedingScheduleResponse])
async def get_feeding_schedules(
    booking_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get feeding schedules for current bookings"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    query = {}
    if booking_id:
        query["booking_id"] = booking_id
    
    schedules = await database.feeding_schedules.find(query, {"_id": 0}).to_list(500)
    return [FeedingScheduleResponse(**s) for s in schedules]


@api_router.post("/ops/feeding-schedules", response_model=FeedingScheduleResponse)
async def create_feeding_schedule(
    schedule_data: FeedingScheduleCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create a feeding schedule for a dog"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    # Get dog name
    dog = await database.dogs.find_one({"id": schedule_data.dog_id}, {"_id": 0})
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    schedule = FeedingSchedule(
        **schedule_data.model_dump(),
        dog_name=dog.get('name', 'Unknown')
    )
    
    doc = schedule.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.feeding_schedules.insert_one(doc)
    
    return FeedingScheduleResponse(**schedule.model_dump())


@api_router.patch("/ops/feeding-schedules/{schedule_id}")
async def update_feeding_schedule(
    schedule_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update a feeding schedule"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await database.feeding_schedules.update_one(
        {"id": schedule_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Feeding schedule not found")
    
    return {"message": "Feeding schedule updated"}


@api_router.post("/ops/feeding-schedules/{schedule_id}/log-feeding")
async def log_feeding(
    schedule_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Log that a dog has been fed"""
    user = await get_current_user(credentials, database)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    result = await database.feeding_schedules.update_one(
        {"id": schedule_id},
        {"$set": {
            "last_fed_at": datetime.now(timezone.utc).isoformat(),
            "last_fed_by": user.id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Feeding schedule not found")
    
    return {"message": "Feeding logged", "fed_at": datetime.now(timezone.utc).isoformat()}


# ==================== PHASE 3: ENHANCED BOOKING ====================

@api_router.post("/bookings/v2", response_model=BookingResponse)
async def create_booking_v2(
    booking_data: BookingCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """
    Enhanced booking creation with full pricing engine support.
    Phase 3 implementation with add-ons and policy awareness.
    """
    user = await get_current_user(credentials, database)
    
    # Determine service type
    service_type_id = booking_data.service_type_id
    if not service_type_id:
        # Get default service type
        default_service = await database.service_types.find_one({"active": True}, {"_id": 0})
        service_type_id = default_service['id'] if default_service else None
    
    # Calculate price using pricing engine
    pricing_engine = PricingEngine(database)
    
    try:
        price_breakdown = await pricing_engine.calculate_price(
            service_type_id=service_type_id,
            location_id=booking_data.location_id,
            dog_ids=booking_data.dog_ids,
            check_in=booking_data.check_in_date,
            check_out=booking_data.check_out_date,
            accommodation_type=booking_data.accommodation_type,
            add_on_ids=booking_data.add_on_ids,
            add_on_quantities=booking_data.add_on_quantities
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Determine if approval is required
    requires_approval = price_breakdown.get('requires_approval', False)
    status = BookingStatus.PENDING if requires_approval else BookingStatus.PENDING
    
    # Get default cancellation policy
    default_policy = await database.cancellation_policies.find_one(
        {"active": True, "is_default": True}, {"_id": 0}
    )
    
    # Create booking with full details
    booking = Booking(
        dog_ids=booking_data.dog_ids,
        location_id=booking_data.location_id,
        accommodation_type=booking_data.accommodation_type,
        check_in_date=booking_data.check_in_date,
        check_out_date=booking_data.check_out_date,
        notes=booking_data.notes,
        special_request=booking_data.special_request,
        needs_separate_playtime=booking_data.needs_separate_playtime,
        household_id=user.household_id if user.role == UserRole.CUSTOMER else None,
        customer_id=user.id if user.role == UserRole.CUSTOMER else None,
        status=status,
        # Pricing details
        service_type_id=service_type_id,
        add_ons=price_breakdown.get('add_ons_detail', []),
        subtotal=price_breakdown.get('subtotal', 0),
        tax_amount=price_breakdown.get('tax_amount', 0),
        total_price=price_breakdown.get('total', 0),
        deposit_percentage=price_breakdown.get('deposit_percentage', 50),
        deposit_amount=price_breakdown.get('deposit_amount', 0),
        balance_due=price_breakdown.get('balance_due', 0),
        is_holiday_pricing=any(adj.get('rule_type') == 'holiday' for adj in price_breakdown.get('pricing_adjustments', [])),
        pricing_rules_applied=[adj.get('rule_id') for adj in price_breakdown.get('pricing_adjustments', [])],
        requires_approval=requires_approval,
        cancellation_policy_id=default_policy['id'] if default_policy else None
    )
    
    doc = booking.model_dump()
    doc['check_in_date'] = doc['check_in_date'].isoformat()
    doc['check_out_date'] = doc['check_out_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.bookings.insert_one(doc)
    
    await create_audit_log(user.id, AuditAction.CREATE, "booking", booking.id, {
        "total_price": booking.total_price,
        "requires_approval": requires_approval
    })
    
    # Create invoice
    invoice = {
        "id": str(uuid.uuid4()),
        "booking_id": booking.id,
        "household_id": booking.household_id,
        "invoice_number": f"INV-{booking.id[:8].upper()}",
        "subtotal": price_breakdown.get('subtotal', 0),
        "tax_amount": price_breakdown.get('tax_amount', 0),
        "discount_amount": price_breakdown.get('discount_amount', 0),
        "total_amount": price_breakdown.get('total', 0),
        "deposit_required": price_breakdown.get('deposit_amount', 0),
        "deposit_paid": 0,
        "balance_due": price_breakdown.get('balance_due', 0),
        "balance_paid": 0,
        "currency": "USD",
        "status": "draft",
        "line_items": [
            {
                "description": f"Boarding - {(booking_data.check_out_date - booking_data.check_in_date).days} night(s) x {len(booking_data.dog_ids)} dog(s)",
                "amount": price_breakdown.get('service_subtotal', 0)
            }
        ] + [
            {"description": addon['name'], "amount": addon['total']}
            for addon in price_breakdown.get('add_ons_detail', [])
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await database.invoices.insert_one(invoice)
    
    # Update booking with invoice ID
    await database.bookings.update_one(
        {"id": booking.id},
        {"$set": {"invoice_id": invoice["id"]}}
    )
    
    # Trigger automation
    automation = AutomationService(database)
    if requires_approval:
        await automation.log_event(
            "booking.requires_approval",
            "booking",
            booking.id,
            user.id,
            {
                "booking_id": booking.id,
                "customer_name": user.full_name,
                "approval_reason": "Over capacity" if price_breakdown.get('is_over_capacity') else "Manual review required",
                "check_in_date": booking_data.check_in_date.strftime('%Y-%m-%d')
            }
        )
    else:
        await automation.log_event(
            "booking.created",
            "booking",
            booking.id,
            user.id,
            {
                "booking_id": booking.id,
                "household_id": booking.household_id,
                "total_price": booking.total_price
            }
        )
    
    return BookingResponse(**booking.model_dump())


@api_router.patch("/bookings/{booking_id}/modify")
async def modify_booking(
    booking_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """
    Modify a booking with policy awareness.
    Customers can only modify their own bookings within policy limits.
    """
    user = await get_current_user(credentials, database)
    
    booking = await database.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check ownership for customers
    if user.role == UserRole.CUSTOMER:
        if booking.get('household_id') != user.household_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if modification is allowed (not checked in, not in the past)
        if booking.get('status') == 'checked_in':
            raise HTTPException(status_code=400, detail="Cannot modify a booking after check-in")
    
    # Recalculate price if dates or add-ons changed
    needs_recalc = any(k in update_data for k in ['check_in_date', 'check_out_date', 'dog_ids', 'add_on_ids'])
    
    if needs_recalc:
        check_in = update_data.get('check_in_date', booking.get('check_in_date'))
        check_out = update_data.get('check_out_date', booking.get('check_out_date'))
        dog_ids = update_data.get('dog_ids', booking.get('dog_ids', []))
        add_on_ids = update_data.get('add_on_ids', [])
        
        if isinstance(check_in, str):
            check_in = datetime.fromisoformat(check_in.replace('Z', '+00:00'))
        if isinstance(check_out, str):
            check_out = datetime.fromisoformat(check_out.replace('Z', '+00:00'))
        
        pricing_engine = PricingEngine(database)
        price_breakdown = await pricing_engine.calculate_price(
            service_type_id=booking.get('service_type_id'),
            location_id=booking.get('location_id'),
            dog_ids=dog_ids,
            check_in=check_in,
            check_out=check_out,
            accommodation_type=booking.get('accommodation_type', 'room'),
            add_on_ids=add_on_ids,
            exclude_booking_id=booking_id
        )
        
        update_data.update({
            'subtotal': price_breakdown.get('subtotal', 0),
            'tax_amount': price_breakdown.get('tax_amount', 0),
            'total_price': price_breakdown.get('total', 0),
            'deposit_amount': price_breakdown.get('deposit_amount', 0),
            'balance_due': price_breakdown.get('balance_due', 0) - (booking.get('deposit_amount', 0) if booking.get('deposit_paid') else 0),
            'add_ons': price_breakdown.get('add_ons_detail', []),
            'pricing_rules_applied': [adj.get('rule_id') for adj in price_breakdown.get('pricing_adjustments', [])]
        })
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    update_data['modification_reason'] = update_data.get('modification_reason', 'Customer modification')
    
    # Handle date conversions
    for date_field in ['check_in_date', 'check_out_date']:
        if date_field in update_data and isinstance(update_data[date_field], datetime):
            update_data[date_field] = update_data[date_field].isoformat()
    
    result = await database.bookings.update_one(
        {"id": booking_id},
        {"$set": update_data}
    )
    
    await create_audit_log(user.id, AuditAction.UPDATE, "booking", booking_id, {
        "modifications": list(update_data.keys()),
        "by_role": user.role.value
    })
    
    return {"message": "Booking modified successfully", "price_recalculated": needs_recalc}


# ==================== PHASE 4: NOTIFICATIONS ====================

@api_router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get notifications for current user"""
    user = await get_current_user(credentials, database)
    
    automation = AutomationService(database)
    notifications = await automation.get_user_notifications(user.id, unread_only, limit)
    
    return [NotificationResponse(**n) for n in notifications]


@api_router.get("/notifications/unread-count")
async def get_unread_notification_count(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get count of unread notifications"""
    user = await get_current_user(credentials, database)
    
    automation = AutomationService(database)
    count = await automation.get_unread_count(user.id)
    
    return {"unread_count": count}


@api_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Mark a notification as read"""
    user = await get_current_user(credentials, database)
    
    automation = AutomationService(database)
    success = await automation.mark_notification_read(notification_id, user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification marked as read"}


@api_router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Mark all notifications as read"""
    user = await get_current_user(credentials, database)
    
    result = await database.notifications.update_many(
        {"user_id": user.id, "read_at": None},
        {"$set": {
            "status": "read",
            "read_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": f"Marked {result.modified_count} notifications as read"}


# ==================== PHASE 4: NOTIFICATION TEMPLATES (Admin) ====================

@api_router.get("/admin/notification-templates", response_model=List[NotificationTemplateResponse])
async def get_notification_templates(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get all notification templates (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    templates = await database.notification_templates.find({}, {"_id": 0}).to_list(100)
    return [NotificationTemplateResponse(**t) for t in templates]


@api_router.post("/admin/notification-templates", response_model=NotificationTemplateResponse)
async def create_notification_template(
    template_data: NotificationTemplateCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create a notification template (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    template = NotificationTemplate(**template_data.model_dump())
    doc = template.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.notification_templates.insert_one(doc)
    
    return NotificationTemplateResponse(**template.model_dump())


@api_router.patch("/admin/notification-templates/{template_id}")
async def update_notification_template(
    template_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update a notification template (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await database.notification_templates.update_one(
        {"id": template_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template updated"}


# ==================== PHASE 4: AUTOMATION RULES (Admin) ====================

@api_router.get("/admin/automation-rules", response_model=List[AutomationRuleResponse])
async def get_automation_rules(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get all automation rules (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rules = await database.automation_rules.find({}, {"_id": 0}).sort("priority", 1).to_list(100)
    return [AutomationRuleResponse(**r) for r in rules]


@api_router.post("/admin/automation-rules", response_model=AutomationRuleResponse)
async def create_automation_rule(
    rule_data: AutomationRuleCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Create an automation rule (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rule = AutomationRule(**rule_data.model_dump())
    doc = rule.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await database.automation_rules.insert_one(doc)
    
    await create_audit_log(user.id, AuditAction.CREATE, "automation_rule", rule.id)
    
    return AutomationRuleResponse(**rule.model_dump())


@api_router.patch("/admin/automation-rules/{rule_id}")
async def update_automation_rule(
    rule_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Update an automation rule (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await database.automation_rules.update_one(
        {"id": rule_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "automation_rule", rule_id, update_data)
    
    return {"message": "Automation rule updated"}


@api_router.delete("/admin/automation-rules/{rule_id}")
async def delete_automation_rule(
    rule_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Delete an automation rule (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await database.automation_rules.delete_one({"id": rule_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    
    await create_audit_log(user.id, AuditAction.DELETE, "automation_rule", rule_id)
    
    return {"message": "Automation rule deleted"}


# ==================== PHASE 4: EVENT LOGS (Admin) ====================

@api_router.get("/admin/event-logs", response_model=List[EventLogResponse])
async def get_event_logs(
    event_type: Optional[str] = None,
    limit: int = 100,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Get system event logs (admin only)"""
    user = await get_current_user(credentials, database)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if event_type:
        query["event_type"] = event_type
    
    logs = await database.event_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return [EventLogResponse(**log) for log in logs]


# ==================== PHASE 4: MANUAL NOTIFICATION SEND ====================

class SendNotificationRequest(BaseModel):
    user_id: str
    subject: str
    body: str
    channel: str = "in_app"

@api_router.post("/admin/send-notification")
async def send_manual_notification(
    request: SendNotificationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Send a manual notification to a user (admin only)"""
    admin = await get_current_user(credentials, database)
    if admin.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Verify user exists
    target_user = await database.users.find_one({"id": request.user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    automation = AutomationService(database)
    notification_id = await automation.send_notification(
        user_id=request.user_id,
        notification_type="custom",
        channel=request.channel,
        subject=request.subject,
        body=request.body,
        metadata={"sent_by": admin.id}
    )
    
    await create_audit_log(admin.id, AuditAction.CREATE, "notification", notification_id, {
        "recipient": request.user_id,
        "subject": request.subject
    })
    
    return {"message": "Notification sent", "notification_id": notification_id}


# ==================== INCLUDE ROUTER (MUST BE AFTER ALL ROUTES) ====================
app.include_router(api_router)

# Include HR/Staff management routers
from routers.timeclock import router as timeclock_router
from routers.forms import router as forms_router
from routers.hr import router as hr_router
from routers.communications import router as comms_router
from routers.scheduling import router as scheduling_router
from routers.exports import router as exports_router

app.include_router(timeclock_router)
app.include_router(forms_router)
app.include_router(hr_router)
app.include_router(comms_router)
app.include_router(scheduling_router)
app.include_router(exports_router)

# Include K9Command core routers (refactored from moego.py)
from routers.kennels import router as kennels_router
from routers.bookings import router as bookings_router
from routers.operations import router as operations_router
from routers.notifications import router as notifications_router
from routers.payments import router as payments_router
from routers.portal import router as portal_router
from routers.inventory import router as inventory_router
from routers.crm import router as crm_router
from routers.reminders import router as reminders_router
from routers.admin import router as admin_router

app.include_router(kennels_router)
app.include_router(bookings_router)
app.include_router(operations_router)
app.include_router(notifications_router)
app.include_router(payments_router)
app.include_router(portal_router)
app.include_router(inventory_router)
app.include_router(crm_router)
app.include_router(reminders_router)
app.include_router(admin_router)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
