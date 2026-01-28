from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
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
    
    # Simple pricing calculation
    base_price = 50.0  # per night per dog
    total_price = base_price * nights * len(booking_data.dog_ids)
    
    booking = Booking(
        **booking_data.model_dump(),
        household_id=user.household_id,
        status=BookingStatus.PENDING,
        total_price=total_price
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
    
    result = await database.bookings.update_one(
        {"id": booking_id},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    await create_audit_log(user.id, AuditAction.UPDATE, "booking", booking_id, {"status": status})
    
    return {"message": "Status updated", "status": status}

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
    
    media_item = MediaItem(
        url=file_url,
        type="photo" if file.content_type.startswith("image") else "video",
        caption=caption,
        uploaded_by=user.id
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
    
    # Generate AI summary
    summary = await generate_daily_summary(
        dog_names=dog_names,
        staff_notes=update_doc.get('staff_notes', ''),
        media_count=len(update_doc.get('media_items', []))
    )
    
    # Update document
    await database.daily_updates.update_one(
        {"id": update_id},
        {"$set": {"ai_summary": summary, "status": UpdateStatus.PENDING_APPROVAL}}
    )
    
    return {"message": "Summary generated", "summary": summary}

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

# ==================== TIME TRACKING ROUTES ====================

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
