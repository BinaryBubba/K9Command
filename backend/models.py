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
    payment_type: Optional[str] = "invoice"
    customer_id: Optional[str] = None
    accommodation_type: Optional[str] = None
    is_holiday_pricing: Optional[bool] = False
    needs_separate_playtime: Optional[bool] = False
    separate_playtime_fee: Optional[float] = 0.0

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
    price_type: PriceType
    category: str
    requires_staff_assignment: bool
    max_quantity: int
    active: bool
    location_id: Optional[str] = None
    service_type_ids: List[str] = []
    sort_order: int


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
    buffer_capacity: int
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    active: bool


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
    multiplier: float
    flat_adjustment: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    recurring_yearly: bool
    days_of_week: List[int]
    service_type_ids: List[str]
    location_id: Optional[str] = None
    priority: int
    active: bool
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
    refund_deposit_only: bool
    applies_to_deposit: bool
    applies_to_balance: bool
    service_type_ids: List[str]
    location_id: Optional[str] = None
    active: bool
    is_default: bool
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
