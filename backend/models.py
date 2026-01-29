from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid

# Enums
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

# Base Model Configuration
class BaseDBModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# User Models
class User(BaseDBModel):
    email: EmailStr
    hashed_password: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    location_id: Optional[str] = None
    is_active: bool = True
    household_id: Optional[str] = None  # For customers
    reset_token: Optional[str] = None
    reset_token_expiry: Optional[datetime] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.CUSTOMER

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
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

# Location Models
class Location(BaseDBModel):
    name: str
    address: str
    capacity: int
    contact_email: EmailStr
    contact_phone: str

class LocationCreate(BaseModel):
    name: str
    address: str
    capacity: int
    contact_email: EmailStr
    contact_phone: str

class LocationResponse(BaseDBModel):
    name: str
    address: str
    capacity: int
    contact_email: str
    contact_phone: str

# Dog Models
class VaccinationRecord(BaseModel):
    vaccine_name: str
    date_administered: datetime
    expiry_date: Optional[datetime] = None
    document_url: Optional[str] = None

class Dog(BaseDBModel):
    name: str
    breed: str
    age: Optional[int] = None
    weight: Optional[float] = None
    household_id: str
    photo_url: Optional[str] = None
    vaccinations: List[VaccinationRecord] = []
    vaccination_file_url: Optional[str] = None
    behavioral_notes: Optional[str] = None
    medical_flags: List[str] = []
    internal_notes: Optional[str] = None  # Staff only
    
    # Detailed profile fields
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

class DogResponse(BaseDBModel):
    name: str
    breed: str
    age: Optional[int] = None
    weight: Optional[float] = None
    household_id: str
    photo_url: Optional[str] = None
    vaccinations: List[VaccinationRecord] = []
    behavioral_notes: Optional[str] = None
    medical_flags: List[str] = []
    diet_requirements: Optional[str] = None

# Booking Models
class AccommodationType(str, Enum):
    ROOM = "room"
    CRATE = "crate"

class PricingRule(BaseModel):
    base_price_per_night: float
    additional_dog_discount: float = 0.0  # percentage
    holiday_surcharge: float = 0.0  # percentage
    separate_playtime_fee: float = 0.0  # flat fee

class ItemChecklist(BaseModel):
    toys: bool = False
    bowls: bool = False
    food: bool = False
    blanket: bool = False
    medication: bool = False
    collar: bool = False
    leash: bool = False
    other_items: Optional[str] = None

class Booking(BaseDBModel):
    household_id: str
    dog_ids: List[str]
    location_id: str
    accommodation_type: AccommodationType
    check_in_date: datetime
    check_out_date: datetime
    status: BookingStatus
    total_price: float
    notes: Optional[str] = None
    special_request: Optional[str] = None
    payment_status: str = "pending"
    payment_intent_id: Optional[str] = None
    is_holiday_pricing: bool = False
    needs_separate_playtime: bool = False
    separate_playtime_fee: float = 0.0
    items_checklist: Optional[ItemChecklist] = None
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None

class BookingCreate(BaseModel):
    dog_ids: List[str]
    location_id: str
    accommodation_type: str
    check_in_date: datetime
    check_out_date: datetime
    notes: Optional[str] = None
    special_request: Optional[str] = None
    needs_separate_playtime: bool = False

class BookingResponse(BaseDBModel):
    household_id: str
    dog_ids: List[str]
    location_id: str
    check_in_date: datetime
    check_out_date: datetime
    status: BookingStatus
    total_price: float
    notes: Optional[str] = None
    payment_status: str

# Daily Update Models
class MediaItem(BaseModel):
    url: str
    type: str  # photo or video
    caption: Optional[str] = None
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dog_ids: List[str] = []  # Dogs tagged in this media
    watermarked: bool = True
    purchased: bool = False

class StaffSnippet(BaseModel):
    staff_id: str
    staff_name: str
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CustomerReaction(BaseModel):
    user_id: str
    reaction: str  # emoji or type
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CustomerComment(BaseModel):
    user_id: str
    user_name: str
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DailyUpdate(BaseDBModel):
    household_id: str
    booking_id: str
    date: datetime
    media_items: List[MediaItem] = []
    staff_snippets: List[StaffSnippet] = []
    ai_summary: Optional[str] = None
    status: UpdateStatus
    approved_by: Optional[str] = None
    sent_at: Optional[datetime] = None
    reactions: List[CustomerReaction] = []
    comments: List[CustomerComment] = []

class DailyUpdateCreate(BaseModel):
    household_id: str
    booking_id: str
    staff_notes: Optional[str] = None

class DailyUpdateResponse(BaseDBModel):
    household_id: str
    booking_id: str
    date: datetime
    media_items: List[MediaItem]
    ai_summary: Optional[str] = None
    staff_notes: Optional[str] = None
    status: UpdateStatus
    sent_at: Optional[datetime] = None

# Staff Task Models
class Task(BaseDBModel):
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    location_id: str
    due_date: Optional[datetime] = None
    status: TaskStatus
    completed_at: Optional[datetime] = None
    checklist_items: List[Dict[str, Any]] = []

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    location_id: str
    due_date: Optional[datetime] = None

class TaskResponse(BaseDBModel):
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    location_id: str
    due_date: Optional[datetime] = None
    status: TaskStatus
    completed_at: Optional[datetime] = None

# Time Tracking
class TimeEntry(BaseDBModel):
    staff_id: str
    clock_in: datetime
    clock_out: Optional[datetime] = None
    location_id: str
    notes: Optional[str] = None

class TimeEntryCreate(BaseModel):
    staff_id: str
    location_id: str

class TimeEntryResponse(BaseDBModel):
    staff_id: str
    clock_in: datetime
    clock_out: Optional[datetime] = None
    location_id: str
    notes: Optional[str] = None

# Audit Log
class AuditLog(BaseDBModel):
    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None

class AuditLogResponse(BaseDBModel):
    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any]
    created_at: datetime

# Incident Report
class Incident(BaseDBModel):
    title: str
    description: str
    severity: str  # low, medium, high, critical
    dog_id: Optional[str] = None
    booking_id: Optional[str] = None
    reported_by: str
    location_id: str
    evidence_urls: List[str] = []
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

class IncidentCreate(BaseModel):
    title: str
    description: str
    severity: str
    dog_id: Optional[str] = None
    booking_id: Optional[str] = None
    location_id: str

class IncidentResponse(BaseDBModel):
    title: str
    description: str
    severity: str
    dog_id: Optional[str] = None
    reported_by: str
    location_id: str
    resolved: bool
    created_at: datetime

# Review Models
class Review(BaseDBModel):
    household_id: str
    booking_id: str
    rating: int  # 1-5
    comment: Optional[str] = None
    approved: bool = False
    public: bool = False

class ReviewCreate(BaseModel):
    booking_id: str
    rating: int
    comment: Optional[str] = None

class ReviewResponse(BaseDBModel):
    household_id: str
    booking_id: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime

# Chat Models
class ChatType(str, Enum):
    ADMIN_STAFF = "admin_staff"
    KENNEL_CUSTOMER = "kennel_customer"

class ChatMessage(BaseDBModel):
    chat_id: str
    sender_id: str
    sender_name: str
    sender_role: UserRole
    content: str
    read: bool = False

class ChatMessageCreate(BaseModel):
    chat_id: str
    content: str

class ChatMessageResponse(BaseDBModel):
    chat_id: str
    sender_id: str
    sender_name: str
    sender_role: str
    content: str
    read: bool
    created_at: datetime

class Chat(BaseDBModel):
    chat_type: ChatType
    participants: List[str]  # user IDs
    participant_names: Dict[str, str] = {}  # user_id -> name mapping
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: Dict[str, int] = {}  # user_id -> unread count

class ChatCreate(BaseModel):
    chat_type: ChatType
    participant_id: str  # The other participant

class ChatResponse(BaseDBModel):
    chat_type: str
    participants: List[str]
    participant_names: Dict[str, str]
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: Dict[str, int] = {}
