from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import EmailStr
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import base64

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
    UserRole
)
from auth import hash_password, verify_password, create_access_token, get_current_user, require_role, security
from ai_service import generate_daily_summary

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
        raise HTTPException(status_code=403, detail="Only customers can create bookings")
    
    # Calculate nights
    nights = (booking_data.check_out_date - booking_data.check_in_date).days
    if nights <= 0:
        raise HTTPException(status_code=400, detail="Invalid date range")
    
    # Check if dates include holidays (basic check - can be enhanced)
    is_holiday = False
    for holiday_date in ["2025-12-25", "2025-12-31", "2025-07-04", "2025-11-28"]:
        holiday = datetime.fromisoformat(holiday_date)
        if booking_data.check_in_date <= holiday < booking_data.check_out_date:
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

@api_router.post("/bookings/{booking_id}/confirm-payment")
async def confirm_payment(
    booking_id: str,
    payment_method: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database=Depends(get_db)
):
    """Mock payment confirmation (Square integration mocked)"""
    user = await get_current_user(credentials, database)
    
    # Simulate payment processing
    import uuid
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
        "method": payment_method
    })
    
    return {
        "message": "Payment processed successfully",
        "payment_id": mock_payment_id,
        "status": "completed"
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
        {"$set": {"status": TaskStatus.COMPLETED, "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "task", task_id, {"status": "completed"})
    
    return {"message": "Task completed"}

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
    
    entry = TimeEntry(**entry_data.model_dump(), clock_in=datetime.now(timezone.utc))
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
    
    incidents = await database.incidents.find({}, {"_id": 0}).to_list(1000)
    return [IncidentResponse(**inc) for inc in incidents]

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
        except:
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
        except:
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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
