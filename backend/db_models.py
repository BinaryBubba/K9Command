"""
SQLAlchemy ORM Models for PostgreSQL
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Date, Text, ForeignKey, Enum, JSON, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
import uuid
from datetime import datetime, timezone


def generate_uuid():
    return str(uuid.uuid4())


# ==================== ENUMS ====================

class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    STAFF = "staff"
    MANAGER = "manager"
    ADMIN = "admin"


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


class TaskStatusLegacy(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class UpdateStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    PAYMENT = "payment"
    INCIDENT = "incident"


class TimeModificationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccommodationType(str, enum.Enum):
    ROOM = "room"
    CRATE = "crate"


class ChatType(str, enum.Enum):
    ADMIN_STAFF = "admin_staff"
    KENNEL_CUSTOMER = "kennel_customer"


# ==================== MODELS ====================

class User(Base):
    __tablename__ = "users"
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(Enum(UserRole), nullable=False)
    location_id = Column(String, ForeignKey("locations.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_owner = Column(Boolean, nullable=False, server_default=text("false"), default=False)
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    hire_date = Column(String, nullable=True)
    manager_pin = Column(String(4), nullable=True)
    connecteam_user_id = Column(String, nullable=True)
    is_on_shift = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    shift_started_at = Column(DateTime(timezone=True), nullable=True)
    address = Column(String, nullable=True)
    birthday = Column(String, nullable=True)
    avatar_key = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    household_id = Column(String, nullable=True, index=True)  # NOT unique: a household can have >1 portal account
    reset_token = Column(String, nullable=True)
    reset_token_expiry = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    email_verified = Column(Boolean, default=False)

    # Relationships
    # dogs relationship removed - dogs now linked via Household not User
    bookings_created = relationship("Booking", back_populates="creator", foreign_keys="Booking.created_by")
    time_entries = relationship("TimeEntry", back_populates="staff")
    shifts = relationship("Shift", back_populates="staff")


class Location(Base):
    __tablename__ = "locations"
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    contact_email = Column(String, nullable=False)
    contact_phone = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Dog(Base):
    __tablename__ = "dogs"
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    household_id_new = None  # placeholder - household_id already exists
    veterinarian_id = Column(String, ForeignKey("veterinarians.id"), nullable=True)
    spay_neuter_status = Column(String, nullable=True)
    microchip_number = Column(String, nullable=True)
    meet_and_greet_status = Column(String, nullable=True, default="required")
    meet_and_greet_outcome = Column(String, nullable=True)
    boarding_eligible = Column(Boolean, default=False)
    daycare_eligible = Column(Boolean, default=False)
    is_deceased = Column(Boolean, default=False)
    escape_risk = Column(Boolean, default=False)
    medical_alert = Column(Boolean, default=False)

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    breed = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    household_id = Column(String, ForeignKey("households.id"), nullable=False, index=True)
    photo_url = Column(Text, nullable=True)
    vaccination_file_url = Column(Text, nullable=True)
    behavioral_notes = Column(Text, nullable=True)
    medical_flags = Column(JSON, default=list)  # List of strings
    internal_notes = Column(Text, nullable=True)  # Staff only
    gender = Column(String, nullable=True)
    color = Column(String, nullable=True)
    birthday = Column(DateTime(timezone=True), nullable=True)
    meal_routine = Column(Text, nullable=True)
    medication_requirements = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    friendly_to_cats = Column(Boolean, nullable=True)
    friendly_with_dogs = Column(Boolean, nullable=True)
    seizure_activity = Column(Boolean, nullable=True)
    afraid_of_thunder = Column(Boolean, nullable=True)
    afraid_of_fireworks = Column(Boolean, nullable=True)
    resource_guarding = Column(Boolean, nullable=True)
    fence_aggression = Column(Boolean, nullable=True)
    incidents_of_aggression = Column(Text, nullable=True)
    other_notes = Column(Text, nullable=True)
    vaccinations = Column(JSON, default=list)  # List of vaccination records
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    household = relationship("Household", foreign_keys=[household_id])


class BookingDogLegacy(Base):
    """Legacy association table - superseded by booking_dogs_v2"""
    __tablename__ = "booking_dogs"

    booking_id = Column(String, ForeignKey("bookings.id"), primary_key=True)
    dog_id = Column(String, ForeignKey("dogs.id"), primary_key=True)


class Booking(Base):
    __tablename__ = "bookings"
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)

    id = Column(String, primary_key=True, default=generate_uuid)
    household_id = Column(String, nullable=False, index=True)
    location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    accommodation_type = Column(Enum(AccommodationType), default=AccommodationType.ROOM)
    check_in_date = Column(DateTime(timezone=True), nullable=False)
    check_out_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    total_price = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    special_request = Column(Text, nullable=True)
    payment_status = Column(String, default="pending")
    payment_intent_id = Column(String, nullable=True)
    payment_type = Column(String, default="invoice")  # 'immediate' or 'invoice'
    is_holiday_pricing = Column(Boolean, default=False)
    needs_separate_playtime = Column(Boolean, default=False)
    separate_playtime_fee = Column(Float, default=0.0)
    items_checklist = Column(JSON, nullable=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    checked_out_at = Column(DateTime(timezone=True), nullable=True)
    customer_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    modification_reason = Column(Text, nullable=True)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    dog_ids = Column(JSON, default=list)  # Store dog IDs as JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", back_populates="bookings_created", foreign_keys=[created_by])


class DailyUpdate(Base):
    __tablename__ = "daily_updates"

    id = Column(String, primary_key=True, default=generate_uuid)
    household_id = Column(String, nullable=False, index=True)
    booking_id = Column(String, ForeignKey("bookings.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    media_items = Column(JSON, default=list)
    staff_snippets = Column(JSON, default=list)
    ai_summary = Column(Text, nullable=True)
    status = Column(Enum(UpdateStatus), default=UpdateStatus.DRAFT)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    reactions = Column(JSON, default=list)
    comments = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TaskLegacy(Base):
    __tablename__ = "tasks"
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)
    location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(TaskStatusLegacy), default=TaskStatusLegacy.PENDING)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(String, ForeignKey("users.id"), nullable=True)
    completed_by_name = Column(String, nullable=True)
    checklist_items = Column(JSON, default=list)

    # === Forms integration ===
    form_template_id = Column(String, ForeignKey("form_templates.id"), nullable=True)
    require_form_completion = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(String, primary_key=True, default=generate_uuid)
    staff_id = Column(String, ForeignKey("users.id"), nullable=False)
    clock_in = Column(DateTime(timezone=True), nullable=False)
    clock_out = Column(DateTime(timezone=True), nullable=True)
    location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    staff = relationship("User", back_populates="time_entries")


class TimeModificationRequest(Base):
    __tablename__ = "time_modification_requests"

    id = Column(String, primary_key=True, default=generate_uuid)
    time_entry_id = Column(String, ForeignKey("time_entries.id"), nullable=False)
    staff_id = Column(String, ForeignKey("users.id"), nullable=False)
    staff_name = Column(String, nullable=False)
    original_clock_in = Column(DateTime(timezone=True), nullable=False)
    original_clock_out = Column(DateTime(timezone=True), nullable=True)
    requested_clock_in = Column(DateTime(timezone=True), nullable=False)
    requested_clock_out = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(Enum(TimeModificationStatus), default=TimeModificationStatus.PENDING)
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(String, primary_key=True, default=generate_uuid)
    staff_id = Column(String, ForeignKey("users.id"), nullable=False)
    staff_name = Column(String, nullable=True)
    location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    staff = relationship("User", back_populates="shifts")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(Enum(AuditAction), nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IncidentLegacy(Base):
    __tablename__ = "incidents"
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, nullable=False)  # low, medium, high, critical
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=True)
    booking_id = Column(String, ForeignKey("bookings.id"), nullable=True)
    reported_by = Column(String, ForeignKey("users.id"), nullable=False)
    location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    evidence_urls = Column(JSON, default=list)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, default=generate_uuid)
    household_id = Column(String, nullable=False, index=True)
    booking_id = Column(String, ForeignKey("bookings.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    approved = Column(Boolean, default=False)
    public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=generate_uuid)
    chat_type = Column(Enum(ChatType), nullable=False)
    participants = Column(JSON, default=list)  # List of user IDs
    participant_names = Column(JSON, default=dict)  # user_id -> name mapping
    last_message = Column(Text, nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    unread_count = Column(JSON, default=dict)  # user_id -> unread count
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False, index=True)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    sender_name = Column(String, nullable=False)
    sender_role = Column(Enum(UserRole), nullable=False)
    content = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== STAFF REQUESTS ====================

class StaffRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class StaffRequest(Base):
    __tablename__ = "staff_requests"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)

    status = Column(Enum(StaffRequestStatus), default=StaffRequestStatus.PENDING, nullable=False)

    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FormTemplateORM(Base):
    __tablename__ = "form_templates"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    location_id = Column(String, nullable=True, index=True)

    fields = Column(JSON, nullable=False, default=list)
    assignable_to = Column(String, nullable=False, default="all")

    require_signature = Column(Boolean, nullable=False, default=False)
    require_gps = Column(Boolean, nullable=False, default=False)
    allow_save_draft = Column(Boolean, nullable=False, default=True)
    allow_edit_after_submit = Column(Boolean, nullable=False, default=False)

    notify_on_submit = Column(JSON, nullable=False, default=list)

    is_active = Column(Boolean, nullable=False, default=True)
    is_template = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)

    category = Column(String, nullable=True, index=True)
    tags = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class FormSubmissionORM(Base):
    __tablename__ = "form_submissions"

    id = Column(String, primary_key=True, default=generate_uuid)
    template_id = Column(String, ForeignKey("form_templates.id"), nullable=False, index=True)

    staff_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    staff_name = Column(String, nullable=True)

    location_id = Column(String, ForeignKey("locations.id"), nullable=True, index=True)

    values = Column(JSON, nullable=False, default=dict)
    attachments = Column(JSON, nullable=False, default=list)

    signature_data = Column(Text, nullable=True)

    gps_latitude = Column(Float, nullable=True)
    gps_longitude = Column(Float, nullable=True)
    gps_accuracy = Column(Float, nullable=True)

    status = Column(String, nullable=False, default="draft")
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    related_type = Column(String, nullable=True)
    related_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



# ==================== ORGANIZATION ====================

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    timezone = Column(String, nullable=False, default="America/Chicago")
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    feature_flags = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== FACILITY STATUS ====================

class FacilityStatusType(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    HOLIDAY = "holiday"
    EMERGENCY_CLOSURE = "emergency_closure"


class FacilityStatus(Base):
    __tablename__ = "facility_status"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(FacilityStatusType), nullable=False, default=FacilityStatusType.OPEN)
    reason = Column(String, nullable=True)
    affects_bookings = Column(Boolean, default=True)
    set_by = Column(String, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== HOUSEHOLD & CONTACTS ====================

class HouseholdStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"

class MeetAndGreetStatus(str, enum.Enum):
    REQUIRED = "required"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    WAIVED = "waived"

class Household(Base):
    __tablename__ = "households"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    display_name = Column(String, nullable=False)
    status = Column(Enum(HouseholdStatus), default=HouseholdStatus.ACTIVE)
    preferred_contact_method = Column(String, nullable=True)
    general_notes = Column(Text, nullable=True)
    referral_source = Column(String, nullable=True)
    meet_and_greet_status = Column(Enum(MeetAndGreetStatus), default=MeetAndGreetStatus.REQUIRED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    updated_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    contacts = relationship("Contact", back_populates="household", cascade="all, delete-orphan")


class ContactType(str, enum.Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EMERGENCY = "emergency"
    AUTHORIZED_PICKUP = "authorized_pickup"
    OTHER = "other"


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    household_id = Column(String, ForeignKey("households.id"), nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    contact_type = Column(Enum(ContactType), default=ContactType.PRIMARY)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False)
    is_emergency_contact = Column(Boolean, default=False)
    is_authorized_pickup = Column(Boolean, default=False)
    relationship_to_household = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="contacts")


# ==================== VETERINARIAN ====================

class Veterinarian(Base):
    __tablename__ = "veterinarians"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    clinic_name = Column(String, nullable=False)
    veterinarian_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    emergency_instructions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== VACCINATION RECORDS ====================

class VaccinationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class VaccinationRecord(Base):
    __tablename__ = "vaccination_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, index=True)
    vaccination_type = Column(String, nullable=False)
    administration_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    provider = Column(String, nullable=True)
    verification_status = Column(Enum(VaccinationStatus), default=VaccinationStatus.PENDING, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    document_path = Column(Text, nullable=True)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=True)
    verified_by = Column(String, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== BEHAVIOR PROFILE ====================

class BehaviorProfile(Base):
    __tablename__ = "behavior_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, unique=True, index=True)
    handling_restrictions = Column(Text, nullable=True)
    known_triggers = Column(Text, nullable=True)
    dog_compatibility = Column(String, nullable=True)
    human_compatibility = Column(String, nullable=True)
    food_guarding = Column(Boolean, default=False)
    toy_guarding = Column(Boolean, default=False)
    barrier_reactivity = Column(Boolean, default=False)
    leash_behavior = Column(Text, nullable=True)
    escape_behavior = Column(Text, nullable=True)
    bite_history = Column(Boolean, default=False)
    bite_history_detail = Column(Text, nullable=True)
    muzzle_required = Column(Boolean, default=False)
    handlers_required = Column(Integer, default=1)
    approved_playgroups = Column(Text, nullable=True)
    prohibited_pairings = Column(JSON, default=list)
    active_safety_alert = Column(Boolean, default=False)
    safety_alert_detail = Column(Text, nullable=True)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== MEET AND GREET ====================

class MeetAndGreetOutcome(str, enum.Enum):
    PASS = "pass"
    CONDITIONAL = "conditional"
    FAIL = "fail"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class MeetAndGreet(Base):
    __tablename__ = "meet_and_greets"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, index=True)
    household_id = Column(String, ForeignKey("households.id"), nullable=False, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    conducted_by = Column(String, ForeignKey("users.id"), nullable=True)
    outcome = Column(Enum(MeetAndGreetOutcome), nullable=True)
    conditions = Column(Text, nullable=True)
    boarding_eligible_granted = Column(Boolean, default=False)
    daycare_eligible_granted = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # These columns were added directly via psql (AUTO_INIT_DB=false) and
    # were never reflected here, so any ORM (not raw-SQL) access to them
    # silently raised AttributeError.
    status = Column(String, default="pending")
    slot = Column(String, nullable=True)
    requested_stay_start = Column(Date, nullable=True)
    requested_stay_end = Column(Date, nullable=True)
    requested_by = Column(String, ForeignKey("users.id"), nullable=True)


# ==================== ROOMS ====================

class Room(Base):
    __tablename__ = "rooms"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    room_type = Column(String, nullable=True)
    max_dogs = Column(Integer, default=3)
    adjacency_group = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_out_of_service = Column(Boolean, default=False)
    out_of_service_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== SERVICE TYPES ====================

class ServiceType(Base):
    __tablename__ = "service_types"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_overnight = Column(Boolean, default=False)
    display_color = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== BOOKING DOG (proper join table) ====================

class ArrivalStatus(str, enum.Enum):
    EXPECTED = "expected"
    ARRIVED = "arrived"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"

class DepartureStatus(str, enum.Enum):
    EXPECTED = "expected"
    DEPARTED = "departed"
    EXTENDED = "extended"

class BookingDog(Base):
    __tablename__ = "booking_dogs_v2"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    booking_id = Column(String, ForeignKey("bookings.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, index=True)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=True)
    arrival_status = Column(Enum(ArrivalStatus), default=ArrivalStatus.EXPECTED)
    departure_status = Column(Enum(DepartureStatus), default=DepartureStatus.EXPECTED)
    care_notes = Column(Text, nullable=True)
    eligibility_override = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== STAYS ====================

class StayStatus(str, enum.Enum):
    EXPECTED = "expected"
    ON_SITE = "on_site"
    TEMPORARILY_OFF_SITE = "temporarily_off_site"
    CHECKED_OUT = "checked_out"


class Stay(Base):
    __tablename__ = "stays"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    booking_id = Column(String, ForeignKey("bookings.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, index=True)
    status = Column(Enum(StayStatus), default=StayStatus.EXPECTED, nullable=False)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    checked_in_by = Column(String, ForeignKey("users.id"), nullable=True)
    checked_out_at = Column(DateTime(timezone=True), nullable=True)
    checked_out_by = Column(String, ForeignKey("users.id"), nullable=True)
    is_first_stay = Column(Boolean, default=False)
    intake_condition_note = Column(Text, nullable=True)
    belongings_note = Column(Text, nullable=True)
    checkout_summary = Column(Text, nullable=True)
    last_handoff_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== STAY ALERTS ====================

class StayAlertSeverity(str, enum.Enum):
    INFO = "info"
    CAUTION = "caution"
    WARNING = "warning"


class StayAlert(Base):
    __tablename__ = "stay_alerts"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    stay_id = Column(String, ForeignKey("stays.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, index=True)
    alert_message = Column(Text, nullable=False)
    severity = Column(Enum(StayAlertSeverity), default=StayAlertSeverity.CAUTION, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    cleared_by = Column(String, ForeignKey("users.id"), nullable=True)
    cleared_at = Column(DateTime(timezone=True), nullable=True)
    cleared_reason = Column(Text, nullable=True)


# ==================== STAY FEEDING OVERRIDE ====================

class StayFeedingOverride(Base):
    __tablename__ = "stay_feeding_overrides"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    stay_id = Column(String, ForeignKey("stays.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, index=True)
    override_type = Column(String, nullable=False)
    override_detail = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== CHECKOUT PICKUP RECORD ====================

class CheckoutPickupRecord(Base):
    __tablename__ = "checkout_pickup_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    stay_id = Column(String, ForeignKey("stays.id"), nullable=False, index=True)
    pickup_person_name = Column(String, nullable=False)
    relationship_to_household = Column(String, nullable=True)
    is_authorized_pickup = Column(Boolean, default=False)
    id_verified = Column(Boolean, default=False)
    id_type = Column(String, nullable=True)
    confirmed_by = Column(String, ForeignKey("users.id"), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)


# ==================== ROOM ASSIGNMENT ====================

class RoomAssignment(Base):
    __tablename__ = "room_assignments"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    stay_id = Column(String, ForeignKey("stays.id"), nullable=False, index=True)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(String, ForeignKey("users.id"), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    reason_for_move = Column(Text, nullable=True)
    compatibility_override = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ==================== FEEDING ====================

class FeedingPlan(Base):
    __tablename__ = "feeding_plans"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, index=True)
    food_name = Column(String, nullable=False)
    amount = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    scheduled_times = Column(JSON, default=list)
    preparation_instructions = Column(Text, nullable=True)
    supplements = Column(Text, nullable=True)
    food_supplied_by_owner = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AppetiteRating(str, enum.Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    REFUSED = "refused"


class FeedingEvent(Base):
    __tablename__ = "feeding_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    stay_id = Column(String, ForeignKey("stays.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, index=True)
    scheduled_time = Column(DateTime(timezone=True), nullable=True)
    completed_time = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(String, ForeignKey("users.id"), nullable=True)
    amount_offered = Column(String, nullable=True)
    amount_eaten = Column(String, nullable=True)
    appetite_rating = Column(Enum(AppetiteRating), nullable=True)
    refusal_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ==================== MEDICATIONS ====================

class MedicationStatus(str, enum.Enum):
    DUE = "due"
    ADMINISTERED = "administered"
    REFUSED = "refused"
    MISSED = "missed"
    HELD = "held"
    NOT_APPLICABLE = "not_applicable"


class Medication(Base):
    __tablename__ = "medications"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    dose = Column(String, nullable=False)
    route = Column(String, nullable=True)
    frequency = Column(String, nullable=False)
    scheduled_times = Column(JSON, default=list)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    as_needed = Column(Boolean, default=False)
    storage_instructions = Column(Text, nullable=True)
    administration_instructions = Column(Text, nullable=True)
    prescriber = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MedicationAdministration(Base):
    __tablename__ = "medication_administrations"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    stay_id = Column(String, ForeignKey("stays.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, index=True)
    medication_id = Column(String, ForeignKey("medications.id"), nullable=False, index=True)
    scheduled_time = Column(DateTime(timezone=True), nullable=True)
    administered_time = Column(DateTime(timezone=True), nullable=True)
    administered_by = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(MedicationStatus), default=MedicationStatus.DUE, nullable=False)
    dose_administered = Column(String, nullable=True)
    exception_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== SHIFT HANDOFF ====================

class ShiftHandoff(Base):
    __tablename__ = "shift_handoffs"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    staff_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    shift_start = Column(DateTime(timezone=True), nullable=True)
    shift_end = Column(DateTime(timezone=True), nullable=True)
    dogs_on_site_snapshot = Column(JSON, default=list)
    outstanding_care = Column(JSON, default=list)
    active_medications = Column(JSON, default=list)
    active_alerts = Column(JSON, default=list)
    open_incidents = Column(JSON, default=list)
    staff_notes = Column(Text, nullable=True)
    follow_up_items = Column(JSON, default=list)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== TASKS ====================

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=True, index=True)
    stay_id = Column(String, ForeignKey("stays.id"), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(String, ForeignKey("users.id"), nullable=True)
    checklist = Column(JSON, default=list)
    recurrence = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    form_template_id = Column(String, ForeignKey("form_templates.id"), nullable=True)
    require_form_completion = Column(Boolean, default=False)


# ==================== INCIDENTS ====================

class IncidentSeverity(str, enum.Enum):
    INFO = "info"           # Tier 1 - FYI only
    CAUTION = "caution"     # Tier 2 - monitor
    WARNING = "warning"     # Tier 3 - owner acknowledgment required
    CRITICAL = "critical"   # Tier 4 - immediate action required

class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    CLOSED = "closed"

class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(IncidentSeverity), nullable=False)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.OPEN, nullable=False)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=True, index=True)
    stay_id = Column(String, ForeignKey("stays.id"), nullable=True)
    reported_by = Column(String, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    location_description = Column(String, nullable=True)
    witness_names = Column(Text, nullable=True)
    immediate_action_taken = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, default=False)
    follow_up_notes = Column(Text, nullable=True)
    acknowledged_by = Column(String, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== DOG NOTES ====================

class DogNote(Base):
    __tablename__ = "dog_notes"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    dog_id = Column(String, ForeignKey("dogs.id"), nullable=False, index=True)
    note_text = Column(String(500), nullable=False)
    is_alert = Column(Boolean, default=False)
    image_keys = Column(JSON, default=list)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
