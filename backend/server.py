"""
FastAPI Server with PostgreSQL + Redis
Kennel Operations Platform
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func as sql_func
from sqlalchemy.orm import selectinload
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import base64
import uuid

# Database and models
from database import get_db, init_db, close_db, get_redis
from db_models import (
    User, Location, Dog, Booking, DailyUpdate, Task, TimeEntry,
    TimeModificationRequest, Shift, AuditLog, Incident, Review, Chat, ChatMessage,
    UserRole, BookingStatus, TaskStatus, UpdateStatus, AuditAction,
    TimeModificationStatus, AccommodationType, ChatType
)
from schemas import (
    UserCreate, UserResponse, LoginRequest, LoginResponse,
    LocationCreate, LocationResponse,
    DogCreate, DogResponse,
    BookingCreate, BookingResponse,
    DailyUpdateCreate, DailyUpdateResponse, MediaItem,
    TaskCreate, TaskResponse,
    TimeEntryCreate, TimeEntryResponse,
    TimeModificationRequestCreate, TimeModificationRequestResponse,
    ShiftCreate, ShiftResponse,
    AuditLogResponse,
    IncidentCreate, IncidentResponse,
    ReviewCreate, ReviewResponse,
    ChatCreate, ChatResponse, ChatMessageCreate, ChatMessageResponse
)
from auth import hash_password, verify_password, create_access_token, get_current_user, security
from cache_service import CacheService
from ai_service import generate_daily_summary

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global cache service
cache_service: Optional[CacheService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global cache_service
    # Startup
    logger.info("Starting up application...")
    await init_db()
    
    # Initialize Redis cache
    try:
        redis = await get_redis()
        cache_service = CacheService(redis)
        logger.info("Redis cache initialized")
    except Exception as e:
        logger.warning(f"Redis not available, running without cache: {e}")
        cache_service = None
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_db()


# Create the main app
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Dependency to get cache
async def get_cache():
    return cache_service


# Helper function to log audit
async def create_audit_log(
    db: AsyncSession,
    user_id: str,
    action: AuditAction,
    resource_type: str,
    resource_id: str = None,
    details: dict = None
):
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {}
    )
    db.add(audit)
    await db.commit()


# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=LoginResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create household for customers
    household_id = None
    if user_data.role == UserRole.CUSTOMER:
        household_id = str(uuid.uuid4())
    
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
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Create token
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    
    # Audit log
    await create_audit_log(db, user.id, AuditAction.CREATE, "user", user.id)
    
    user_response = UserResponse.model_validate(user)
    return LoginResponse(token=token, user=user_response)


@api_router.post("/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")
    
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    
    # Audit log
    await create_audit_log(db, user.id, AuditAction.LOGIN, "user", user.id)
    
    user_response = UserResponse.model_validate(user)
    return LoginResponse(token=token, user=user_response)


@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    return UserResponse.model_validate(user)


@api_router.post("/auth/forgot-password")
async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):
    """Generate password reset token"""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Return success even if user doesn't exist (security best practice)
        return {"message": "If this email exists, a reset link has been sent"}
    
    # Generate reset token
    import secrets
    reset_token = secrets.token_urlsafe(32)
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    
    user.reset_token = reset_token
    user.reset_token_expiry = expiry
    await db.commit()
    
    return {
        "message": "Password reset token generated",
        "reset_token": reset_token,
        "note": "In production, this would be sent via email"
    }


@api_router.post("/auth/reset-password")
async def reset_password(request_data: dict, db: AsyncSession = Depends(get_db)):
    """Reset password using token"""
    reset_token = request_data.get('reset_token')
    new_password = request_data.get('new_password')
    
    if not reset_token or not new_password:
        raise HTTPException(status_code=400, detail="reset_token and new_password are required")
    
    result = await db.execute(select(User).where(User.reset_token == reset_token))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Check if token is expired
    if user.reset_token_expiry and datetime.now(timezone.utc) > user.reset_token_expiry:
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    # Update password
    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    await db.commit()
    
    return {"message": "Password reset successful"}


# ==================== LOCATION ROUTES ====================

@api_router.post("/locations", response_model=LocationResponse)
async def create_location(
    location_data: LocationCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    location = Location(**location_data.model_dump())
    db.add(location)
    await db.commit()
    await db.refresh(location)
    
    await create_audit_log(db, user.id, AuditAction.CREATE, "location", location.id)
    
    # Invalidate cache
    if cache:
        await cache.invalidate_locations()
    
    return LocationResponse.model_validate(location)


@api_router.get("/locations", response_model=List[LocationResponse])
async def get_locations(
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    # Try cache first
    if cache:
        cached = await cache.get_locations()
        if cached:
            return [LocationResponse(**loc) for loc in cached]
    
    result = await db.execute(select(Location))
    locations = result.scalars().all()
    
    # Cache results
    if cache and locations:
        await cache.set_locations([{
            "id": loc.id, "name": loc.name, "address": loc.address,
            "capacity": loc.capacity, "contact_email": loc.contact_email,
            "contact_phone": loc.contact_phone,
            "created_at": loc.created_at.isoformat() if loc.created_at else None,
            "updated_at": loc.updated_at.isoformat() if loc.updated_at else None
        } for loc in locations])
    
    return [LocationResponse.model_validate(loc) for loc in locations]


@api_router.get("/locations/{location_id}/availability")
async def check_availability(
    location_id: str,
    check_in: str,
    check_out: str,
    db: AsyncSession = Depends(get_db)
):
    """Check real-time availability for rooms and crates"""
    check_in_date = datetime.fromisoformat(check_in.replace('Z', '+00:00'))
    check_out_date = datetime.fromisoformat(check_out.replace('Z', '+00:00'))
    
    # Get all bookings that overlap with requested dates
    result = await db.execute(
        select(Booking).where(
            and_(
                Booking.location_id == location_id,
                Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]),
                Booking.check_in_date < check_out_date,
                Booking.check_out_date > check_in_date
            )
        )
    )
    overlapping_bookings = result.scalars().all()
    
    # Count occupied rooms and crates
    rooms_occupied = sum(1 for b in overlapping_bookings if b.accommodation_type == AccommodationType.ROOM)
    crates_occupied = sum(1 for b in overlapping_bookings if b.accommodation_type == AccommodationType.CRATE)
    
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
async def create_dog(
    dog_data: DogCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Only customers can add dogs")
    
    dog = Dog(**dog_data.model_dump(), household_id=user.household_id)
    db.add(dog)
    await db.commit()
    await db.refresh(dog)
    
    await create_audit_log(db, user.id, AuditAction.CREATE, "dog", dog.id)
    
    return DogResponse.model_validate(dog)


@api_router.get("/dogs", response_model=List[DogResponse])
async def get_dogs(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    if user.role == UserRole.CUSTOMER:
        result = await db.execute(select(Dog).where(Dog.household_id == user.household_id))
    else:
        result = await db.execute(select(Dog))
    
    dogs = result.scalars().all()
    return [DogResponse.model_validate(dog) for dog in dogs]


@api_router.get("/dogs/{dog_id}", response_model=DogResponse)
async def get_dog(
    dog_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    result = await db.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalar_one_or_none()
    
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    if user.role == UserRole.CUSTOMER and dog.household_id != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return DogResponse.model_validate(dog)


@api_router.post("/dogs/{dog_id}/upload-photo")
async def upload_dog_photo(
    dog_id: str,
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Upload dog profile photo"""
    user = await get_current_user(credentials, db, cache)
    
    result = await db.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalar_one_or_none()
    
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    if user.role == UserRole.CUSTOMER and dog.household_id != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Read file
    content = await file.read()
    file_data = base64.b64encode(content).decode('utf-8')
    photo_url = f"data:{file.content_type};base64,{file_data}"
    
    dog.photo_url = photo_url
    await db.commit()
    
    return {"message": "Photo uploaded successfully", "photo_url": photo_url[:100] + "..."}


@api_router.post("/dogs/{dog_id}/upload-vaccination")
async def upload_vaccination_file(
    dog_id: str,
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Upload vaccination documents"""
    user = await get_current_user(credentials, db, cache)
    
    result = await db.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalar_one_or_none()
    
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    if user.role == UserRole.CUSTOMER and dog.household_id != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    content = await file.read()
    file_data = base64.b64encode(content).decode('utf-8')
    file_url = f"data:{file.content_type};base64,{file_data}"
    
    dog.vaccination_file_url = file_url
    await db.commit()
    
    return {"message": "Vaccination file uploaded successfully"}


# ==================== BOOKING ROUTES ====================

@api_router.post("/bookings", response_model=BookingResponse)
async def create_booking(
    booking_data: BookingCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
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
    base_price = 50.0
    total_price = base_price * nights * len(booking_data.dog_ids)
    
    if is_holiday:
        total_price *= 1.20
    
    separate_playtime_fee = 0.0
    if booking_data.needs_separate_playtime:
        separate_playtime_fee = 6.0 * nights
        total_price += separate_playtime_fee
    
    booking = Booking(
        dog_ids=booking_data.dog_ids,
        location_id=booking_data.location_id,
        accommodation_type=AccommodationType(booking_data.accommodation_type),
        check_in_date=booking_data.check_in_date,
        check_out_date=booking_data.check_out_date,
        notes=booking_data.notes,
        special_request=booking_data.special_request,
        needs_separate_playtime=booking_data.needs_separate_playtime,
        household_id=user.household_id,
        status=BookingStatus.PENDING,
        total_price=round(total_price, 2),
        is_holiday_pricing=is_holiday,
        separate_playtime_fee=separate_playtime_fee
    )
    
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    
    await create_audit_log(db, user.id, AuditAction.CREATE, "booking", booking.id)
    
    # Invalidate stats cache
    if cache:
        await cache.invalidate_stats()
    
    return BookingResponse.model_validate(booking)


@api_router.post("/bookings/admin", response_model=BookingResponse)
async def create_booking_admin(
    booking_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Create booking on behalf of customer (staff/admin only)"""
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff or Admin access required")
    
    customer_id = booking_data.get('customer_id')
    if not customer_id:
        raise HTTPException(status_code=400, detail="Customer ID is required")
    
    result = await db.execute(select(User).where(User.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Parse dates
    check_in_date = datetime.fromisoformat(booking_data['check_in_date'].replace('Z', '+00:00')) if isinstance(booking_data['check_in_date'], str) else booking_data['check_in_date']
    check_out_date = datetime.fromisoformat(booking_data['check_out_date'].replace('Z', '+00:00')) if isinstance(booking_data['check_out_date'], str) else booking_data['check_out_date']
    
    nights = (check_out_date - check_in_date).days
    if nights <= 0:
        raise HTTPException(status_code=400, detail="Invalid date range")
    
    dog_ids = booking_data.get('dog_ids', [])
    if not dog_ids:
        raise HTTPException(status_code=400, detail="At least one dog is required")
    
    # Holiday check
    is_holiday = False
    holidays = ["2025-12-25", "2025-12-31", "2025-07-04", "2025-11-28", "2026-12-25", "2026-12-31", "2026-07-04", "2026-11-28"]
    for holiday_date in holidays:
        holiday = datetime.fromisoformat(holiday_date)
        if check_in_date.date() <= holiday.date() < check_out_date.date():
            is_holiday = True
            break
    
    # Pricing
    base_price = 50.0
    total_price = base_price * nights * len(dog_ids)
    
    if is_holiday:
        total_price *= 1.20
    
    separate_playtime_fee = 0.0
    needs_separate_playtime = booking_data.get('needs_separate_playtime', False)
    if needs_separate_playtime:
        separate_playtime_fee = 6.0 * nights
        total_price += separate_playtime_fee
    
    payment_type = booking_data.get('payment_type', 'invoice')
    
    # Get location
    location_id = booking_data.get('location_id')
    if not location_id:
        result = await db.execute(select(Location).limit(1))
        location = result.scalar_one_or_none()
        location_id = location.id if location else 'main-kennel'
    
    booking = Booking(
        dog_ids=dog_ids,
        location_id=location_id,
        accommodation_type=AccommodationType(booking_data.get('accommodation_type', 'room')),
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        notes=booking_data.get('notes', ''),
        special_request=booking_data.get('special_request', ''),
        needs_separate_playtime=needs_separate_playtime,
        household_id=customer.household_id,
        customer_id=customer_id,
        status=BookingStatus.PENDING,
        payment_status="pending",
        payment_type=payment_type,
        total_price=round(total_price, 2),
        is_holiday_pricing=is_holiday,
        separate_playtime_fee=separate_playtime_fee,
        created_by=user.id
    )
    
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    
    await create_audit_log(db, user.id, AuditAction.CREATE, "booking", booking.id, {
        "customer_id": customer_id,
        "payment_type": payment_type,
        "created_by_staff": True
    })
    
    if cache:
        await cache.invalidate_stats()
    
    return BookingResponse.model_validate(booking)


@api_router.get("/bookings", response_model=List[BookingResponse])
async def get_bookings(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    if user.role == UserRole.CUSTOMER:
        result = await db.execute(select(Booking).where(Booking.household_id == user.household_id))
    elif user.role == UserRole.STAFF:
        result = await db.execute(select(Booking).where(Booking.location_id == user.location_id))
    else:
        result = await db.execute(select(Booking))
    
    bookings = result.scalars().all()
    return [BookingResponse.model_validate(b) for b in bookings]


@api_router.patch("/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    status: BookingStatus,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff or Admin access required")
    
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.status = status
    
    if status == BookingStatus.CHECKED_IN:
        booking.checked_in_at = datetime.now(timezone.utc)
        await create_audit_log(db, user.id, AuditAction.CHECK_IN, "booking", booking_id)
    elif status == BookingStatus.CHECKED_OUT:
        booking.checked_out_at = datetime.now(timezone.utc)
        await create_audit_log(db, user.id, AuditAction.CHECK_OUT, "booking", booking_id)
    
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "booking", booking_id, {"status": status.value})
    
    if cache:
        await cache.invalidate_stats()
    
    return {"message": "Status updated", "status": status.value}


@api_router.patch("/bookings/{booking_id}")
async def update_booking(
    booking_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Update booking details (staff/admin only)"""
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff or Admin access required")
    
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Update allowed fields
    allowed_fields = ['dog_ids', 'location_id', 'accommodation_type', 'check_in_date',
                      'check_out_date', 'notes', 'special_request', 'needs_separate_playtime',
                      'status', 'modification_reason']
    
    for field in allowed_fields:
        if field in update_data:
            if field == 'status':
                setattr(booking, field, BookingStatus(update_data[field]))
            elif field == 'accommodation_type':
                setattr(booking, field, AccommodationType(update_data[field]))
            elif field in ['check_in_date', 'check_out_date'] and isinstance(update_data[field], str):
                setattr(booking, field, datetime.fromisoformat(update_data[field].replace('Z', '+00:00')))
            else:
                setattr(booking, field, update_data[field])
    
    # Recalculate price if dates changed
    if 'check_in_date' in update_data or 'check_out_date' in update_data:
        nights = (booking.check_out_date - booking.check_in_date).days
        dog_count = len(booking.dog_ids or [])
        base_price = 50.0
        total = base_price * nights * dog_count
        
        holidays = ['2025-12-25', '2025-12-31', '2025-07-04', '2025-11-28', '2026-12-25', '2026-12-31']
        is_holiday = any(booking.check_in_date.date() <= datetime.strptime(h, '%Y-%m-%d').date() < booking.check_out_date.date() for h in holidays)
        if is_holiday:
            total *= 1.20
            booking.is_holiday_pricing = True
        
        if booking.needs_separate_playtime:
            booking.separate_playtime_fee = 6.0 * nights
            total += booking.separate_playtime_fee
        
        booking.total_price = round(total, 2)
    
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "booking", booking_id, {
        "fields_updated": list(update_data.keys()),
        "reason": update_data.get('modification_reason', '')
    })
    
    if cache:
        await cache.invalidate_stats()
    
    return {"message": "Booking updated successfully"}


@api_router.delete("/bookings/{booking_id}")
async def delete_booking(
    booking_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Delete/Cancel a booking (staff/admin only)"""
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff or Admin access required")
    
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.status = BookingStatus.CANCELLED
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.DELETE, "booking", booking_id)
    
    if cache:
        await cache.invalidate_stats()
    
    return {"message": "Booking cancelled"}


@api_router.patch("/bookings/{booking_id}/items")
async def update_items_checklist(
    booking_id: str,
    items: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff or Admin access required")
    
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.items_checklist = items
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "booking", booking_id, {"items_updated": True})
    
    return {"message": "Items checklist updated", "items": items}


@api_router.post("/bookings/{booking_id}/confirm-payment")
async def confirm_payment(
    booking_id: str,
    payment_method: str,
    source_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Process payment - uses Square if configured, otherwise mock mode"""
    user = await get_current_user(credentials, db, cache)
    
    result = await db.execute(
        select(Booking).where(
            and_(Booking.id == booking_id, Booking.household_id == user.household_id)
        )
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    square_token = os.environ.get('SQUARE_ACCESS_TOKEN', '')
    
    if square_token and source_id:
        try:
            from square import Square
            
            square_client = Square(
                access_token=square_token,
                environment=os.environ.get('SQUARE_ENVIRONMENT', 'sandbox')
            )
            
            idempotency_key = f"{booking_id}:{str(uuid.uuid4())}"
            payment_result = square_client.payments.create_payment({
                "source_id": source_id,
                "amount_money": {
                    "amount": int(booking.total_price * 100),
                    "currency": "USD"
                },
                "idempotency_key": idempotency_key,
                "reference_id": booking_id,
            })
            
            if payment_result.is_success:
                payment = payment_result.body.get('payment', {})
                payment_id = payment.get('id', '')
                payment_status = payment.get('status', 'COMPLETED')
                
                booking.payment_status = "completed" if payment_status == "COMPLETED" else "pending"
                booking.payment_intent_id = payment_id
                booking.status = BookingStatus.CONFIRMED if payment_status == "COMPLETED" else BookingStatus.PENDING
                await db.commit()
                
                await create_audit_log(db, user.id, AuditAction.PAYMENT, "booking", booking_id, {
                    "payment_id": payment_id,
                    "method": "square",
                    "amount": booking.total_price
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
    
    booking.payment_status = "completed"
    booking.payment_intent_id = mock_payment_id
    booking.status = BookingStatus.CONFIRMED
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.PAYMENT, "booking", booking_id, {
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
async def create_daily_update(
    update_data: DailyUpdateCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    daily_update = DailyUpdate(
        household_id=update_data.household_id,
        booking_id=update_data.booking_id,
        date=datetime.now(timezone.utc),
        status=UpdateStatus.DRAFT
    )
    
    db.add(daily_update)
    await db.commit()
    await db.refresh(daily_update)
    
    await create_audit_log(db, user.id, AuditAction.CREATE, "daily_update", daily_update.id)
    
    return DailyUpdateResponse.model_validate(daily_update)


@api_router.post("/daily-updates/{update_id}/snippets")
async def add_staff_snippet(
    update_id: str,
    snippet_text: str = Form(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    result = await db.execute(select(DailyUpdate).where(DailyUpdate.id == update_id))
    daily_update = result.scalar_one_or_none()
    
    if not daily_update:
        raise HTTPException(status_code=404, detail="Update not found")
    
    snippet = {
        "staff_id": user.id,
        "staff_name": user.full_name,
        "text": snippet_text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    snippets = daily_update.staff_snippets or []
    snippets.append(snippet)
    daily_update.staff_snippets = snippets
    await db.commit()
    
    return {"message": "Snippet added", "snippet": snippet}


@api_router.post("/daily-updates/{update_id}/media")
async def add_media_to_update(
    update_id: str,
    dog_ids: str = Form(...),
    caption: Optional[str] = Form(None),
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    result = await db.execute(select(DailyUpdate).where(DailyUpdate.id == update_id))
    daily_update = result.scalar_one_or_none()
    
    if not daily_update:
        raise HTTPException(status_code=404, detail="Update not found")
    
    content = await file.read()
    file_data = base64.b64encode(content).decode('utf-8')
    file_url = f"data:{file.content_type};base64,{file_data[:100]}..."
    
    tagged_dogs = dog_ids.split(',') if dog_ids else []
    
    media_item = {
        "url": file_url,
        "type": "photo" if file.content_type.startswith("image") else "video",
        "caption": caption,
        "uploaded_by": user.id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "dog_ids": tagged_dogs,
        "watermarked": True,
        "purchased": False
    }
    
    media_items = daily_update.media_items or []
    media_items.append(media_item)
    daily_update.media_items = media_items
    await db.commit()
    
    return {"message": "Media added successfully", "media": media_item}


@api_router.post("/daily-updates/{update_id}/reactions")
async def add_reaction(
    update_id: str,
    reaction: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    result = await db.execute(select(DailyUpdate).where(DailyUpdate.id == update_id))
    daily_update = result.scalar_one_or_none()
    
    if not daily_update:
        raise HTTPException(status_code=404, detail="Update not found")
    
    reaction_doc = {
        "user_id": user.id,
        "reaction": reaction,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    reactions = daily_update.reactions or []
    reactions.append(reaction_doc)
    daily_update.reactions = reactions
    await db.commit()
    
    return {"message": "Reaction added", "reaction": reaction_doc}


@api_router.post("/daily-updates/{update_id}/comments")
async def add_comment(
    update_id: str,
    text: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    result = await db.execute(select(DailyUpdate).where(DailyUpdate.id == update_id))
    daily_update = result.scalar_one_or_none()
    
    if not daily_update:
        raise HTTPException(status_code=404, detail="Update not found")
    
    comment_doc = {
        "user_id": user.id,
        "user_name": user.full_name,
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    comments = daily_update.comments or []
    comments.append(comment_doc)
    daily_update.comments = comments
    await db.commit()
    
    return {"message": "Comment added", "comment": comment_doc}


@api_router.post("/daily-updates/{update_id}/purchase-photos")
async def purchase_photos(
    update_id: str,
    payment_method: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Purchase photos to remove watermark (mock payment)"""
    user = await get_current_user(credentials, db, cache)
    
    result = await db.execute(select(DailyUpdate).where(DailyUpdate.id == update_id))
    daily_update = result.scalar_one_or_none()
    
    if not daily_update:
        raise HTTPException(status_code=404, detail="Update not found")
    
    if user.role == UserRole.CUSTOMER and daily_update.household_id != user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Mock payment
    payment_id = f"photo_purchase_{str(uuid.uuid4())[:8]}"
    
    # Mark all media as purchased
    media_items = daily_update.media_items or []
    for item in media_items:
        item['purchased'] = True
        item['watermarked'] = False
    daily_update.media_items = media_items
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.PAYMENT, "photo_purchase", update_id, {
        "payment_id": payment_id,
        "amount": 9.99
    })
    
    return {
        "message": "Photos purchased successfully! Watermarks removed.",
        "payment_id": payment_id,
        "amount": 9.99
    }


@api_router.post("/daily-updates/{update_id}/generate-summary")
async def generate_summary(
    update_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    result = await db.execute(select(DailyUpdate).where(DailyUpdate.id == update_id))
    daily_update = result.scalar_one_or_none()
    
    if not daily_update:
        raise HTTPException(status_code=404, detail="Update not found")
    
    # Get booking
    booking_result = await db.execute(select(Booking).where(Booking.id == daily_update.booking_id))
    booking = booking_result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Get dog names
    dog_names = []
    for dog_id in booking.dog_ids or []:
        dog_result = await db.execute(select(Dog).where(Dog.id == dog_id))
        dog = dog_result.scalar_one_or_none()
        if dog:
            dog_names.append(dog.name)
    
    staff_snippets = daily_update.staff_snippets or []
    if not staff_snippets:
        raise HTTPException(status_code=400, detail="No staff snippets to summarize")
    
    summary = await generate_daily_summary(
        dog_names=dog_names,
        staff_snippets=staff_snippets,
        media_count=len(daily_update.media_items or [])
    )
    
    daily_update.ai_summary = summary
    daily_update.status = UpdateStatus.PENDING_APPROVAL
    await db.commit()
    
    return {"message": "Summary generated", "summary": summary}


@api_router.post("/daily-updates/{update_id}/approve")
async def approve_and_send_update(
    update_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    result = await db.execute(select(DailyUpdate).where(DailyUpdate.id == update_id))
    daily_update = result.scalar_one_or_none()
    
    if not daily_update:
        raise HTTPException(status_code=404, detail="Update not found")
    
    daily_update.status = UpdateStatus.SENT
    daily_update.approved_by = user.id
    daily_update.sent_at = datetime.now(timezone.utc)
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "daily_update", update_id, {"action": "approved_and_sent"})
    
    return {"message": "Update approved and sent to customer"}


@api_router.get("/daily-updates", response_model=List[DailyUpdateResponse])
async def get_daily_updates(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    if user.role == UserRole.CUSTOMER:
        result = await db.execute(select(DailyUpdate).where(DailyUpdate.household_id == user.household_id))
    else:
        result = await db.execute(select(DailyUpdate))
    
    updates = result.scalars().all()
    return [DailyUpdateResponse.model_validate(u) for u in updates]


# ==================== TASK ROUTES ====================

@api_router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    task = Task(**task_data.model_dump(), status=TaskStatus.PENDING)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    await create_audit_log(db, user.id, AuditAction.CREATE, "task", task.id)
    
    return TaskResponse.model_validate(task)


@api_router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    if user.role == UserRole.STAFF:
        result = await db.execute(
            select(Task).where(
                or_(Task.assigned_to == user.id, Task.location_id == user.location_id)
            )
        )
    else:
        result = await db.execute(select(Task))
    
    tasks = result.scalars().all()
    return [TaskResponse.model_validate(t) for t in tasks]


@api_router.patch("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(timezone.utc)
    task.completed_by = user.id
    task.completed_by_name = user.full_name
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "task", task_id, {"status": "completed"})
    
    return {"message": "Task completed"}


@api_router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(delete(Task).where(Task.id == task_id))
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.commit()
    await create_audit_log(db, user.id, AuditAction.DELETE, "task", task_id)
    
    return {"message": "Task deleted"}


# ==================== TIME TRACKING ROUTES ====================

@api_router.get("/time-entries", response_model=List[TimeEntryResponse])
async def get_time_entries(
    staff_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    if user.role == UserRole.STAFF:
        result = await db.execute(
            select(TimeEntry).where(TimeEntry.staff_id == user.id).order_by(TimeEntry.clock_in.desc())
        )
    elif user.role == UserRole.ADMIN:
        if staff_id:
            result = await db.execute(
                select(TimeEntry).where(TimeEntry.staff_id == staff_id).order_by(TimeEntry.clock_in.desc())
            )
        else:
            result = await db.execute(select(TimeEntry).order_by(TimeEntry.clock_in.desc()))
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    entries = result.scalars().all()
    return [TimeEntryResponse.model_validate(e) for e in entries]


@api_router.get("/time-entries/current")
async def get_current_time_entry(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff access only")
    
    result = await db.execute(
        select(TimeEntry).where(
            and_(TimeEntry.staff_id == user.id, TimeEntry.clock_out.is_(None))
        )
    )
    active_entry = result.scalar_one_or_none()
    
    if active_entry:
        return {"clocked_in": True, "entry": TimeEntryResponse.model_validate(active_entry)}
    
    return {"clocked_in": False, "entry": None}


@api_router.post("/time-entries/clock-in", response_model=TimeEntryResponse)
async def clock_in(
    entry_data: TimeEntryCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff access only")
    
    # Check if already clocked in
    result = await db.execute(
        select(TimeEntry).where(
            and_(TimeEntry.staff_id == user.id, TimeEntry.clock_out.is_(None))
        )
    )
    active_entry = result.scalar_one_or_none()
    
    if active_entry:
        raise HTTPException(status_code=400, detail="Already clocked in")
    
    entry = TimeEntry(
        staff_id=user.id,
        location_id=entry_data.location_id,
        clock_in=datetime.now(timezone.utc)
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    await create_audit_log(db, user.id, AuditAction.CREATE, "time_entry", entry.id, {"action": "clock_in"})
    
    return TimeEntryResponse.model_validate(entry)


@api_router.post("/time-entries/clock-out")
async def clock_out(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff access only")
    
    result = await db.execute(
        select(TimeEntry).where(
            and_(TimeEntry.staff_id == user.id, TimeEntry.clock_out.is_(None))
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=400, detail="Not clocked in")
    
    entry.clock_out = datetime.now(timezone.utc)
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "time_entry", entry.id, {"action": "clock_out"})
    
    return {"message": "Clocked out successfully"}


@api_router.post("/time-entries/modification-request")
async def create_modification_request(
    request_data: TimeModificationRequestCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Staff access only")
    
    result = await db.execute(
        select(TimeEntry).where(
            and_(TimeEntry.id == request_data.time_entry_id, TimeEntry.staff_id == user.id)
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    mod_request = TimeModificationRequest(
        time_entry_id=request_data.time_entry_id,
        staff_id=user.id,
        staff_name=user.full_name,
        original_clock_in=entry.clock_in,
        original_clock_out=entry.clock_out,
        requested_clock_in=request_data.requested_clock_in,
        requested_clock_out=request_data.requested_clock_out,
        reason=request_data.reason
    )
    
    db.add(mod_request)
    await db.commit()
    await db.refresh(mod_request)
    
    return {"message": "Modification request submitted", "request_id": mod_request.id}


@api_router.get("/time-entries/modification-requests")
async def get_modification_requests(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    if user.role == UserRole.STAFF:
        result = await db.execute(
            select(TimeModificationRequest)
            .where(TimeModificationRequest.staff_id == user.id)
            .order_by(TimeModificationRequest.created_at.desc())
        )
    elif user.role == UserRole.ADMIN:
        result = await db.execute(
            select(TimeModificationRequest).order_by(TimeModificationRequest.created_at.desc())
        )
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    requests = result.scalars().all()
    return [TimeModificationRequestResponse.model_validate(r) for r in requests]


@api_router.patch("/time-entries/modification-requests/{request_id}")
async def review_modification_request(
    request_id: str,
    action: str,
    review_notes: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(
        select(TimeModificationRequest).where(TimeModificationRequest.id == request_id)
    )
    mod_request = result.scalar_one_or_none()
    
    if not mod_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    new_status = TimeModificationStatus.APPROVED if action == "approve" else TimeModificationStatus.REJECTED
    
    mod_request.status = new_status
    mod_request.reviewed_by = user.id
    mod_request.reviewed_at = datetime.now(timezone.utc)
    mod_request.review_notes = review_notes
    
    # If approved, update the original time entry
    if action == "approve":
        entry_result = await db.execute(
            select(TimeEntry).where(TimeEntry.id == mod_request.time_entry_id)
        )
        entry = entry_result.scalar_one_or_none()
        if entry:
            entry.clock_in = mod_request.requested_clock_in
            if mod_request.requested_clock_out:
                entry.clock_out = mod_request.requested_clock_out
    
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "time_modification_request", request_id, {"action": action})
    
    return {"message": f"Request {action}d", "status": new_status.value}


@api_router.post("/time-entries", response_model=TimeEntryResponse)
async def create_time_entry(
    entry_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Admin create time entry"""
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    entry = TimeEntry(
        staff_id=entry_data['staff_id'],
        location_id=entry_data.get('location_id', 'main-kennel'),
        clock_in=datetime.fromisoformat(entry_data['clock_in'].replace('Z', '+00:00')),
        clock_out=datetime.fromisoformat(entry_data['clock_out'].replace('Z', '+00:00')) if entry_data.get('clock_out') else None,
        notes=entry_data.get('notes')
    )
    
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    await create_audit_log(db, user.id, AuditAction.CREATE, "time_entry", entry.id)
    
    return TimeEntryResponse.model_validate(entry)


@api_router.patch("/time-entries/{entry_id}")
async def update_time_entry(
    entry_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Admin update time entry"""
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(TimeEntry).where(TimeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    if 'clock_in' in update_data:
        entry.clock_in = datetime.fromisoformat(update_data['clock_in'].replace('Z', '+00:00')) if isinstance(update_data['clock_in'], str) else update_data['clock_in']
    if 'clock_out' in update_data:
        entry.clock_out = datetime.fromisoformat(update_data['clock_out'].replace('Z', '+00:00')) if isinstance(update_data['clock_out'], str) else update_data['clock_out']
    if 'notes' in update_data:
        entry.notes = update_data['notes']
    
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "time_entry", entry_id)
    
    return {"message": "Time entry updated"}


@api_router.delete("/time-entries/{entry_id}")
async def delete_time_entry(
    entry_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Admin delete time entry"""
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(delete(TimeEntry).where(TimeEntry.id == entry_id))
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.DELETE, "time_entry", entry_id)
    
    return {"message": "Time entry deleted"}


# ==================== SHIFT SCHEDULING ====================

@api_router.post("/shifts", response_model=ShiftResponse)
async def create_shift(
    shift_data: ShiftCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get staff name
    staff_result = await db.execute(select(User).where(User.id == shift_data.staff_id))
    staff = staff_result.scalar_one_or_none()
    staff_name = staff.full_name if staff else "Unknown"
    
    shift = Shift(**shift_data.model_dump(), staff_name=staff_name)
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    
    await create_audit_log(db, user.id, AuditAction.CREATE, "shift", shift.id)
    
    return ShiftResponse.model_validate(shift)


@api_router.get("/shifts", response_model=List[ShiftResponse])
async def get_shifts(
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    query = select(Shift)
    
    if user.role == UserRole.STAFF:
        query = query.where(Shift.staff_id == user.id)
    elif user.role == UserRole.ADMIN and staff_id:
        query = query.where(Shift.staff_id == staff_id)
    elif user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if start_date:
        query = query.where(Shift.start_time >= start_date)
    if end_date:
        query = query.where(Shift.start_time <= end_date)
    
    query = query.order_by(Shift.start_time.asc())
    
    result = await db.execute(query)
    shifts = result.scalars().all()
    
    return [ShiftResponse.model_validate(s) for s in shifts]


@api_router.patch("/shifts/{shift_id}")
async def update_shift(
    shift_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(Shift).where(Shift.id == shift_id))
    shift = result.scalar_one_or_none()
    
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    allowed_fields = ['staff_id', 'start_time', 'end_time', 'notes', 'location_id']
    for field in allowed_fields:
        if field in update_data:
            if field in ['start_time', 'end_time'] and isinstance(update_data[field], str):
                setattr(shift, field, datetime.fromisoformat(update_data[field].replace('Z', '+00:00')))
            else:
                setattr(shift, field, update_data[field])
    
    # Update staff name if staff_id changed
    if 'staff_id' in update_data:
        staff_result = await db.execute(select(User).where(User.id == update_data['staff_id']))
        staff = staff_result.scalar_one_or_none()
        shift.staff_name = staff.full_name if staff else "Unknown"
    
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "shift", shift_id)
    
    return {"message": "Shift updated"}


@api_router.delete("/shifts/{shift_id}")
async def delete_shift(
    shift_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(delete(Shift).where(Shift.id == shift_id))
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.DELETE, "shift", shift_id)
    
    return {"message": "Shift deleted"}


# ==================== INCIDENT ROUTES ====================

@api_router.post("/incidents", response_model=IncidentResponse)
async def create_incident(
    incident_data: IncidentCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    incident = Incident(**incident_data.model_dump(), reported_by=user.id)
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    
    await create_audit_log(db, user.id, AuditAction.INCIDENT, "incident", incident.id)
    
    return IncidentResponse.model_validate(incident)


@api_router.get("/incidents", response_model=List[IncidentResponse])
async def get_incidents(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    result = await db.execute(select(Incident).order_by(Incident.created_at.desc()))
    incidents = result.scalars().all()
    
    return [IncidentResponse.model_validate(i) for i in incidents]


@api_router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return IncidentResponse.model_validate(incident)


@api_router.patch("/incidents/{incident_id}")
async def update_incident(
    incident_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    allowed_fields = ['title', 'description', 'severity', 'resolved', 'resolution_notes']
    for field in allowed_fields:
        if field in update_data:
            setattr(incident, field, update_data[field])
    
    if update_data.get('resolved') and not incident.resolved_at:
        incident.resolved_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "incident", incident_id)
    
    return {"message": "Incident updated"}


@api_router.delete("/incidents/{incident_id}")
async def delete_incident(
    incident_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(delete(Incident).where(Incident.id == incident_id))
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.DELETE, "incident", incident_id)
    
    return {"message": "Incident deleted"}


# ==================== ADMIN CUSTOMER ROUTES ====================

@api_router.post("/admin/customers")
async def create_customer(
    customer_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Admin create customer account"""
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if email exists
    result = await db.execute(select(User).where(User.email == customer_data['email']))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    household_id = str(uuid.uuid4())
    
    new_customer = User(
        email=customer_data['email'],
        hashed_password=hash_password(customer_data.get('password', 'TempPass123!')),
        full_name=customer_data['full_name'],
        phone=customer_data.get('phone'),
        role=UserRole.CUSTOMER,
        household_id=household_id,
        is_active=True
    )
    
    db.add(new_customer)
    await db.commit()
    await db.refresh(new_customer)
    
    await create_audit_log(db, user.id, AuditAction.CREATE, "user", new_customer.id, {"created_by_admin": True})
    
    return {
        "message": "Customer created successfully",
        "customer": UserResponse.model_validate(new_customer).model_dump()
    }


@api_router.patch("/admin/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Admin update customer"""
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(User).where(User.id == customer_id))
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    allowed_fields = ['full_name', 'phone', 'email', 'is_active']
    for field in allowed_fields:
        if field in update_data:
            setattr(customer, field, update_data[field])
    
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "user", customer_id)
    
    # Invalidate cache
    if cache:
        await cache.invalidate_user(customer_id)
    
    return {"message": "Customer updated successfully"}


@api_router.delete("/admin/customers/{customer_id}")
async def delete_customer(
    customer_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """Admin delete customer (soft delete)"""
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(User).where(User.id == customer_id))
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer.is_active = False
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.DELETE, "user", customer_id)
    
    if cache:
        await cache.invalidate_user(customer_id)
    
    return {"message": "Customer deactivated"}


# ==================== REVIEW ROUTES ====================

@api_router.post("/reviews", response_model=ReviewResponse)
async def create_review(
    review_data: ReviewCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    review = Review(**review_data.model_dump(), household_id=user.household_id)
    db.add(review)
    await db.commit()
    await db.refresh(review)
    
    return ReviewResponse.model_validate(review)


@api_router.get("/reviews", response_model=List[ReviewResponse])
async def get_reviews(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review).where(Review.public == True))
    reviews = result.scalars().all()
    return [ReviewResponse.model_validate(r) for r in reviews]


# ==================== AUDIT LOG ROUTES ====================

@api_router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500))
    logs = result.scalars().all()
    
    return [AuditLogResponse.model_validate(log) for log in logs]


# ==================== ADMIN USER ROUTES ====================

@api_router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(
    role: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if role:
        result = await db.execute(select(User).where(User.role == UserRole(role)))
    else:
        result = await db.execute(select(User))
    
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@api_router.patch("/admin/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    target_user.is_active = is_active
    await db.commit()
    
    await create_audit_log(db, user.id, AuditAction.UPDATE, "user", user_id, {"is_active": is_active})
    
    if cache:
        await cache.invalidate_user(user_id)
    
    return {"message": f"User {'activated' if is_active else 'deactivated'}"}


# ==================== DASHBOARD STATS ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    # Try cache first
    cache_key = f"dashboard_{user.role.value}"
    if cache:
        cached = await cache.get_stats(cache_key)
        if cached:
            return cached
    
    now = datetime.now(timezone.utc)
    
    # Active bookings
    active_result = await db.execute(
        select(sql_func.count(Booking.id)).where(
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN])
        )
    )
    active_bookings = active_result.scalar() or 0
    
    # Today's check-ins
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    checkin_result = await db.execute(
        select(sql_func.count(Booking.id)).where(
            and_(
                Booking.check_in_date >= today_start,
                Booking.check_in_date < today_end,
                Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN])
            )
        )
    )
    todays_checkins = checkin_result.scalar() or 0
    
    # Pending tasks
    tasks_result = await db.execute(
        select(sql_func.count(Task.id)).where(Task.status == TaskStatus.PENDING)
    )
    pending_tasks = tasks_result.scalar() or 0
    
    # Total customers
    customers_result = await db.execute(
        select(sql_func.count(User.id)).where(User.role == UserRole.CUSTOMER)
    )
    total_customers = customers_result.scalar() or 0
    
    stats = {
        "active_bookings": active_bookings,
        "todays_checkins": todays_checkins,
        "pending_tasks": pending_tasks,
        "total_customers": total_customers
    }
    
    # Cache results
    if cache:
        await cache.set_stats(cache_key, stats)
    
    return stats


# ==================== REVENUE ANALYTICS ====================

@api_router.get("/admin/revenue/summary")
async def get_revenue_summary(
    period: str = "30d",
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Try cache
    cache_key = f"revenue_summary_{period}"
    if cache:
        cached = await cache.get_stats(cache_key)
        if cached:
            return cached
    
    now = datetime.now(timezone.utc)
    
    if period == "7d":
        start_date = now - timedelta(days=7)
        prev_start = start_date - timedelta(days=7)
    elif period == "1y":
        start_date = now - timedelta(days=365)
        prev_start = start_date - timedelta(days=365)
    else:  # 30d default
        start_date = now - timedelta(days=30)
        prev_start = start_date - timedelta(days=30)
    
    # Current period revenue
    current_result = await db.execute(
        select(sql_func.sum(Booking.total_price)).where(
            and_(
                Booking.created_at >= start_date,
                Booking.payment_status == "completed"
            )
        )
    )
    current_revenue = current_result.scalar() or 0
    
    # Previous period revenue
    prev_result = await db.execute(
        select(sql_func.sum(Booking.total_price)).where(
            and_(
                Booking.created_at >= prev_start,
                Booking.created_at < start_date,
                Booking.payment_status == "completed"
            )
        )
    )
    prev_revenue = prev_result.scalar() or 0
    
    # Booking count
    booking_count_result = await db.execute(
        select(sql_func.count(Booking.id)).where(Booking.created_at >= start_date)
    )
    total_bookings = booking_count_result.scalar() or 0
    
    prev_booking_count_result = await db.execute(
        select(sql_func.count(Booking.id)).where(
            and_(Booking.created_at >= prev_start, Booking.created_at < start_date)
        )
    )
    prev_bookings = prev_booking_count_result.scalar() or 0
    
    # Calculate changes
    revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    booking_change = ((total_bookings - prev_bookings) / prev_bookings * 100) if prev_bookings > 0 else 0
    
    avg_value = current_revenue / total_bookings if total_bookings > 0 else 0
    prev_avg = prev_revenue / prev_bookings if prev_bookings > 0 else 0
    avg_change = ((avg_value - prev_avg) / prev_avg * 100) if prev_avg > 0 else 0
    
    summary = {
        "total_revenue": round(current_revenue, 2),
        "revenue_change": round(revenue_change, 1),
        "total_bookings": total_bookings,
        "booking_change": round(booking_change, 1),
        "average_booking_value": round(avg_value, 2),
        "avg_change": round(avg_change, 1),
        "period": period
    }
    
    if cache:
        await cache.set_stats(cache_key, summary)
    
    return summary


@api_router.get("/admin/revenue/trends")
async def get_revenue_trends(
    period: str = "30d",
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    
    if period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "1y":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)
    
    result = await db.execute(
        select(Booking).where(
            and_(Booking.created_at >= start_date, Booking.payment_status == "completed")
        ).order_by(Booking.created_at.asc())
    )
    bookings = result.scalars().all()
    
    # Group by date
    trends = {}
    for booking in bookings:
        date_key = booking.created_at.strftime("%Y-%m-%d")
        if date_key not in trends:
            trends[date_key] = {"date": date_key, "revenue": 0, "bookings": 0}
        trends[date_key]["revenue"] += booking.total_price
        trends[date_key]["bookings"] += 1
    
    return list(trends.values())


@api_router.get("/admin/revenue/by-accommodation")
async def get_revenue_by_accommodation(
    period: str = "30d",
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    
    if period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "1y":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)
    
    result = await db.execute(
        select(Booking).where(
            and_(Booking.created_at >= start_date, Booking.payment_status == "completed")
        )
    )
    bookings = result.scalars().all()
    
    by_type = {"room": 0, "crate": 0}
    for booking in bookings:
        acc_type = booking.accommodation_type.value if booking.accommodation_type else "room"
        if acc_type in by_type:
            by_type[acc_type] += booking.total_price
    
    return [
        {"name": "Rooms", "value": round(by_type["room"], 2)},
        {"name": "Crates", "value": round(by_type["crate"], 2)}
    ]


# ==================== CHAT ROUTES ====================

@api_router.get("/chats", response_model=List[ChatResponse])
async def get_chats(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    # Use JSON contains query
    result = await db.execute(select(Chat).order_by(Chat.last_message_at.desc().nullslast()))
    all_chats = result.scalars().all()
    
    # Filter chats where user is a participant
    user_chats = [c for c in all_chats if user.id in (c.participants or [])]
    
    return [ChatResponse.model_validate(c) for c in user_chats]


@api_router.post("/chats", response_model=ChatResponse)
async def create_chat(
    chat_data: ChatCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    # Get other participant
    other_result = await db.execute(select(User).where(User.id == chat_data.participant_id))
    other_user = other_result.scalar_one_or_none()
    
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if chat already exists
    result = await db.execute(select(Chat))
    all_chats = result.scalars().all()
    
    existing_chat = None
    for c in all_chats:
        if user.id in (c.participants or []) and chat_data.participant_id in (c.participants or []):
            existing_chat = c
            break
    
    if existing_chat:
        return ChatResponse.model_validate(existing_chat)
    
    # Create new chat
    chat = Chat(
        chat_type=chat_data.chat_type,
        participants=[user.id, chat_data.participant_id],
        participant_names={user.id: user.full_name, chat_data.participant_id: other_user.full_name},
        unread_count={user.id: 0, chat_data.participant_id: 0}
    )
    
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    
    return ChatResponse.model_validate(chat)


@api_router.get("/chats/{chat_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    chat_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    # Verify chat access
    chat_result = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = chat_result.scalar_one_or_none()
    
    if not chat or user.id not in (chat.participants or []):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Mark messages as read
    await db.execute(
        update(ChatMessage)
        .where(and_(ChatMessage.chat_id == chat_id, ChatMessage.sender_id != user.id))
        .values(read=True)
    )
    
    # Reset unread count
    if chat.unread_count:
        chat.unread_count[user.id] = 0
        await db.commit()
    
    # Get messages
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    
    return [ChatMessageResponse.model_validate(m) for m in messages]


@api_router.post("/chats/{chat_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    chat_id: str,
    message_data: ChatMessageCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    # Verify chat access
    chat_result = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = chat_result.scalar_one_or_none()
    
    if not chat or user.id not in (chat.participants or []):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create message
    message = ChatMessage(
        chat_id=chat_id,
        sender_id=user.id,
        sender_name=user.full_name,
        sender_role=user.role,
        content=message_data.content
    )
    
    db.add(message)
    
    # Update chat metadata
    chat.last_message = message_data.content[:100]
    chat.last_message_at = datetime.now(timezone.utc)
    
    # Increment unread for other participants
    unread = chat.unread_count or {}
    for participant_id in chat.participants or []:
        if participant_id != user.id:
            unread[participant_id] = unread.get(participant_id, 0) + 1
    chat.unread_count = unread
    
    await db.commit()
    await db.refresh(message)
    
    return ChatMessageResponse.model_validate(message)


@api_router.get("/chat/users")
async def get_chat_users(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    user = await get_current_user(credentials, db, cache)
    
    if user.role == UserRole.CUSTOMER:
        # Customers can chat with staff/admin
        result = await db.execute(
            select(User).where(
                and_(User.role.in_([UserRole.STAFF, UserRole.ADMIN]), User.is_active == True)
            )
        )
    elif user.role in [UserRole.STAFF, UserRole.ADMIN]:
        # Staff/Admin can chat with everyone
        result = await db.execute(
            select(User).where(and_(User.id != user.id, User.is_active == True))
        )
    else:
        return []
    
    users = result.scalars().all()
    
    return [{
        "id": u.id,
        "full_name": u.full_name,
        "role": u.role.value
    } for u in users]


# ==================== HEALTH CHECK ====================

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "postgresql",
        "cache": "redis" if cache_service else "disabled",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
