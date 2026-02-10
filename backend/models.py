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
    PENDING_APPROVAL = "pending_approval"
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
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    notes: Optional[str] = None

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
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    notes: Optional[str] = None

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

class BookingType(str, Enum):
    STAY = "stay"
    DAYCARE = "daycare"
    MEET_GREET = "meet_greet"

class BookingPricingConfig(BaseModel):
    """Simple booking pricing configuration"""
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
    booking_type: str = "stay"  # stay, daycare, meet_greet
    notes: Optional[str] = None
    special_request: Optional[str] = None
    payment_status: str = "pending"
    payment_intent_id: Optional[str] = None
    payment_type: str = "invoice"  # 'immediate' or 'invoice'
    is_holiday_pricing: bool = False
    needs_separate_playtime: bool = False
    separate_playtime_fee: float = 0.0
    items_checklist: Optional[ItemChecklist] = None
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None
    customer_id: Optional[str] = None
    created_by: Optional[str] = None
    modification_reason: Optional[str] = None
    # Phase 1 additions
    service_type_id: Optional[str] = None
    add_ons: List[Dict[str, Any]] = []  # List of BookingAddOn
    subtotal: float = 0.0
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    deposit_percentage: float = 50.0
    deposit_amount: float = 0.0
    deposit_paid: bool = False
    deposit_paid_at: Optional[datetime] = None
    balance_due: float = 0.0
    balance_paid: bool = False
    balance_paid_at: Optional[datetime] = None
    invoice_id: Optional[str] = None
    pricing_rules_applied: List[str] = []  # IDs of applied pricing rules
    requires_approval: bool = False  # True if over soft capacity
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    cancellation_policy_id: Optional[str] = None

class BookingCreate(BaseModel):
    dog_ids: List[str]
    location_id: str
    accommodation_type: str
    check_in_date: datetime
    check_out_date: datetime
    notes: Optional[str] = None
    special_request: Optional[str] = None
    needs_separate_playtime: bool = False
    # Phase 1 additions
    service_type_id: Optional[str] = None
    add_on_ids: List[str] = []
    add_on_quantities: Dict[str, int] = {}  # add_on_id -> quantity

class BookingResponse(BaseDBModel):
    household_id: str
    dog_ids: List[str]
    location_id: Optional[str] = None
    check_in_date: datetime
    check_out_date: datetime
    status: BookingStatus
    total_price: float
    notes: Optional[str] = None
    payment_status: Optional[str] = "pending"
    payment_type: Optional[str] = "invoice"
    customer_id: Optional[str] = None
    accommodation_type: Optional[str] = None
    is_holiday_pricing: Optional[bool] = False
    needs_separate_playtime: Optional[bool] = False
    separate_playtime_fee: Optional[float] = 0.0
    # Phase 1 additions
    service_type_id: Optional[str] = None
    add_ons: List[Dict[str, Any]] = []
    subtotal: Optional[float] = 0.0
    tax_amount: Optional[float] = 0.0
    discount_amount: Optional[float] = 0.0
    deposit_percentage: Optional[float] = 50.0
    deposit_amount: Optional[float] = 0.0
    deposit_paid: Optional[bool] = False
    balance_due: Optional[float] = 0.0
    balance_paid: Optional[bool] = False
    requires_approval: Optional[bool] = False
    invoice_id: Optional[str] = None

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
    completed_by: Optional[str] = None
    completed_by_name: Optional[str] = None
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
    completed_by: Optional[str] = None
    completed_by_name: Optional[str] = None

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
    staff_name: Optional[str] = None
    clock_in: datetime
    clock_out: Optional[datetime] = None
    location_id: str
    notes: Optional[str] = None

class TimeModificationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class TimeModificationRequest(BaseDBModel):
    time_entry_id: str
    staff_id: str
    staff_name: str
    original_clock_in: datetime
    original_clock_out: Optional[datetime] = None
    requested_clock_in: datetime
    requested_clock_out: Optional[datetime] = None
    reason: str
    status: TimeModificationStatus = TimeModificationStatus.PENDING
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

class TimeModificationRequestCreate(BaseModel):
    time_entry_id: str
    requested_clock_in: datetime
    requested_clock_out: Optional[datetime] = None
    reason: str

class TimeModificationRequestResponse(BaseDBModel):
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

# Shift Scheduling
class Shift(BaseDBModel):
    staff_id: str
    staff_name: Optional[str] = None
    location_id: str
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None

class ShiftCreate(BaseModel):
    staff_id: str
    location_id: str
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None

class ShiftResponse(BaseDBModel):
    staff_id: str
    staff_name: Optional[str] = None
    location_id: str
    start_time: datetime
    end_time: datetime
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



# ==================== PHASE 1: DATA & RULES FOUNDATION ====================

# Enums for new models
class PriceType(str, Enum):
    FLAT = "flat"  # One-time fee
    PER_DAY = "per_day"  # Per day of stay
    PER_DOG = "per_dog"  # Per dog
    PER_DOG_PER_DAY = "per_dog_per_day"  # Per dog per day

class PricingRuleType(str, Enum):
    WEEKEND = "weekend"
    HOLIDAY = "holiday"
    SEASONAL = "seasonal"
    BLACKOUT = "blackout"  # No bookings allowed

class PaymentProvider(str, Enum):
    SQUARE = "square"
    CRYPTO = "crypto"
    MANUAL = "manual"  # Cash, check, etc.

class PaymentType(str, Enum):
    DEPOSIT = "deposit"
    BALANCE = "balance"
    FULL = "full"
    REFUND = "refund"

class RefundStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSED = "processed"
    DENIED = "denied"


# ==================== SERVICE TYPES ====================

class ServiceType(BaseDBModel):
    """Defines types of services (Boarding, Daycare, etc.)"""
    name: str
    description: Optional[str] = None
    base_price: float  # Base price per unit
    price_type: PriceType = PriceType.PER_DOG_PER_DAY
    is_overnight: bool = True  # True for boarding, False for daycare
    min_duration_days: int = 1
    max_duration_days: Optional[int] = None
    requires_vaccination: bool = True
    active: bool = True
    location_id: Optional[str] = None  # None = all locations
    sort_order: int = 0

class ServiceTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    base_price: float
    price_type: PriceType = PriceType.PER_DOG_PER_DAY
    is_overnight: bool = True
    min_duration_days: int = 1
    max_duration_days: Optional[int] = None
    requires_vaccination: bool = True
    active: bool = True
    location_id: Optional[str] = None
    sort_order: int = 0

class ServiceTypeResponse(BaseDBModel):
    name: str
    description: Optional[str] = None
    base_price: float
    price_type: PriceType
    is_overnight: bool
    min_duration_days: int
    max_duration_days: Optional[int] = None
    requires_vaccination: bool
    active: bool
    location_id: Optional[str] = None
    sort_order: int


# ==================== ADD-ONS ====================

class AddOn(BaseDBModel):
    """Add-on services customers can select during booking"""
    name: str
    description: Optional[str] = None
    price: float
    price_type: PriceType = PriceType.FLAT
    category: str = "general"  # bath, transport, playtime, feeding, etc.
    requires_staff_assignment: bool = False
    max_quantity: int = 1  # Max per booking
    active: bool = True
    location_id: Optional[str] = None  # None = all locations
    service_type_ids: List[str] = []  # Empty = applies to all service types
    sort_order: int = 0

class AddOnCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    price_type: PriceType = PriceType.FLAT
    category: str = "general"
    requires_staff_assignment: bool = False
    max_quantity: int = 1
    active: bool = True
    location_id: Optional[str] = None
    service_type_ids: List[str] = []
    sort_order: int = 0

class AddOnResponse(BaseDBModel):
    name: str
    description: Optional[str] = None
    price: float
    price_type: PriceType = PriceType.FLAT
    category: str = "general"
    requires_staff_assignment: bool = False
    max_quantity: int = 1
    active: bool = True
    location_id: Optional[str] = None
    service_type_ids: List[str] = []
    sort_order: int = 0


# ==================== BOOKING ADD-ON (Junction) ====================

class BookingAddOn(BaseModel):
    """Add-on attached to a specific booking"""
    add_on_id: str
    add_on_name: str
    quantity: int = 1
    unit_price: float
    total_price: float
    notes: Optional[str] = None


# ==================== CAPACITY RULES ====================

class CapacityRule(BaseDBModel):
    """Configurable capacity limits per location/service"""
    location_id: str
    service_type_id: Optional[str] = None  # None = applies to all services
    accommodation_type: Optional[str] = None  # room, crate, or None for total
    max_capacity: int
    buffer_capacity: int = 0  # Extra capacity for admin override
    effective_date: Optional[datetime] = None  # None = always active
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    active: bool = True

class CapacityRuleCreate(BaseModel):
    location_id: str
    service_type_id: Optional[str] = None
    accommodation_type: Optional[str] = None
    max_capacity: int
    buffer_capacity: int = 0
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    active: bool = True

class CapacityRuleResponse(BaseDBModel):
    location_id: str
    service_type_id: Optional[str] = None
    accommodation_type: Optional[str] = None
    max_capacity: int
    buffer_capacity: int = 0
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    active: bool = True


# ==================== PRICING RULES ====================

class PricingRule(BaseDBModel):
    """Dynamic pricing rules (weekends, holidays, seasonal, blackouts)"""
    name: str
    rule_type: PricingRuleType
    multiplier: float = 1.0  # 1.2 = 20% increase, 0.8 = 20% discount
    flat_adjustment: float = 0.0  # Added/subtracted from total
    start_date: Optional[datetime] = None  # For seasonal/specific dates
    end_date: Optional[datetime] = None
    recurring_yearly: bool = False  # True for holidays
    days_of_week: List[int] = []  # 0=Monday, 6=Sunday (for weekend rules)
    service_type_ids: List[str] = []  # Empty = applies to all
    location_id: Optional[str] = None  # None = all locations
    priority: int = 0  # Higher priority rules applied last
    active: bool = True
    description: Optional[str] = None

class PricingRuleCreate(BaseModel):
    name: str
    rule_type: PricingRuleType
    multiplier: float = 1.0
    flat_adjustment: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    recurring_yearly: bool = False
    days_of_week: List[int] = []
    service_type_ids: List[str] = []
    location_id: Optional[str] = None
    priority: int = 0
    active: bool = True
    description: Optional[str] = None

class PricingRuleResponse(BaseDBModel):
    name: str
    rule_type: PricingRuleType
    multiplier: float = 1.0
    flat_adjustment: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    recurring_yearly: bool = False
    days_of_week: List[int] = []
    service_type_ids: List[str] = []
    location_id: Optional[str] = None
    priority: int = 0
    active: bool = True
    description: Optional[str] = None


# ==================== CANCELLATION POLICY ====================

class CancellationPolicy(BaseDBModel):
    """Cancellation and refund policies"""
    name: str
    days_before_checkin: int  # Cancel X days before for this refund
    refund_percentage: float  # 100 = full refund, 50 = half, 0 = no refund
    refund_deposit_only: bool = False  # True = only refund deposit, not full amount
    applies_to_deposit: bool = True
    applies_to_balance: bool = True
    service_type_ids: List[str] = []  # Empty = applies to all
    location_id: Optional[str] = None
    active: bool = True
    is_default: bool = False
    description: Optional[str] = None

class CancellationPolicyCreate(BaseModel):
    name: str
    days_before_checkin: int
    refund_percentage: float
    refund_deposit_only: bool = False
    applies_to_deposit: bool = True
    applies_to_balance: bool = True
    service_type_ids: List[str] = []
    location_id: Optional[str] = None
    active: bool = True
    is_default: bool = False
    description: Optional[str] = None

class CancellationPolicyResponse(BaseDBModel):
    name: str
    days_before_checkin: int
    refund_percentage: float
    refund_deposit_only: bool = False
    applies_to_deposit: bool = True
    applies_to_balance: bool = True
    service_type_ids: List[str] = []
    location_id: Optional[str] = None
    active: bool = True
    is_default: bool = False
    description: Optional[str] = None


# ==================== SYSTEM SETTINGS ====================

class SystemSetting(BaseDBModel):
    """Key-value store for system configuration"""
    key: str
    value: str  # JSON-serialized for complex values
    value_type: str = "string"  # string, number, boolean, json
    category: str = "general"
    description: Optional[str] = None
    editable: bool = True


# ==================== PAYMENT RECORDS ====================

class Payment(BaseDBModel):
    """Payment transaction record"""
    booking_id: str
    household_id: str
    amount: float
    currency: str = "USD"
    payment_type: PaymentType
    provider: PaymentProvider
    provider_transaction_id: Optional[str] = None
    provider_receipt_url: Optional[str] = None
    status: str = "pending"  # pending, completed, failed, refunded
    refund_of: Optional[str] = None  # If this is a refund, reference original payment
    metadata: Dict[str, Any] = {}
    notes: Optional[str] = None
    processed_by: Optional[str] = None  # Staff ID if manual
    processed_at: Optional[datetime] = None

class PaymentCreate(BaseModel):
    booking_id: str
    amount: float
    currency: str = "USD"
    payment_type: PaymentType
    provider: PaymentProvider
    provider_transaction_id: Optional[str] = None
    notes: Optional[str] = None

class PaymentResponse(BaseDBModel):
    booking_id: str
    household_id: str
    amount: float
    currency: str
    payment_type: PaymentType
    provider: PaymentProvider
    provider_transaction_id: Optional[str] = None
    provider_receipt_url: Optional[str] = None
    status: str
    refund_of: Optional[str] = None
    processed_at: Optional[datetime] = None


# ==================== INVOICE ====================

class Invoice(BaseDBModel):
    """Invoice for booking payments"""
    booking_id: str
    household_id: str
    invoice_number: str
    subtotal: float
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    total_amount: float
    deposit_required: float
    deposit_paid: float = 0.0
    balance_due: float
    balance_paid: float = 0.0
    currency: str = "USD"
    status: str = "draft"  # draft, sent, partial, paid, overdue, cancelled
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    line_items: List[Dict[str, Any]] = []  # Itemized breakdown
    notes: Optional[str] = None
    sent_at: Optional[datetime] = None

class InvoiceResponse(BaseDBModel):
    booking_id: str
    household_id: str
    invoice_number: str
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    deposit_required: float
    deposit_paid: float
    balance_due: float
    balance_paid: float
    currency: str
    status: str
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    line_items: List[Dict[str, Any]]


# ==================== PRICE CALCULATION REQUEST/RESPONSE ====================

class PriceCalculationRequest(BaseModel):
    """Request to calculate booking price"""
    service_type_id: str
    location_id: str
    dog_ids: List[str]
    check_in_date: datetime
    check_out_date: datetime
    accommodation_type: str = "room"
    add_on_ids: List[str] = []
    add_on_quantities: Dict[str, int] = {}  # add_on_id -> quantity
    promo_code: Optional[str] = None

class PriceBreakdown(BaseModel):
    """Detailed price breakdown"""
    base_price: float
    nights: int
    dog_count: int
    service_subtotal: float
    add_ons_subtotal: float
    add_ons_detail: List[Dict[str, Any]] = []
    pricing_adjustments: List[Dict[str, Any]] = []  # Applied rules
    subtotal: float
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    total: float
    deposit_percentage: float
    deposit_amount: float
    balance_due: float
    is_over_capacity: bool = False
    requires_approval: bool = False
    blocked_dates: List[str] = []  # Blackout dates in range
    warnings: List[str] = []



# ==================== PHASE 2: STAFF OPERATIONS ====================

class DogCompatibility(str, Enum):
    GOOD_WITH_ALL = "good_with_all"
    SELECTIVE = "selective"
    DOGS_ONLY = "dogs_only"
    SOLO_ONLY = "solo_only"

class FeedingFrequency(str, Enum):
    ONCE_DAILY = "once_daily"
    TWICE_DAILY = "twice_daily"
    THREE_TIMES = "three_times"
    FREE_FEED = "free_feed"
    CUSTOM = "custom"


class StaffAssignment(BaseDBModel):
    """Staff assigned to care for specific dogs"""
    staff_id: str
    staff_name: str
    dog_id: str
    dog_name: str
    booking_id: str
    assignment_date: datetime
    assignment_type: str = "primary"  # primary, backup, feeding, walking
    notes: Optional[str] = None
    active: bool = True

class StaffAssignmentCreate(BaseModel):
    staff_id: str
    dog_id: str
    booking_id: str
    assignment_date: datetime
    assignment_type: str = "primary"
    notes: Optional[str] = None

class StaffAssignmentResponse(BaseDBModel):
    staff_id: str
    staff_name: str
    dog_id: str
    dog_name: str
    booking_id: str
    assignment_date: datetime
    assignment_type: str
    notes: Optional[str] = None
    active: bool = True


class PlayGroup(BaseDBModel):
    """Group of compatible dogs for play sessions"""
    name: str
    dog_ids: List[str] = []
    dog_names: List[str] = []
    location_id: str
    scheduled_date: datetime
    scheduled_time: str  # "09:00", "14:00"
    duration_minutes: int = 60
    max_dogs: int = 6
    compatibility_level: DogCompatibility = DogCompatibility.GOOD_WITH_ALL
    supervisor_id: Optional[str] = None
    supervisor_name: Optional[str] = None
    notes: Optional[str] = None
    status: str = "scheduled"  # scheduled, in_progress, completed, cancelled
    completed_at: Optional[datetime] = None

class PlayGroupCreate(BaseModel):
    name: str
    dog_ids: List[str] = []
    location_id: str
    scheduled_date: datetime
    scheduled_time: str
    duration_minutes: int = 60
    max_dogs: int = 6
    compatibility_level: DogCompatibility = DogCompatibility.GOOD_WITH_ALL
    supervisor_id: Optional[str] = None
    notes: Optional[str] = None

class PlayGroupResponse(BaseDBModel):
    name: str
    dog_ids: List[str]
    dog_names: List[str] = []
    location_id: str
    scheduled_date: datetime
    scheduled_time: str
    duration_minutes: int
    max_dogs: int
    compatibility_level: DogCompatibility
    supervisor_id: Optional[str] = None
    supervisor_name: Optional[str] = None
    notes: Optional[str] = None
    status: str


class FeedingSchedule(BaseDBModel):
    """Feeding schedule for a dog during their stay"""
    dog_id: str
    dog_name: str
    booking_id: str
    frequency: FeedingFrequency = FeedingFrequency.TWICE_DAILY
    feeding_times: List[str] = ["08:00", "17:00"]  # Times in HH:MM
    food_type: str = "dry"  # dry, wet, raw, mixed
    portion_size: str = ""  # "1 cup", "2 scoops", etc.
    special_instructions: Optional[str] = None
    medications_with_food: List[str] = []
    allergies: List[str] = []
    treats_allowed: bool = True
    last_fed_at: Optional[datetime] = None
    last_fed_by: Optional[str] = None
    notes: Optional[str] = None

class FeedingScheduleCreate(BaseModel):
    dog_id: str
    booking_id: str
    frequency: FeedingFrequency = FeedingFrequency.TWICE_DAILY
    feeding_times: List[str] = ["08:00", "17:00"]
    food_type: str = "dry"
    portion_size: str = ""
    special_instructions: Optional[str] = None
    medications_with_food: List[str] = []
    allergies: List[str] = []
    treats_allowed: bool = True
    notes: Optional[str] = None

class FeedingScheduleResponse(BaseDBModel):
    dog_id: str
    dog_name: str
    booking_id: str
    frequency: FeedingFrequency
    feeding_times: List[str]
    food_type: str
    portion_size: str
    special_instructions: Optional[str] = None
    medications_with_food: List[str] = []
    allergies: List[str] = []
    treats_allowed: bool
    last_fed_at: Optional[datetime] = None
    last_fed_by: Optional[str] = None
    notes: Optional[str] = None


# ==================== PHASE 2: OPS DASHBOARD RESPONSES ====================

class DogOnSite(BaseModel):
    """Dog currently on site"""
    dog_id: str
    dog_name: str
    breed: str
    photo_url: Optional[str] = None
    household_id: str
    owner_name: str
    booking_id: str
    check_in_date: datetime
    check_out_date: datetime
    accommodation_type: str
    room_number: Optional[str] = None
    special_needs: List[str] = []
    feeding_schedule: Optional[str] = None
    assigned_staff: List[str] = []
    days_remaining: int = 0
    notes: Optional[str] = None

class ArrivalDeparture(BaseModel):
    """Arrival or departure record"""
    booking_id: str
    dog_ids: List[str]
    dog_names: List[str]
    owner_name: str
    owner_phone: Optional[str] = None
    scheduled_time: datetime
    accommodation_type: str
    type: str  # "arrival" or "departure"
    status: str  # "pending", "completed"
    special_instructions: Optional[str] = None
    items_checklist: Optional[Dict[str, Any]] = None

class CapacitySnapshot(BaseModel):
    """Current capacity status"""
    date: str
    total_capacity: int
    rooms_capacity: int
    crates_capacity: int
    total_occupied: int
    rooms_occupied: int
    crates_occupied: int
    total_available: int
    rooms_available: int
    crates_available: int
    arrivals_today: int
    departures_today: int
    requires_approval_count: int

class ApprovalQueueItem(BaseModel):
    """Booking requiring approval"""
    booking_id: str
    household_id: str
    customer_name: str
    customer_email: str
    dog_names: List[str]
    check_in_date: datetime
    check_out_date: datetime
    accommodation_type: str
    total_price: float
    reason: str  # "over_capacity", "blackout_date", "manual_review"
    submitted_at: datetime
    notes: Optional[str] = None


# ==================== PHASE 4: AUTOMATION & NOTIFICATIONS ====================

class NotificationType(str, Enum):
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_REMINDER = "booking_reminder"
    BOOKING_CANCELLED = "booking_cancelled"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_DUE = "payment_due"
    CHECK_IN_REMINDER = "check_in_reminder"
    CHECK_OUT_REMINDER = "check_out_reminder"
    DAILY_UPDATE = "daily_update"
    INCIDENT_REPORT = "incident_report"
    TASK_ASSIGNED = "task_assigned"
    TASK_DUE = "task_due"
    CUSTOM = "custom"

class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    PUSH = "push"

class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


class NotificationTemplate(BaseDBModel):
    """Reusable notification templates"""
    name: str
    notification_type: NotificationType
    channel: NotificationChannel
    subject: str  # For emails
    body: str  # Template with {{placeholders}}
    active: bool = True
    trigger_event: Optional[str] = None  # Event that triggers this
    delay_minutes: int = 0  # Delay after trigger
    conditions: Dict[str, Any] = {}  # Conditions for sending

class NotificationTemplateCreate(BaseModel):
    name: str
    notification_type: NotificationType
    channel: NotificationChannel
    subject: str
    body: str
    active: bool = True
    trigger_event: Optional[str] = None
    delay_minutes: int = 0
    conditions: Dict[str, Any] = {}

class NotificationTemplateResponse(BaseDBModel):
    name: str
    notification_type: NotificationType
    channel: NotificationChannel
    subject: str
    body: str
    active: bool
    trigger_event: Optional[str] = None
    delay_minutes: int
    conditions: Dict[str, Any] = {}


class Notification(BaseDBModel):
    """Individual notification instance"""
    user_id: str
    household_id: Optional[str] = None
    notification_type: NotificationType
    channel: NotificationChannel
    subject: str
    body: str
    status: NotificationStatus = NotificationStatus.PENDING
    reference_type: Optional[str] = None  # "booking", "payment", "task"
    reference_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

class NotificationResponse(BaseDBModel):
    user_id: str
    notification_type: NotificationType
    channel: NotificationChannel
    subject: str
    body: str
    status: NotificationStatus
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None


class AutomationRule(BaseDBModel):
    """Automation rules for triggered actions"""
    name: str
    description: Optional[str] = None
    trigger_event: str  # "booking.created", "booking.checked_in", "payment.completed"
    conditions: Dict[str, Any] = {}  # {"status": "confirmed", "days_until_checkin": {"$lte": 1}}
    actions: List[Dict[str, Any]] = []  # [{"type": "send_notification", "template_id": "..."}]
    active: bool = True
    priority: int = 0
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0

class AutomationRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_event: str
    conditions: Dict[str, Any] = {}
    actions: List[Dict[str, Any]] = []
    active: bool = True
    priority: int = 0

class AutomationRuleResponse(BaseDBModel):
    name: str
    description: Optional[str] = None
    trigger_event: str
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    active: bool
    priority: int
    last_triggered_at: Optional[datetime] = None
    trigger_count: int


class EventLog(BaseDBModel):
    """System event log for automation tracking"""
    event_type: str
    event_source: str  # "booking", "payment", "user", "system"
    source_id: Optional[str] = None
    user_id: Optional[str] = None
    data: Dict[str, Any] = {}
    triggered_automations: List[str] = []
    processed: bool = False
    processed_at: Optional[datetime] = None

class EventLogResponse(BaseDBModel):
    event_type: str
    event_source: str
    source_id: Optional[str] = None
    user_id: Optional[str] = None
    data: Dict[str, Any]
    triggered_automations: List[str]
    processed: bool


# ==================== CONNECTEAM PARITY: PHASE 1 ====================
# GPS, Time Clock, Breaks, Overtime, Forms, HR, Training, Announcements

# ==================== GPS & GEOFENCING ====================

class GPSRecord(BaseDBModel):
    """GPS location capture for clock events"""
    staff_id: str
    latitude: float
    longitude: float
    accuracy: float  # meters
    altitude: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "mobile"  # mobile, kiosk, manual
    event_type: str = "clock_in"  # clock_in, clock_out, break_start, break_end
    event_id: Optional[str] = None  # Reference to time entry or break


class GeofenceZone(BaseDBModel):
    """Geofence boundary for location verification"""
    name: str
    location_id: str
    latitude: float  # Center point
    longitude: float
    radius: float = 100.0  # meters, default 100m as specified
    is_active: bool = True
    require_within: bool = True  # If true, clock events must be within zone
    description: Optional[str] = None


class GeofenceZoneCreate(BaseModel):
    name: str
    location_id: str
    latitude: float
    longitude: float
    radius: float = 100.0
    is_active: bool = True
    require_within: bool = True
    description: Optional[str] = None


class GeofenceZoneResponse(BaseDBModel):
    name: str
    location_id: str
    latitude: float
    longitude: float
    radius: float
    is_active: bool
    require_within: bool
    description: Optional[str] = None


# ==================== ENHANCED TIME CLOCK ====================

class ClockEventType(str, Enum):
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"
    BREAK_START = "break_start"
    BREAK_END = "break_end"


class ClockEventSource(str, Enum):
    MOBILE = "mobile"
    KIOSK = "kiosk"
    WEB = "web"
    MANUAL = "manual"  # Admin correction


class DiscrepancyType(str, Enum):
    MISSING_CLOCK_OUT = "missing_clock_out"
    MISSING_CLOCK_IN = "missing_clock_in"
    LOCATION_MISMATCH = "location_mismatch"
    OUTSIDE_GEOFENCE = "outside_geofence"
    OUTSIDE_SCHEDULED_SHIFT = "outside_scheduled_shift"
    OVERTIME_EXCEEDED = "overtime_exceeded"
    BREAK_VIOLATION = "break_violation"


class EnhancedTimeEntry(BaseDBModel):
    """Extended time entry with GPS, breaks, and discrepancy tracking"""
    staff_id: str
    staff_name: Optional[str] = None
    location_id: str
    
    # Clock times
    clock_in: datetime
    clock_out: Optional[datetime] = None
    
    # GPS data
    clock_in_gps_id: Optional[str] = None
    clock_out_gps_id: Optional[str] = None
    clock_in_within_geofence: bool = True
    clock_out_within_geofence: Optional[bool] = None
    
    # Source tracking
    clock_in_source: ClockEventSource = ClockEventSource.MOBILE
    clock_out_source: Optional[ClockEventSource] = None
    
    # Shift association
    shift_id: Optional[str] = None
    
    # Calculated hours
    regular_hours: float = 0.0
    overtime_hours: float = 0.0
    double_time_hours: float = 0.0
    total_break_minutes: int = 0
    paid_break_minutes: int = 0
    unpaid_break_minutes: int = 0
    
    # Rounding applied
    rounded_clock_in: Optional[datetime] = None
    rounded_clock_out: Optional[datetime] = None
    rounding_rule_applied: Optional[str] = None
    
    # Status
    status: str = "active"  # active, approved, locked, flagged
    discrepancies: List[str] = []  # List of DiscrepancyType values
    
    # Approval
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    pay_period_id: Optional[str] = None
    
    # Notes
    notes: Optional[str] = None
    admin_notes: Optional[str] = None


class EnhancedTimeEntryCreate(BaseModel):
    location_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    source: ClockEventSource = ClockEventSource.MOBILE
    shift_id: Optional[str] = None
    notes: Optional[str] = None


class EnhancedTimeEntryResponse(BaseDBModel):
    staff_id: str
    staff_name: Optional[str] = None
    location_id: str
    clock_in: datetime
    clock_out: Optional[datetime] = None
    clock_in_within_geofence: bool
    clock_out_within_geofence: Optional[bool] = None
    clock_in_source: ClockEventSource
    clock_out_source: Optional[ClockEventSource] = None
    shift_id: Optional[str] = None
    regular_hours: float
    overtime_hours: float
    double_time_hours: float
    total_break_minutes: int
    status: str
    discrepancies: List[str] = []
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    pay_period_id: Optional[str] = None
    notes: Optional[str] = None


# ==================== BREAK TRACKING ====================

class BreakType(str, Enum):
    LUNCH = "lunch"
    REST = "rest"
    PERSONAL = "personal"
    OTHER = "other"


class BreakEntry(BaseDBModel):
    """Individual break within a time entry"""
    time_entry_id: str
    staff_id: str
    break_type: BreakType = BreakType.REST
    start_time: datetime
    end_time: Optional[datetime] = None
    is_paid: bool = False
    duration_minutes: Optional[int] = None  # Calculated on end
    
    # GPS
    start_gps_id: Optional[str] = None
    end_gps_id: Optional[str] = None
    
    notes: Optional[str] = None
    auto_deducted: bool = False  # True if auto-deducted by policy


class BreakEntryCreate(BaseModel):
    time_entry_id: str
    break_type: BreakType = BreakType.REST
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    notes: Optional[str] = None


class BreakEntryResponse(BaseDBModel):
    time_entry_id: str
    staff_id: str
    break_type: BreakType
    start_time: datetime
    end_time: Optional[datetime] = None
    is_paid: bool
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None


class BreakPolicy(BaseDBModel):
    """Break rules per location/role"""
    name: str
    location_id: Optional[str] = None  # None = all locations
    role: Optional[str] = None  # None = all roles
    
    # Break rules
    min_shift_for_break: float = 4.0  # Hours worked before break required
    break_duration_minutes: int = 30
    is_paid: bool = False
    auto_deduct: bool = False  # Auto-deduct if not taken
    
    # Multiple breaks
    second_break_after_hours: Optional[float] = None  # e.g., 8 hours
    second_break_duration_minutes: Optional[int] = None
    
    is_active: bool = True
    description: Optional[str] = None


class BreakPolicyCreate(BaseModel):
    name: str
    location_id: Optional[str] = None
    role: Optional[str] = None
    min_shift_for_break: float = 4.0
    break_duration_minutes: int = 30
    is_paid: bool = False
    auto_deduct: bool = False
    second_break_after_hours: Optional[float] = None
    second_break_duration_minutes: Optional[int] = None
    is_active: bool = True
    description: Optional[str] = None


class BreakPolicyResponse(BaseDBModel):
    name: str
    location_id: Optional[str] = None
    role: Optional[str] = None
    min_shift_for_break: float
    break_duration_minutes: int
    is_paid: bool
    auto_deduct: bool
    second_break_after_hours: Optional[float] = None
    second_break_duration_minutes: Optional[int] = None
    is_active: bool
    description: Optional[str] = None


# ==================== OVERTIME RULES ====================

class OvertimeRule(BaseDBModel):
    """Overtime calculation rules - weekly with admin-configurable limits"""
    name: str
    location_id: Optional[str] = None  # None = all locations
    
    # Weekly overtime (primary)
    weekly_regular_hours: float = 40.0  # Hours before OT kicks in
    weekly_overtime_multiplier: float = 1.5  # 1.5x pay
    
    # Double time (optional)
    weekly_double_time_hours: Optional[float] = None  # e.g., 60 hours
    double_time_multiplier: float = 2.0
    
    # Daily limits (optional, admin-configurable)
    daily_regular_hours: Optional[float] = None  # e.g., 8 hours
    daily_overtime_multiplier: Optional[float] = None
    
    # Caps
    max_weekly_hours: Optional[float] = None  # Hard cap
    max_daily_hours: Optional[float] = None
    
    is_active: bool = True
    priority: int = 0  # Higher priority rules override
    description: Optional[str] = None


class OvertimeRuleCreate(BaseModel):
    name: str
    location_id: Optional[str] = None
    weekly_regular_hours: float = 40.0
    weekly_overtime_multiplier: float = 1.5
    weekly_double_time_hours: Optional[float] = None
    double_time_multiplier: float = 2.0
    daily_regular_hours: Optional[float] = None
    daily_overtime_multiplier: Optional[float] = None
    max_weekly_hours: Optional[float] = None
    max_daily_hours: Optional[float] = None
    is_active: bool = True
    priority: int = 0
    description: Optional[str] = None


class OvertimeRuleResponse(BaseDBModel):
    name: str
    location_id: Optional[str] = None
    weekly_regular_hours: float
    weekly_overtime_multiplier: float
    weekly_double_time_hours: Optional[float] = None
    double_time_multiplier: float
    daily_regular_hours: Optional[float] = None
    daily_overtime_multiplier: Optional[float] = None
    max_weekly_hours: Optional[float] = None
    max_daily_hours: Optional[float] = None
    is_active: bool
    priority: int
    description: Optional[str] = None


# ==================== PUNCH ROUNDING ====================

class RoundingDirection(str, Enum):
    NEAREST = "nearest"
    UP = "up"
    DOWN = "down"


class PunchRoundingRule(BaseDBModel):
    """Punch rounding configuration"""
    name: str
    location_id: Optional[str] = None
    
    # Rounding interval in minutes (5, 10, 15, etc.)
    interval_minutes: int = 15
    
    # Direction
    clock_in_direction: RoundingDirection = RoundingDirection.NEAREST
    clock_out_direction: RoundingDirection = RoundingDirection.NEAREST
    
    # Grace period (optional)
    grace_period_minutes: int = 0  # Minutes before/after scheduled time
    
    is_active: bool = True
    description: Optional[str] = None


class PunchRoundingRuleCreate(BaseModel):
    name: str
    location_id: Optional[str] = None
    interval_minutes: int = 15
    clock_in_direction: RoundingDirection = RoundingDirection.NEAREST
    clock_out_direction: RoundingDirection = RoundingDirection.NEAREST
    grace_period_minutes: int = 0
    is_active: bool = True
    description: Optional[str] = None


class PunchRoundingRuleResponse(BaseDBModel):
    name: str
    location_id: Optional[str] = None
    interval_minutes: int
    clock_in_direction: RoundingDirection
    clock_out_direction: RoundingDirection
    grace_period_minutes: int
    is_active: bool
    description: Optional[str] = None


# ==================== PAY PERIODS & TIMESHEETS ====================

class PayPeriodType(str, Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"
    MONTHLY = "monthly"


class PayPeriodStatus(str, Enum):
    OPEN = "open"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    LOCKED = "locked"
    EXPORTED = "exported"


class PayPeriod(BaseDBModel):
    """Pay period for timesheet grouping and locking"""
    name: str
    location_id: Optional[str] = None  # None = all locations
    period_type: PayPeriodType = PayPeriodType.BIWEEKLY
    start_date: datetime
    end_date: datetime
    status: PayPeriodStatus = PayPeriodStatus.OPEN
    
    # Approval tracking
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    
    # Export tracking
    exported_at: Optional[datetime] = None
    export_format: Optional[str] = None  # csv, pdf
    export_url: Optional[str] = None
    
    notes: Optional[str] = None


class PayPeriodCreate(BaseModel):
    name: str
    location_id: Optional[str] = None
    period_type: PayPeriodType = PayPeriodType.BIWEEKLY
    start_date: datetime
    end_date: datetime
    notes: Optional[str] = None


class PayPeriodResponse(BaseDBModel):
    name: str
    location_id: Optional[str] = None
    period_type: PayPeriodType
    start_date: datetime
    end_date: datetime
    status: PayPeriodStatus
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    exported_at: Optional[datetime] = None
    notes: Optional[str] = None


class TimesheetSummary(BaseModel):
    """Summary of hours for a staff member in a pay period"""
    staff_id: str
    staff_name: str
    pay_period_id: str
    
    # Hours breakdown
    total_hours: float = 0.0
    regular_hours: float = 0.0
    overtime_hours: float = 0.0
    double_time_hours: float = 0.0
    
    # Breaks
    total_break_minutes: int = 0
    paid_break_minutes: int = 0
    unpaid_break_minutes: int = 0
    
    # Entries
    entry_count: int = 0
    entries_approved: int = 0
    entries_pending: int = 0
    entries_flagged: int = 0
    
    # Discrepancies
    discrepancy_count: int = 0
    discrepancies: List[Dict[str, Any]] = []


# ==================== SHIFT TEMPLATES & SWAPS ====================

class ShiftTemplate(BaseDBModel):
    """Reusable shift pattern"""
    name: str
    location_id: str
    
    # Time pattern (not actual dates)
    start_time: str  # "09:00" format
    end_time: str    # "17:00" format
    
    # Assignment
    role: Optional[str] = None  # staff, admin
    default_staff_id: Optional[str] = None
    
    # Recurrence
    days_of_week: List[int] = []  # 0=Monday, 6=Sunday
    is_active: bool = True
    
    # Attached items
    task_template_ids: List[str] = []  # Tasks auto-created with shift
    notes: Optional[str] = None
    color: Optional[str] = None  # For calendar display


class ShiftTemplateCreate(BaseModel):
    name: str
    location_id: str
    start_time: str
    end_time: str
    role: Optional[str] = None
    default_staff_id: Optional[str] = None
    days_of_week: List[int] = []
    is_active: bool = True
    task_template_ids: List[str] = []
    notes: Optional[str] = None
    color: Optional[str] = None


class ShiftTemplateResponse(BaseDBModel):
    name: str
    location_id: str
    start_time: str
    end_time: str
    role: Optional[str] = None
    default_staff_id: Optional[str] = None
    days_of_week: List[int]
    is_active: bool
    task_template_ids: List[str]
    notes: Optional[str] = None
    color: Optional[str] = None


class ShiftSwapStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ShiftSwapRequest(BaseDBModel):
    """Request to swap/trade shifts between staff"""
    shift_id: str
    requesting_staff_id: str
    requesting_staff_name: str
    target_staff_id: str
    target_staff_name: str
    
    # Optional: swap for another shift
    swap_shift_id: Optional[str] = None  # If trading shifts
    
    reason: Optional[str] = None
    status: ShiftSwapStatus = ShiftSwapStatus.PENDING
    
    # Approval
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None


class ShiftSwapRequestCreate(BaseModel):
    shift_id: str
    target_staff_id: str
    swap_shift_id: Optional[str] = None
    reason: Optional[str] = None


class ShiftSwapRequestResponse(BaseDBModel):
    shift_id: str
    requesting_staff_id: str
    requesting_staff_name: str
    target_staff_id: str
    target_staff_name: str
    swap_shift_id: Optional[str] = None
    reason: Optional[str] = None
    status: ShiftSwapStatus
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None


# Extend existing Shift model fields (to be added via migration)
class EnhancedShift(BaseDBModel):
    """Extended shift with template support and attachments"""
    staff_id: str
    staff_name: Optional[str] = None
    location_id: str
    start_time: datetime
    end_time: datetime
    
    # Template reference
    template_id: Optional[str] = None
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None  # iCal RRULE format
    
    # Status
    status: str = "scheduled"  # scheduled, in_progress, completed, cancelled
    
    # Planned vs actual
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    time_entry_id: Optional[str] = None  # Link to actual time entry
    
    # Attachments
    task_ids: List[str] = []
    form_ids: List[str] = []
    
    notes: Optional[str] = None
    color: Optional[str] = None
    
    # Publishing
    published: bool = False
    published_at: Optional[datetime] = None


# ==================== FORMS ENGINE ====================

class FormFieldType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    SELECT = "select"
    MULTISELECT = "multiselect"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    FILE = "file"
    PHOTO = "photo"  # Camera capture
    SIGNATURE = "signature"  # Signature pad
    GPS = "gps"  # Location stamp
    BARCODE = "barcode"  # Barcode/QR scanner
    SECTION = "section"  # Section divider
    INSTRUCTIONS = "instructions"  # Read-only text


class FormField(BaseModel):
    """Individual field in a form template"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    field_type: FormFieldType
    label: str
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    
    # Validation
    required: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # Regex pattern
    
    # Options (for select, multiselect, radio, checkbox)
    options: List[Dict[str, str]] = []  # [{"value": "x", "label": "X"}]
    
    # Conditional logic
    show_if: Optional[Dict[str, Any]] = None  # {"field_id": "x", "equals": "value"}
    
    # Layout
    order: int = 0
    width: str = "full"  # full, half, third


class FormTemplate(BaseDBModel):
    """Form template definition"""
    name: str
    description: Optional[str] = None
    location_id: Optional[str] = None  # None = all locations
    
    # Fields
    fields: List[FormField] = []
    
    # Assignment
    assignable_to: str = "all"  # all, staff, admin, role:xyz
    
    # Settings
    require_signature: bool = False
    require_gps: bool = False
    allow_save_draft: bool = True
    allow_edit_after_submit: bool = False
    
    # Notifications
    notify_on_submit: List[str] = []  # User IDs or roles
    
    # Status
    is_active: bool = True
    is_template: bool = True  # False for ad-hoc forms
    version: int = 1
    
    # Categories/tags
    category: Optional[str] = None
    tags: List[str] = []


class FormTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location_id: Optional[str] = None
    fields: List[Dict[str, Any]] = []
    assignable_to: str = "all"
    require_signature: bool = False
    require_gps: bool = False
    allow_save_draft: bool = True
    allow_edit_after_submit: bool = False
    notify_on_submit: List[str] = []
    is_active: bool = True
    category: Optional[str] = None
    tags: List[str] = []


class FormTemplateResponse(BaseDBModel):
    name: str
    description: Optional[str] = None
    location_id: Optional[str] = None
    fields: List[Dict[str, Any]]
    assignable_to: str
    require_signature: bool
    require_gps: bool
    allow_save_draft: bool
    allow_edit_after_submit: bool
    notify_on_submit: List[str]
    is_active: bool
    version: int
    category: Optional[str] = None
    tags: List[str]


class FormSubmissionStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class FormSubmission(BaseDBModel):
    """Completed form submission"""
    template_id: str
    template_name: str
    submitted_by: str
    submitted_by_name: str
    location_id: Optional[str] = None
    
    # Field values
    values: Dict[str, Any] = {}  # field_id -> value
    
    # Attachments (file URLs)
    attachments: List[Dict[str, str]] = []  # [{"field_id": "x", "url": "..."}]
    
    # Signature
    signature_data: Optional[str] = None  # Base64 or URL
    signature_timestamp: Optional[datetime] = None
    
    # GPS
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_accuracy: Optional[float] = None
    gps_timestamp: Optional[datetime] = None
    
    # Status
    status: FormSubmissionStatus = FormSubmissionStatus.DRAFT
    submitted_at: Optional[datetime] = None
    
    # Review
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    # Association
    related_type: Optional[str] = None  # booking, task, shift, etc.
    related_id: Optional[str] = None


class FormSubmissionCreate(BaseModel):
    template_id: str
    values: Dict[str, Any] = {}
    attachments: List[Dict[str, str]] = []
    signature_data: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_accuracy: Optional[float] = None
    status: FormSubmissionStatus = FormSubmissionStatus.DRAFT
    related_type: Optional[str] = None
    related_id: Optional[str] = None


class FormSubmissionResponse(BaseDBModel):
    template_id: str
    template_name: str
    submitted_by: str
    submitted_by_name: str
    location_id: Optional[str] = None
    values: Dict[str, Any]
    attachments: List[Dict[str, str]]
    signature_data: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    status: FormSubmissionStatus
    submitted_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    related_type: Optional[str] = None
    related_id: Optional[str] = None


# ==================== TASK TEMPLATES & CHECKLISTS ====================

class TaskTemplate(BaseDBModel):
    """Reusable task template"""
    name: str
    description: Optional[str] = None
    location_id: Optional[str] = None
    
    # Checklist items
    checklist_items: List[Dict[str, Any]] = []  # [{"text": "x", "required": true}]
    
    # Assignment rules
    assign_to_role: Optional[str] = None
    assign_to_team: Optional[str] = None
    assign_to_staff_id: Optional[str] = None
    
    # Timing
    default_due_hours: Optional[int] = None  # Hours after creation
    
    # Recurrence
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    
    # Forms
    form_template_ids: List[str] = []  # Forms to attach
    
    # Priority
    priority: str = "medium"  # low, medium, high, urgent
    
    # Reminders
    reminder_hours_before: List[int] = []  # e.g., [24, 2] = 24h and 2h before
    escalate_after_hours: Optional[int] = None
    escalate_to: Optional[str] = None  # User ID or role
    
    is_active: bool = True
    category: Optional[str] = None
    tags: List[str] = []


class TaskTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location_id: Optional[str] = None
    checklist_items: List[Dict[str, Any]] = []
    assign_to_role: Optional[str] = None
    assign_to_team: Optional[str] = None
    assign_to_staff_id: Optional[str] = None
    default_due_hours: Optional[int] = None
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    form_template_ids: List[str] = []
    priority: str = "medium"
    reminder_hours_before: List[int] = []
    escalate_after_hours: Optional[int] = None
    escalate_to: Optional[str] = None
    is_active: bool = True
    category: Optional[str] = None
    tags: List[str] = []


class TaskTemplateResponse(BaseDBModel):
    name: str
    description: Optional[str] = None
    location_id: Optional[str] = None
    checklist_items: List[Dict[str, Any]]
    assign_to_role: Optional[str] = None
    assign_to_team: Optional[str] = None
    assign_to_staff_id: Optional[str] = None
    default_due_hours: Optional[int] = None
    is_recurring: bool
    recurrence_rule: Optional[str] = None
    form_template_ids: List[str]
    priority: str
    reminder_hours_before: List[int]
    escalate_after_hours: Optional[int] = None
    escalate_to: Optional[str] = None
    is_active: bool
    category: Optional[str] = None
    tags: List[str]


class EnhancedTask(BaseDBModel):
    """Extended task with templates, assignments, and tracking"""
    title: str
    description: Optional[str] = None
    location_id: str
    
    # Template reference
    template_id: Optional[str] = None
    
    # Assignment
    assigned_to: Optional[str] = None  # User ID
    assigned_to_name: Optional[str] = None
    assigned_to_role: Optional[str] = None
    assigned_to_team: Optional[str] = None
    assigned_by: Optional[str] = None
    
    # Timing
    due_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Checklist
    checklist_items: List[Dict[str, Any]] = []  # [{"text": "x", "completed": false, "completed_by": null}]
    checklist_progress: float = 0.0  # 0-100
    
    # Status
    status: TaskStatus = TaskStatus.PENDING
    
    # Completion
    completed_by: Optional[str] = None
    completed_by_name: Optional[str] = None
    
    # Forms
    form_submission_ids: List[str] = []
    
    # Priority & escalation
    priority: str = "medium"
    escalated: bool = False
    escalated_at: Optional[datetime] = None
    escalated_to: Optional[str] = None
    
    # Reminders sent
    reminders_sent: List[datetime] = []
    
    # Association
    shift_id: Optional[str] = None
    booking_id: Optional[str] = None
    
    notes: Optional[str] = None
    tags: List[str] = []


# ==================== HR / TIME OFF ====================

class TimeOffType(str, Enum):
    VACATION = "vacation"
    SICK = "sick"
    PERSONAL = "personal"
    BEREAVEMENT = "bereavement"
    JURY_DUTY = "jury_duty"
    UNPAID = "unpaid"
    OTHER = "other"


class AccrualFrequency(str, Enum):
    PER_PAY_PERIOD = "per_pay_period"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ANNIVERSARY = "anniversary"


class TimeOffPolicy(BaseDBModel):
    """Time off accrual and rules policy"""
    name: str
    time_off_type: TimeOffType
    location_id: Optional[str] = None  # None = all locations
    
    # Accrual
    accrual_rate: float = 0.0  # Hours accrued per period
    accrual_frequency: AccrualFrequency = AccrualFrequency.PER_PAY_PERIOD
    accrual_start_date: Optional[datetime] = None  # When accrual begins for new staff
    
    # Limits
    max_balance: Optional[float] = None  # Max hours that can accumulate
    max_carryover: Optional[float] = None  # Max hours carried to next year
    
    # Waiting period
    waiting_period_days: int = 0  # Days before staff can use
    
    # Request rules
    min_request_hours: float = 1.0
    max_request_days: Optional[int] = None
    advance_notice_days: int = 0
    
    # Approval
    requires_approval: bool = True
    auto_approve_under_hours: Optional[float] = None
    
    is_paid: bool = True
    is_active: bool = True
    description: Optional[str] = None


class TimeOffPolicyCreate(BaseModel):
    name: str
    time_off_type: TimeOffType
    location_id: Optional[str] = None
    accrual_rate: float = 0.0
    accrual_frequency: AccrualFrequency = AccrualFrequency.PER_PAY_PERIOD
    max_balance: Optional[float] = None
    max_carryover: Optional[float] = None
    waiting_period_days: int = 0
    min_request_hours: float = 1.0
    max_request_days: Optional[int] = None
    advance_notice_days: int = 0
    requires_approval: bool = True
    auto_approve_under_hours: Optional[float] = None
    is_paid: bool = True
    is_active: bool = True
    description: Optional[str] = None


class TimeOffPolicyResponse(BaseDBModel):
    name: str
    time_off_type: TimeOffType
    location_id: Optional[str] = None
    accrual_rate: float
    accrual_frequency: AccrualFrequency
    max_balance: Optional[float] = None
    max_carryover: Optional[float] = None
    waiting_period_days: int
    min_request_hours: float
    max_request_days: Optional[int] = None
    advance_notice_days: int
    requires_approval: bool
    auto_approve_under_hours: Optional[float] = None
    is_paid: bool
    is_active: bool
    description: Optional[str] = None


class TimeOffRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TimeOffRequest(BaseDBModel):
    """Staff time off request"""
    staff_id: str
    staff_name: str
    policy_id: str
    time_off_type: TimeOffType
    
    # Request details
    start_date: datetime
    end_date: datetime
    hours_requested: float
    
    reason: Optional[str] = None
    
    # Status
    status: TimeOffRequestStatus = TimeOffRequestStatus.PENDING
    
    # Approval
    reviewed_by: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    # Balance snapshot at time of request
    balance_before: float = 0.0
    balance_after: float = 0.0


class TimeOffRequestCreate(BaseModel):
    policy_id: str
    start_date: datetime
    end_date: datetime
    hours_requested: float
    reason: Optional[str] = None


class TimeOffRequestResponse(BaseDBModel):
    staff_id: str
    staff_name: str
    policy_id: str
    time_off_type: TimeOffType
    start_date: datetime
    end_date: datetime
    hours_requested: float
    reason: Optional[str] = None
    status: TimeOffRequestStatus
    reviewed_by: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    balance_before: float
    balance_after: float


class TimeOffBalance(BaseDBModel):
    """Staff time off balance per policy"""
    staff_id: str
    policy_id: str
    time_off_type: TimeOffType
    
    # Current balance
    balance_hours: float = 0.0
    
    # Tracking
    accrued_ytd: float = 0.0  # Year to date accrued
    used_ytd: float = 0.0  # Year to date used
    pending_hours: float = 0.0  # In pending requests
    
    # Last updated
    last_accrual_date: Optional[datetime] = None
    
    # Carryover from previous year
    carryover_hours: float = 0.0


class TimeOffBalanceResponse(BaseDBModel):
    staff_id: str
    policy_id: str
    time_off_type: TimeOffType
    balance_hours: float
    accrued_ytd: float
    used_ytd: float
    pending_hours: float
    last_accrual_date: Optional[datetime] = None
    carryover_hours: float


# ==================== TRAINING & KNOWLEDGE ====================

class CourseStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Course(BaseDBModel):
    """Training course/module"""
    title: str
    description: Optional[str] = None
    location_id: Optional[str] = None  # None = all locations
    
    # Content
    content_type: str = "document"  # document, video, mixed
    content_url: Optional[str] = None
    content_html: Optional[str] = None
    video_url: Optional[str] = None
    
    # Structure
    sections: List[Dict[str, Any]] = []  # [{"title": "x", "content": "...", "video_url": null}]
    
    # Quiz
    has_quiz: bool = False
    quiz_id: Optional[str] = None
    passing_score: Optional[int] = None  # Percentage
    
    # Assignment
    required_for_roles: List[str] = []  # Roles that must complete
    required_for_new_staff: bool = False
    due_days_after_start: Optional[int] = None  # Days after employment start
    
    # Deadline
    due_date: Optional[datetime] = None  # Global deadline
    
    # Status
    status: CourseStatus = CourseStatus.DRAFT
    
    # Metadata
    duration_minutes: Optional[int] = None
    category: Optional[str] = None
    tags: List[str] = []
    
    # Versioning
    version: int = 1


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    location_id: Optional[str] = None
    content_type: str = "document"
    content_url: Optional[str] = None
    content_html: Optional[str] = None
    video_url: Optional[str] = None
    sections: List[Dict[str, Any]] = []
    has_quiz: bool = False
    quiz_id: Optional[str] = None
    passing_score: Optional[int] = None
    required_for_roles: List[str] = []
    required_for_new_staff: bool = False
    due_days_after_start: Optional[int] = None
    due_date: Optional[datetime] = None
    status: CourseStatus = CourseStatus.DRAFT
    duration_minutes: Optional[int] = None
    category: Optional[str] = None
    tags: List[str] = []


class CourseResponse(BaseDBModel):
    title: str
    description: Optional[str] = None
    location_id: Optional[str] = None
    content_type: str
    content_url: Optional[str] = None
    video_url: Optional[str] = None
    sections: List[Dict[str, Any]]
    has_quiz: bool
    quiz_id: Optional[str] = None
    passing_score: Optional[int] = None
    required_for_roles: List[str]
    required_for_new_staff: bool
    due_days_after_start: Optional[int] = None
    due_date: Optional[datetime] = None
    status: CourseStatus
    duration_minutes: Optional[int] = None
    category: Optional[str] = None
    tags: List[str]
    version: int


class Quiz(BaseDBModel):
    """Quiz for training assessment"""
    title: str
    description: Optional[str] = None
    course_id: Optional[str] = None
    
    # Questions
    questions: List[Dict[str, Any]] = []  # [{"text": "?", "type": "multiple_choice", "options": [], "correct_answer": "x"}]
    
    # Settings
    passing_score: int = 70  # Percentage
    max_attempts: Optional[int] = None
    time_limit_minutes: Optional[int] = None
    shuffle_questions: bool = False
    show_correct_answers: bool = True
    
    is_active: bool = True


class QuizCreate(BaseModel):
    title: str
    description: Optional[str] = None
    course_id: Optional[str] = None
    questions: List[Dict[str, Any]] = []
    passing_score: int = 70
    max_attempts: Optional[int] = None
    time_limit_minutes: Optional[int] = None
    shuffle_questions: bool = False
    show_correct_answers: bool = True
    is_active: bool = True


class QuizResponse(BaseDBModel):
    title: str
    description: Optional[str] = None
    course_id: Optional[str] = None
    questions: List[Dict[str, Any]]
    passing_score: int
    max_attempts: Optional[int] = None
    time_limit_minutes: Optional[int] = None
    shuffle_questions: bool
    show_correct_answers: bool
    is_active: bool


class QuizAttempt(BaseDBModel):
    """Staff quiz attempt"""
    quiz_id: str
    staff_id: str
    staff_name: str
    
    # Answers
    answers: Dict[str, Any] = {}  # question_id -> answer
    
    # Results
    score: float = 0.0
    passed: bool = False
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    time_taken_seconds: Optional[int] = None
    
    attempt_number: int = 1


class CourseProgress(BaseDBModel):
    """Staff progress on a course"""
    course_id: str
    staff_id: str
    staff_name: str
    
    # Progress
    status: str = "not_started"  # not_started, in_progress, completed
    progress_percentage: float = 0.0
    sections_completed: List[str] = []
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Quiz
    quiz_passed: bool = False
    quiz_attempts: int = 0
    best_quiz_score: Optional[float] = None
    
    # Due date for this staff member
    due_date: Optional[datetime] = None
    overdue: bool = False


class KnowledgeArticle(BaseDBModel):
    """Knowledge base article"""
    title: str
    content: str  # HTML or Markdown
    location_id: Optional[str] = None  # None = all locations
    
    # Organization
    category: Optional[str] = None
    tags: List[str] = []
    
    # Access
    visible_to_roles: List[str] = []  # Empty = all
    
    # Versioning
    version: int = 1
    revision_history: List[Dict[str, Any]] = []  # [{"version": 1, "updated_by": "x", "updated_at": "..."}]
    
    # Status
    status: str = "published"  # draft, published, archived
    
    # Search
    search_keywords: List[str] = []
    
    # Attachments
    attachments: List[Dict[str, str]] = []  # [{"name": "x", "url": "..."}]
    
    # Metadata
    author_id: str
    author_name: str
    last_updated_by: Optional[str] = None


class KnowledgeArticleCreate(BaseModel):
    title: str
    content: str
    location_id: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    visible_to_roles: List[str] = []
    status: str = "published"
    search_keywords: List[str] = []
    attachments: List[Dict[str, str]] = []


class KnowledgeArticleResponse(BaseDBModel):
    title: str
    content: str
    location_id: Optional[str] = None
    category: Optional[str] = None
    tags: List[str]
    visible_to_roles: List[str]
    version: int
    status: str
    author_id: str
    author_name: str
    attachments: List[Dict[str, str]]


# ==================== ANNOUNCEMENTS ====================

class AnnouncementPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Announcement(BaseDBModel):
    """Company announcements and updates"""
    title: str
    content: str  # HTML or Markdown
    
    # Author
    author_id: str
    author_name: str
    
    # Targeting
    location_id: Optional[str] = None  # None = all locations
    target_roles: List[str] = []  # Empty = all
    target_teams: List[str] = []  # Empty = all
    target_staff_ids: List[str] = []  # Specific users
    
    # Priority & pinning
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    is_pinned: bool = False
    
    # Acknowledgement
    requires_acknowledgement: bool = False
    acknowledgement_deadline: Optional[datetime] = None
    
    # Scheduling
    publish_at: Optional[datetime] = None  # Scheduled publish
    expires_at: Optional[datetime] = None
    
    # Status
    status: str = "draft"  # draft, published, archived
    published_at: Optional[datetime] = None
    
    # Attachments
    attachments: List[Dict[str, str]] = []
    
    # Tracking
    view_count: int = 0
    acknowledgement_count: int = 0


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    location_id: Optional[str] = None
    target_roles: List[str] = []
    target_teams: List[str] = []
    target_staff_ids: List[str] = []
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    is_pinned: bool = False
    requires_acknowledgement: bool = False
    acknowledgement_deadline: Optional[datetime] = None
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: str = "draft"
    attachments: List[Dict[str, str]] = []


class AnnouncementResponse(BaseDBModel):
    title: str
    content: str
    author_id: str
    author_name: str
    location_id: Optional[str] = None
    target_roles: List[str]
    target_teams: List[str]
    target_staff_ids: List[str]
    priority: AnnouncementPriority
    is_pinned: bool
    requires_acknowledgement: bool
    acknowledgement_deadline: Optional[datetime] = None
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: str
    published_at: Optional[datetime] = None
    attachments: List[Dict[str, str]]
    view_count: int
    acknowledgement_count: int


class Acknowledgement(BaseDBModel):
    """Staff acknowledgement of announcement"""
    announcement_id: str
    staff_id: str
    staff_name: str
    
    acknowledged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Optional confirmation text
    confirmation_text: Optional[str] = None  # "I have read and understood..."


# ==================== KIOSK MODE ====================

class KioskDevice(BaseDBModel):
    """Registered kiosk device for shared clock in/out"""
    name: str
    location_id: str
    device_code: str  # Unique code to identify the kiosk
    is_active: bool = True
    last_activity: Optional[datetime] = None
    settings: Dict[str, Any] = {}  # Kiosk-specific settings


class KioskDeviceCreate(BaseModel):
    name: str
    location_id: str


class KioskDeviceResponse(BaseDBModel):
    name: str
    location_id: str
    device_code: str
    is_active: bool
    last_activity: Optional[datetime] = None


class StaffKioskPin(BaseDBModel):
    """Staff PIN for kiosk clock in/out"""
    staff_id: str
    pin_hash: str  # Hashed 4-6 digit PIN
    is_active: bool = True
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None


class KioskClockRequest(BaseModel):
    """Request for kiosk clock in/out"""
    device_code: str
    staff_pin: str
    action: str  # clock_in, clock_out, break_start, break_end
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# ==================== SHIFT SCHEDULING EXTENSIONS ====================

class ShiftStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RecurrencePattern(str, Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class ScheduledShift(BaseDBModel):
    """Individual scheduled shift"""
    template_id: Optional[str] = None
    staff_id: str
    staff_name: str
    location_id: str
    
    # Timing
    start_time: datetime
    end_time: datetime
    
    # Recurrence
    recurrence_pattern: RecurrencePattern = RecurrencePattern.NONE
    recurrence_end_date: Optional[datetime] = None
    parent_shift_id: Optional[str] = None  # For recurring instances
    
    # Status
    status: ShiftStatus = ShiftStatus.PUBLISHED
    
    # Actual timing (filled when staff clocks in/out)
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    time_entry_id: Optional[str] = None
    
    # Attachments
    task_ids: List[str] = []
    notes: Optional[str] = None
    color: Optional[str] = "#3B82F6"  # Default blue
    
    # Publishing
    published_at: Optional[datetime] = None
    published_by: Optional[str] = None


class ScheduledShiftCreate(BaseModel):
    template_id: Optional[str] = None
    staff_id: str
    location_id: str
    start_time: datetime
    end_time: datetime
    recurrence_pattern: RecurrencePattern = RecurrencePattern.NONE
    recurrence_end_date: Optional[datetime] = None
    task_ids: List[str] = []
    notes: Optional[str] = None
    color: Optional[str] = "#3B82F6"
    status: ShiftStatus = ShiftStatus.DRAFT


class ScheduledShiftResponse(BaseDBModel):
    template_id: Optional[str] = None
    staff_id: str
    staff_name: str
    location_id: str
    start_time: datetime
    end_time: datetime
    recurrence_pattern: RecurrencePattern
    recurrence_end_date: Optional[datetime] = None
    status: ShiftStatus
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    time_entry_id: Optional[str] = None
    task_ids: List[str]
    notes: Optional[str] = None
    color: Optional[str] = None
    published_at: Optional[datetime] = None


class PlannedVsActualReport(BaseModel):
    """Report comparing scheduled vs actual hours"""
    staff_id: str
    staff_name: str
    period_start: datetime
    period_end: datetime
    
    # Planned (from shifts)
    planned_shifts: int = 0
    planned_hours: float = 0.0
    
    # Actual (from time entries)
    actual_entries: int = 0
    actual_hours: float = 0.0
    
    # Variance
    hours_variance: float = 0.0  # Actual - Planned
    variance_percentage: float = 0.0
    
    # Details
    missed_shifts: int = 0
    late_arrivals: int = 0
    early_departures: int = 0
    unscheduled_entries: int = 0



# ==================== MOEGO PARITY - PHASE 1 ====================
# Slot-based booking, kennels/runs, coupon codes, card-on-file

# ==================== KENNELS / RUNS ====================

class KennelType(str, Enum):
    RUN = "run"  # Large outdoor/indoor run
    SUITE = "suite"  # Premium private room
    CRATE = "crate"  # Standard crate
    LUXURY = "luxury"  # Luxury suite with extras


class KennelStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    CLEANING = "cleaning"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"


class Kennel(BaseDBModel):
    """Individual kennel/run/suite unit"""
    name: str  # e.g., "Run A1", "Suite 3", "Crate 12"
    location_id: str
    kennel_type: KennelType
    
    # Physical attributes
    size_category: str = "medium"  # small, medium, large, xlarge
    max_dogs: int = 1  # Max dogs that can share (family groups)
    square_feet: Optional[float] = None
    
    # Features
    features: List[str] = []  # ["outdoor_access", "webcam", "climate_control", "raised_bed"]
    
    # Pricing
    price_modifier: float = 0.0  # Added to base price (e.g., +$10 for suite)
    
    # Compatibility
    suitable_for_breeds: List[str] = []  # Empty = all breeds
    min_weight: Optional[float] = None
    max_weight: Optional[float] = None
    
    # Status
    status: KennelStatus = KennelStatus.AVAILABLE
    current_booking_id: Optional[str] = None
    current_dog_ids: List[str] = []
    
    # Display
    sort_order: int = 0
    color: Optional[str] = None  # For calendar/map display
    notes: Optional[str] = None
    is_active: bool = True


class KennelCreate(BaseModel):
    name: str
    location_id: str
    kennel_type: KennelType
    size_category: str = "medium"
    max_dogs: int = 1
    square_feet: Optional[float] = None
    features: List[str] = []
    price_modifier: float = 0.0
    suitable_for_breeds: List[str] = []
    min_weight: Optional[float] = None
    max_weight: Optional[float] = None
    sort_order: int = 0
    color: Optional[str] = None
    notes: Optional[str] = None


class KennelResponse(BaseDBModel):
    name: str
    location_id: str
    kennel_type: KennelType
    size_category: str
    max_dogs: int
    square_feet: Optional[float] = None
    features: List[str]
    price_modifier: float
    suitable_for_breeds: List[str]
    min_weight: Optional[float] = None
    max_weight: Optional[float] = None
    status: KennelStatus
    current_booking_id: Optional[str] = None
    current_dog_ids: List[str]
    sort_order: int
    color: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool


# ==================== TIME SLOTS ====================

class SlotType(str, Enum):
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    DAYCARE_DROP_OFF = "daycare_drop_off"
    DAYCARE_PICK_UP = "daycare_pick_up"
    BATH = "bath"
    APPOINTMENT = "appointment"


class TimeSlot(BaseDBModel):
    """Configurable time slot for bookings"""
    location_id: str
    slot_type: SlotType
    
    # Time configuration
    start_time: str  # "08:00" format (24h)
    end_time: str  # "09:00" format
    
    # Days of week (0=Monday, 6=Sunday)
    days_of_week: List[int] = [0, 1, 2, 3, 4, 5, 6]
    
    # Capacity
    max_bookings: int = 5  # Max bookings in this slot
    buffer_minutes: int = 0  # Buffer between slots
    
    # Service type restrictions
    service_type_ids: List[str] = []  # Empty = all services
    
    # Date range (for seasonal slots)
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    
    is_active: bool = True
    notes: Optional[str] = None


class TimeSlotCreate(BaseModel):
    location_id: str
    slot_type: SlotType
    start_time: str
    end_time: str
    days_of_week: List[int] = [0, 1, 2, 3, 4, 5, 6]
    max_bookings: int = 5
    buffer_minutes: int = 0
    service_type_ids: List[str] = []
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None


class TimeSlotResponse(BaseDBModel):
    location_id: str
    slot_type: SlotType
    start_time: str
    end_time: str
    days_of_week: List[int]
    max_bookings: int
    buffer_minutes: int
    service_type_ids: List[str]
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    is_active: bool
    notes: Optional[str] = None


class SlotAvailability(BaseModel):
    """Real-time slot availability"""
    slot_id: str
    slot_type: SlotType
    date: datetime
    start_time: str
    end_time: str
    max_bookings: int
    current_bookings: int
    available_spots: int
    status: str  # "available", "limited", "full", "closed"
    booking_ids: List[str] = []


# ==================== COUPON / DISCOUNT CODES ====================

class DiscountType(str, Enum):
    PERCENTAGE = "percentage"  # % off total
    FLAT_AMOUNT = "flat_amount"  # $ off total
    FREE_ADDON = "free_addon"  # Free add-on service
    FREE_NIGHT = "free_night"  # Free night (buy X get 1)


class CouponCode(BaseDBModel):
    """Coupon/discount code"""
    code: str  # The actual code customers enter
    name: str  # Internal name
    description: Optional[str] = None
    
    # Discount configuration
    discount_type: DiscountType
    discount_value: float  # Amount or percentage
    free_addon_id: Optional[str] = None  # For FREE_ADDON type
    buy_nights_get_free: Optional[int] = None  # For FREE_NIGHT type
    
    # Limits
    max_uses: Optional[int] = None  # Total uses allowed
    max_uses_per_customer: int = 1
    current_uses: int = 0
    
    # Minimum requirements
    min_order_amount: Optional[float] = None
    min_nights: Optional[int] = None
    min_dogs: Optional[int] = None
    
    # Restrictions
    service_type_ids: List[str] = []  # Empty = all services
    location_ids: List[str] = []  # Empty = all locations
    first_booking_only: bool = False
    
    # Validity
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    
    is_active: bool = True
    created_by: Optional[str] = None


class CouponCodeCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    discount_type: DiscountType
    discount_value: float
    free_addon_id: Optional[str] = None
    buy_nights_get_free: Optional[int] = None
    max_uses: Optional[int] = None
    max_uses_per_customer: int = 1
    min_order_amount: Optional[float] = None
    min_nights: Optional[int] = None
    min_dogs: Optional[int] = None
    service_type_ids: List[str] = []
    location_ids: List[str] = []
    first_booking_only: bool = False
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class CouponCodeResponse(BaseDBModel):
    code: str
    name: str
    description: Optional[str] = None
    discount_type: DiscountType
    discount_value: float
    free_addon_id: Optional[str] = None
    buy_nights_get_free: Optional[int] = None
    max_uses: Optional[int] = None
    max_uses_per_customer: int
    current_uses: int
    min_order_amount: Optional[float] = None
    min_nights: Optional[int] = None
    service_type_ids: List[str]
    location_ids: List[str]
    first_booking_only: bool
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool


class CouponUsage(BaseDBModel):
    """Track coupon usage per customer"""
    coupon_id: str
    coupon_code: str
    booking_id: str
    household_id: str
    discount_applied: float
    used_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== CARD ON FILE (SQUARE VAULT) ====================

class PaymentMethodType(str, Enum):
    CARD = "card"
    BANK_ACCOUNT = "bank_account"


class CardBrand(str, Enum):
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    AMERICAN_EXPRESS = "AMERICAN_EXPRESS"
    DISCOVER = "DISCOVER"
    DISCOVER_DINERS = "DISCOVER_DINERS"
    JCB = "JCB"
    CHINA_UNIONPAY = "CHINA_UNIONPAY"
    SQUARE_GIFT_CARD = "SQUARE_GIFT_CARD"
    OTHER = "OTHER"


class StoredPaymentMethod(BaseDBModel):
    """Card on file / stored payment method"""
    household_id: str
    customer_id: str  # Square customer ID
    
    # Square references
    card_id: str  # Square card ID
    
    # Card details (masked)
    payment_method_type: PaymentMethodType = PaymentMethodType.CARD
    card_brand: Optional[CardBrand] = None
    last_4: str
    exp_month: int
    exp_year: int
    cardholder_name: Optional[str] = None
    
    # Billing address (optional)
    billing_zip: Optional[str] = None
    billing_country: Optional[str] = None
    
    # Status
    is_default: bool = False
    is_active: bool = True
    
    # Verification
    verified: bool = False
    verified_at: Optional[datetime] = None
    
    # Last used
    last_used_at: Optional[datetime] = None


class StoredPaymentMethodResponse(BaseModel):
    id: str
    household_id: str
    payment_method_type: PaymentMethodType
    card_brand: Optional[CardBrand] = None
    last_4: str
    exp_month: int
    exp_year: int
    cardholder_name: Optional[str] = None
    billing_zip: Optional[str] = None
    is_default: bool
    is_active: bool
    verified: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime


# ==================== ELIGIBILITY RULES ====================

class EligibilityRuleType(str, Enum):
    VACCINATION = "vaccination"
    WEIGHT = "weight"
    BREED = "breed"
    AGE = "age"
    BEHAVIOR = "behavior"
    SPAY_NEUTER = "spay_neuter"


class EligibilityRule(BaseDBModel):
    """Rules for service/booking eligibility"""
    name: str
    rule_type: EligibilityRuleType
    location_id: Optional[str] = None  # None = all locations
    service_type_ids: List[str] = []  # Empty = all services
    
    # Rule configuration (depends on type)
    # VACCINATION: required vaccines list
    required_vaccines: List[str] = []  # ["rabies", "bordetella", "dhpp"]
    vaccine_expiry_buffer_days: int = 0  # Days before expiry to flag
    
    # WEIGHT: min/max
    min_weight: Optional[float] = None
    max_weight: Optional[float] = None
    
    # BREED: allowed/blocked
    allowed_breeds: List[str] = []  # Empty = all allowed
    blocked_breeds: List[str] = []
    
    # AGE: min/max months
    min_age_months: Optional[int] = None
    max_age_months: Optional[int] = None
    
    # BEHAVIOR: required flags
    requires_dog_friendly: bool = False
    blocks_aggressive: bool = True
    
    # SPAY_NEUTER: required
    requires_spay_neuter: bool = False
    min_age_for_spay_neuter: int = 6  # Months
    
    # Enforcement
    is_hard_block: bool = True  # If false, allows with warning
    warning_message: Optional[str] = None
    block_message: Optional[str] = None
    
    is_active: bool = True


class EligibilityRuleCreate(BaseModel):
    name: str
    rule_type: EligibilityRuleType
    location_id: Optional[str] = None
    service_type_ids: List[str] = []
    required_vaccines: List[str] = []
    vaccine_expiry_buffer_days: int = 0
    min_weight: Optional[float] = None
    max_weight: Optional[float] = None
    allowed_breeds: List[str] = []
    blocked_breeds: List[str] = []
    min_age_months: Optional[int] = None
    max_age_months: Optional[int] = None
    requires_dog_friendly: bool = False
    blocks_aggressive: bool = True
    requires_spay_neuter: bool = False
    is_hard_block: bool = True
    warning_message: Optional[str] = None
    block_message: Optional[str] = None


class EligibilityRuleResponse(BaseDBModel):
    name: str
    rule_type: EligibilityRuleType
    location_id: Optional[str] = None
    service_type_ids: List[str]
    required_vaccines: List[str]
    min_weight: Optional[float] = None
    max_weight: Optional[float] = None
    allowed_breeds: List[str]
    blocked_breeds: List[str]
    min_age_months: Optional[int] = None
    max_age_months: Optional[int] = None
    is_hard_block: bool
    warning_message: Optional[str] = None
    block_message: Optional[str] = None
    is_active: bool


class EligibilityCheckResult(BaseModel):
    """Result of checking dog eligibility"""
    dog_id: str
    dog_name: str
    is_eligible: bool
    has_warnings: bool
    errors: List[Dict[str, Any]] = []  # Hard blocks
    warnings: List[Dict[str, Any]] = []  # Soft warnings
    missing_vaccines: List[str] = []
    expiring_vaccines: List[Dict[str, Any]] = []


# ==================== BOOKING ENHANCEMENTS ====================

class BookingSlot(BaseModel):
    """Slot assignment for a booking"""
    slot_id: str
    slot_type: SlotType
    date: datetime
    time: str  # "08:00" format


class BookingEnhanced(Booking):
    """Enhanced booking with MoeGo features"""
    # Kennel assignment
    kennel_id: Optional[str] = None
    kennel_name: Optional[str] = None
    kennel_type: Optional[KennelType] = None
    
    # Slot assignments
    check_in_slot: Optional[BookingSlot] = None
    check_out_slot: Optional[BookingSlot] = None
    
    # Coupon/discount
    coupon_code: Optional[str] = None
    coupon_id: Optional[str] = None
    coupon_discount: float = 0.0
    
    # Card on file
    stored_payment_method_id: Optional[str] = None
    pre_auth_amount: Optional[float] = None
    pre_auth_id: Optional[str] = None
    
    # Bath add-on (simplified from grooming)
    bath_requested: bool = False
    bath_date: Optional[datetime] = None  # Date for bath (usually day before checkout)
    bath_notes: Optional[str] = None
    bath_completed: bool = False
    bath_completed_by: Optional[str] = None
    bath_completed_at: Optional[datetime] = None
    
    # Eligibility
    eligibility_checked: bool = False
    eligibility_warnings: List[str] = []
    eligibility_overridden: bool = False
    eligibility_override_by: Optional[str] = None
    eligibility_override_reason: Optional[str] = None


# ==================== WAITLIST ====================

class WaitlistStatus(str, Enum):
    WAITING = "waiting"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WaitlistEntry(BaseDBModel):
    """Waitlist entry for full dates"""
    household_id: str
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    
    dog_ids: List[str]
    location_id: str
    service_type_id: str
    
    # Requested dates
    requested_check_in: datetime
    requested_check_out: datetime
    flexible_dates: bool = False
    date_flexibility_days: int = 0
    
    # Preferences
    preferred_kennel_type: Optional[KennelType] = None
    notes: Optional[str] = None
    
    # Status
    status: WaitlistStatus = WaitlistStatus.WAITING
    position: int = 0
    
    # Offer tracking
    offered_at: Optional[datetime] = None
    offer_expires_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    converted_booking_id: Optional[str] = None


class WaitlistEntryCreate(BaseModel):
    dog_ids: List[str]
    location_id: str
    service_type_id: str
    requested_check_in: datetime
    requested_check_out: datetime
    flexible_dates: bool = False
    date_flexibility_days: int = 0
    preferred_kennel_type: Optional[KennelType] = None
    notes: Optional[str] = None


class WaitlistEntryResponse(BaseDBModel):
    household_id: str
    customer_name: str
    dog_ids: List[str]
    location_id: str
    service_type_id: str
    requested_check_in: datetime
    requested_check_out: datetime
    flexible_dates: bool
    preferred_kennel_type: Optional[KennelType] = None
    status: WaitlistStatus
    position: int
    offered_at: Optional[datetime] = None
    offer_expires_at: Optional[datetime] = None


# ==================== DAILY OPERATIONS VIEW ====================

class DogOnSite(BaseModel):
    """Dog currently on site"""
    dog_id: str
    dog_name: str
    breed: str
    weight: Optional[float] = None
    photo_url: Optional[str] = None
    
    booking_id: str
    household_id: str
    customer_name: str
    customer_phone: Optional[str] = None
    
    kennel_id: Optional[str] = None
    kennel_name: Optional[str] = None
    
    check_in_date: datetime
    check_out_date: datetime
    nights_remaining: int
    
    # Status flags
    needs_medication: bool = False
    medication_notes: Optional[str] = None
    special_diet: bool = False
    diet_notes: Optional[str] = None
    behavioral_flags: List[str] = []
    
    # Today's activities
    bath_scheduled: bool = False
    bath_completed: bool = False
    tasks_pending: int = 0
    last_update_sent: Optional[datetime] = None


class DailyOperationsSummary(BaseModel):
    """Daily operations dashboard data"""
    date: datetime
    location_id: str
    
    # Occupancy
    total_kennels: int
    occupied_kennels: int
    available_kennels: int
    occupancy_rate: float
    
    # Today's movements
    check_ins_scheduled: int
    check_ins_completed: int
    check_outs_scheduled: int
    check_outs_completed: int
    
    # Dogs on site
    dogs_on_site: int
    dogs_needing_medication: int
    dogs_with_special_diet: int
    
    # Baths
    baths_scheduled: int
    baths_completed: int
    
    # Alerts
    vaccines_expiring_soon: int
    overdue_checkouts: int
    pending_payments: int


# ==================== PET PARENT PORTAL ENHANCEMENTS ====================

class ServiceHistoryEntry(BaseModel):
    """Entry in pet's service history"""
    booking_id: str
    service_type: str
    service_name: str
    location_name: str
    
    check_in_date: datetime
    check_out_date: datetime
    nights: int
    
    kennel_name: Optional[str] = None
    add_ons: List[str] = []
    bath_included: bool = False
    
    total_paid: float
    
    # For rebooking
    can_rebook: bool = True
    rebook_data: Optional[Dict[str, Any]] = None


class CustomerPortalData(BaseModel):
    """Aggregated data for customer portal"""
    household_id: str
    customer_name: str
    
    # Dogs
    dogs: List[Dict[str, Any]] = []
    dogs_with_expiring_vaccines: List[Dict[str, Any]] = []
    
    # Bookings
    upcoming_bookings: List[Dict[str, Any]] = []
    past_bookings: List[ServiceHistoryEntry] = []
    
    # Payments
    stored_payment_methods: List[StoredPaymentMethodResponse] = []
    outstanding_balance: float = 0.0
    
    # Preferences
    preferred_kennel_type: Optional[str] = None
    preferred_add_ons: List[str] = []
    communication_preferences: Dict[str, bool] = {}
    
    # Stats
    total_stays: int = 0
    total_nights: int = 0
    member_since: Optional[datetime] = None
    loyalty_status: Optional[str] = None
