"""
Pydantic Schemas for API Request/Response Validation
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================

class UserRole(str, Enum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ADMIN = "admin"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class UpdateStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    PAYMENT = "payment"
    INCIDENT = "incident"


class TimeModificationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ChatType(str, Enum):
    ADMIN_STAFF = "admin_staff"
    KENNEL_CUSTOMER = "kennel_customer"


# ==================== USER SCHEMAS ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.CUSTOMER


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    household_id: Optional[str] = None
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse


# ==================== LOCATION SCHEMAS ====================

class LocationCreate(BaseModel):
    name: str
    address: str
    capacity: int
    contact_email: EmailStr
    contact_phone: str


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    address: str
    capacity: int
    contact_email: str
    contact_phone: str
    created_at: datetime
    updated_at: datetime


# ==================== DOG SCHEMAS ====================

class VaccinationRecord(BaseModel):
    vaccine_name: str
    date_administered: datetime
    expiry_date: Optional[datetime] = None
    document_url: Optional[str] = None


class DogCreate(BaseModel):
    name: str
    breed: str
    age: Optional[int] = None
    weight: Optional[float] = None
    photo_url: Optional[str] = None
    vaccination_file_url: Optional[str] = None
    gender: Optional[str] = None
    color: Optional[str] = None
    birthday: Optional[datetime] = None
    meal_routine: Optional[str] = None
    medication_requirements: Optional[str] = None
    allergies: Optional[str] = None
    friendly_to_cats: Optional[bool] = None
    friendly_with_dogs: Optional[bool] = None
    seizure_activity: Optional[bool] = None
    afraid_of_thunder: Optional[bool] = None
    afraid_of_fireworks: Optional[bool] = None
    resource_guarding: Optional[bool] = None
    fence_aggression: Optional[bool] = None
    incidents_of_aggression: Optional[str] = None
    other_notes: Optional[str] = None


class DogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    breed: str
    age: Optional[int] = None
    weight: Optional[float] = None
    household_id: str
    photo_url: Optional[str] = None
    vaccinations: List[VaccinationRecord] = []
    behavioral_notes: Optional[str] = None
    medical_flags: List[str] = []
    created_at: datetime
    updated_at: datetime


# ==================== BOOKING SCHEMAS ====================

class BookingCreate(BaseModel):
    dog_ids: List[str]
    location_id: str
    accommodation_type: str
    check_in_date: datetime
    check_out_date: datetime
    notes: Optional[str] = None
    special_request: Optional[str] = None
    needs_separate_playtime: bool = False


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    household_id: str
    dog_ids: List[str]
    location_id: str
    check_in_date: datetime
    check_out_date: datetime
    status: BookingStatus
    total_price: float
    notes: Optional[str] = None
    payment_status: str
    payment_type: Optional[str] = "invoice"
    customer_id: Optional[str] = None
    accommodation_type: Optional[str] = None
    is_holiday_pricing: Optional[bool] = False
    needs_separate_playtime: Optional[bool] = False
    separate_playtime_fee: Optional[float] = 0.0
    created_at: datetime
    updated_at: datetime


# ==================== DAILY UPDATE SCHEMAS ====================

class MediaItem(BaseModel):
    url: str
    type: str  # photo or video
    caption: Optional[str] = None
    uploaded_by: str
    uploaded_at: datetime
    dog_ids: List[str] = []
    watermarked: bool = True
    purchased: bool = False


class DailyUpdateCreate(BaseModel):
    household_id: str
    booking_id: str
    staff_notes: Optional[str] = None


class DailyUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    household_id: str
    booking_id: str
    date: datetime
    media_items: List[MediaItem] = []
    ai_summary: Optional[str] = None
    status: UpdateStatus
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ==================== TASK SCHEMAS ====================

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    location_id: str
    due_date: Optional[datetime] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    location_id: str
    due_date: Optional[datetime] = None
    status: TaskStatus
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    completed_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ==================== TIME ENTRY SCHEMAS ====================

class TimeEntryCreate(BaseModel):
    staff_id: str
    location_id: str


class TimeEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    staff_id: str
    staff_name: Optional[str] = None
    clock_in: datetime
    clock_out: Optional[datetime] = None
    location_id: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TimeModificationRequestCreate(BaseModel):
    time_entry_id: str
    requested_clock_in: datetime
    requested_clock_out: Optional[datetime] = None
    reason: str


class TimeModificationRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    time_entry_id: str
    staff_id: str
    staff_name: str
    original_clock_in: datetime
    original_clock_out: Optional[datetime] = None
    requested_clock_in: datetime
    requested_clock_out: Optional[datetime] = None
    reason: str
    status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ==================== SHIFT SCHEMAS ====================

class ShiftCreate(BaseModel):
    staff_id: str
    location_id: str
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None


class ShiftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    staff_id: str
    staff_name: Optional[str] = None
    location_id: str
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ==================== AUDIT LOG SCHEMAS ====================

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    created_at: datetime


# ==================== INCIDENT SCHEMAS ====================

class IncidentCreate(BaseModel):
    title: str
    description: str
    severity: str
    dog_id: Optional[str] = None
    booking_id: Optional[str] = None
    location_id: str


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    description: str
    severity: str
    dog_id: Optional[str] = None
    reported_by: str
    location_id: str
    resolved: bool
    created_at: datetime
    updated_at: datetime


# ==================== REVIEW SCHEMAS ====================

class ReviewCreate(BaseModel):
    booking_id: str
    rating: int
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    household_id: str
    booking_id: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime


# ==================== CHAT SCHEMAS ====================

class ChatCreate(BaseModel):
    chat_type: ChatType
    participant_id: str  # The other participant


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    chat_type: str
    participants: List[str]
    participant_names: Dict[str, str]
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: Dict[str, int] = {}
    created_at: datetime
    updated_at: datetime


class ChatMessageCreate(BaseModel):
    chat_id: str
    content: str


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    chat_id: str
    sender_id: str
    sender_name: str
    sender_role: str
    content: str
    read: bool
    created_at: datetime
