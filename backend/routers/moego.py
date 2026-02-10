"""
MoeGo Parity Router - Phase 1 & 2
Handles kennels, time slots, coupons, card-on-file, eligibility, bookings, operations
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid

from models import (
    UserRole,
    # Kennels
    Kennel, KennelCreate, KennelResponse, KennelType, KennelStatus,
    # Time Slots
    TimeSlot, TimeSlotCreate, TimeSlotResponse, SlotType, SlotAvailability,
    # Coupons
    CouponCode, CouponCodeCreate, CouponCodeResponse, CouponUsage, DiscountType,
    # Card on File
    StoredPaymentMethod, StoredPaymentMethodResponse, PaymentMethodType, CardBrand,
    # Eligibility
    EligibilityRule, EligibilityRuleCreate, EligibilityRuleResponse,
    EligibilityRuleType, EligibilityCheckResult,
    # Waitlist
    WaitlistEntry, WaitlistEntryCreate, WaitlistEntryResponse, WaitlistStatus,
    # Operations
    DogOnSite, DailyOperationsSummary,
)
from auth import get_current_user
from services.notifications import (
    NotificationService,
    NotificationChannel,
    notify_booking_auto_blocked,
    notify_admin_pending_approval,
    notify_booking_approved,
    notify_booking_rejected
)

router = APIRouter(prefix="/api/moego", tags=["MoeGo Parity"])
security = HTTPBearer()


def get_db():
    """Get database connection - will be injected"""
    from server import db
    return db


# ==================== KENNELS / RUNS ====================

@router.get("/kennels", response_model=List[KennelResponse])
async def list_kennels(
    location_id: Optional[str] = None,
    kennel_type: Optional[KennelType] = None,
    status: Optional[KennelStatus] = None,
    is_active: bool = True,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List all kennels/runs with optional filters"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {"is_active": is_active}
    if location_id:
        query["location_id"] = location_id
    if kennel_type:
        query["kennel_type"] = kennel_type.value
    if status:
        query["status"] = status.value
    
    kennels = await db.kennels.find(query, {"_id": 0}).sort("sort_order", 1).to_list(500)
    return [KennelResponse(**k) for k in kennels]


@router.get("/kennels/{kennel_id}", response_model=KennelResponse)
async def get_kennel(
    kennel_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single kennel by ID"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    kennel = await db.kennels.find_one({"id": kennel_id}, {"_id": 0})
    if not kennel:
        raise HTTPException(status_code=404, detail="Kennel not found")
    
    return KennelResponse(**kennel)


@router.post("/kennels", response_model=KennelResponse)
async def create_kennel(
    data: KennelCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new kennel/run (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check for duplicate name in location
    existing = await db.kennels.find_one({
        "location_id": data.location_id,
        "name": data.name
    })
    if existing:
        raise HTTPException(status_code=400, detail="Kennel with this name already exists at this location")
    
    kennel = Kennel(**data.model_dump())
    doc = kennel.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['kennel_type'] = doc['kennel_type'].value
    doc['status'] = doc['status'].value
    
    await db.kennels.insert_one(doc)
    return KennelResponse(**kennel.model_dump())


@router.patch("/kennels/{kennel_id}", response_model=KennelResponse)
async def update_kennel(
    kennel_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a kennel (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    existing = await db.kennels.find_one({"id": kennel_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Kennel not found")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Convert enums to strings
    if 'kennel_type' in updates and hasattr(updates['kennel_type'], 'value'):
        updates['kennel_type'] = updates['kennel_type'].value
    if 'status' in updates and hasattr(updates['status'], 'value'):
        updates['status'] = updates['status'].value
    
    await db.kennels.update_one({"id": kennel_id}, {"$set": updates})
    
    kennel = await db.kennels.find_one({"id": kennel_id}, {"_id": 0})
    return KennelResponse(**kennel)


@router.delete("/kennels/{kennel_id}")
async def delete_kennel(
    kennel_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Deactivate a kennel (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.kennels.update_one(
        {"id": kennel_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Kennel not found")
    
    return {"message": "Kennel deactivated"}


@router.get("/kennels/availability/{location_id}")
async def get_kennel_availability(
    location_id: str,
    check_in_date: datetime,
    check_out_date: datetime,
    kennel_type: Optional[KennelType] = None,
    dog_weight: Optional[float] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get available kennels for a date range"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    # Get all active kennels for location
    query = {"location_id": location_id, "is_active": True}
    if kennel_type:
        query["kennel_type"] = kennel_type.value
    
    kennels = await db.kennels.find(query, {"_id": 0}).to_list(500)
    
    # Get bookings that overlap with requested dates
    overlapping_bookings = await db.bookings.find({
        "location_id": location_id,
        "status": {"$nin": ["cancelled", "checked_out"]},
        "$or": [
            {"check_in_date": {"$lt": check_out_date.isoformat()}, "check_out_date": {"$gt": check_in_date.isoformat()}}
        ]
    }, {"_id": 0, "kennel_id": 1}).to_list(1000)
    
    occupied_kennel_ids = {b.get('kennel_id') for b in overlapping_bookings if b.get('kennel_id')}
    
    available = []
    for kennel in kennels:
        if kennel['id'] in occupied_kennel_ids:
            continue
        
        # Check weight restrictions
        if dog_weight:
            min_w = kennel.get('min_weight')
            max_w = kennel.get('max_weight')
            if min_w and dog_weight < min_w:
                continue
            if max_w and dog_weight > max_w:
                continue
        
        available.append(KennelResponse(**kennel))
    
    return {
        "available_kennels": available,
        "total_kennels": len(kennels),
        "occupied_kennels": len(occupied_kennel_ids)
    }


# ==================== TIME SLOTS ====================

@router.get("/slots", response_model=List[TimeSlotResponse])
async def list_time_slots(
    location_id: Optional[str] = None,
    slot_type: Optional[SlotType] = None,
    is_active: bool = True,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List configured time slots"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {"is_active": is_active}
    if location_id:
        query["location_id"] = location_id
    if slot_type:
        query["slot_type"] = slot_type.value
    
    slots = await db.time_slots.find(query, {"_id": 0}).sort("start_time", 1).to_list(200)
    return [TimeSlotResponse(**s) for s in slots]


@router.post("/slots", response_model=TimeSlotResponse)
async def create_time_slot(
    data: TimeSlotCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a time slot (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    slot = TimeSlot(**data.model_dump())
    doc = slot.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['slot_type'] = doc['slot_type'].value
    if doc.get('effective_date'):
        doc['effective_date'] = doc['effective_date'].isoformat()
    if doc.get('expiry_date'):
        doc['expiry_date'] = doc['expiry_date'].isoformat()
    
    await db.time_slots.insert_one(doc)
    return TimeSlotResponse(**slot.model_dump())


@router.patch("/slots/{slot_id}", response_model=TimeSlotResponse)
async def update_time_slot(
    slot_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a time slot (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.time_slots.update_one({"id": slot_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Time slot not found")
    
    slot = await db.time_slots.find_one({"id": slot_id}, {"_id": 0})
    return TimeSlotResponse(**slot)


@router.delete("/slots/{slot_id}")
async def delete_time_slot(
    slot_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Deactivate a time slot (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.time_slots.update_one(
        {"id": slot_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Time slot not found")
    
    return {"message": "Time slot deactivated"}


@router.get("/slots/availability/{location_id}")
async def get_slot_availability(
    location_id: str,
    date: datetime,
    slot_type: SlotType,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get availability for slots on a specific date"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    day_of_week = date.weekday()
    
    # Get applicable slots
    slots = await db.time_slots.find({
        "location_id": location_id,
        "slot_type": slot_type.value,
        "is_active": True,
        "days_of_week": day_of_week
    }, {"_id": 0}).to_list(100)
    
    # Get bookings for this date
    date_str = date.strftime("%Y-%m-%d")
    
    availability = []
    for slot in slots:
        # Count bookings in this slot
        # For check-in slots, match check_in_date
        # For check-out slots, match check_out_date
        if slot_type in [SlotType.CHECK_IN, SlotType.DAYCARE_DROP_OFF]:
            date_field = "check_in_date"
        else:
            date_field = "check_out_date"
        
        booking_count = await db.bookings.count_documents({
            "location_id": location_id,
            "status": {"$nin": ["cancelled"]},
            date_field: {"$regex": f"^{date_str}"},
            "check_in_slot.time": slot['start_time']
        })
        
        available_spots = slot['max_bookings'] - booking_count
        status = "available"
        if available_spots <= 0:
            status = "full"
        elif available_spots <= 2:
            status = "limited"
        
        availability.append(SlotAvailability(
            slot_id=slot['id'],
            slot_type=SlotType(slot['slot_type']),
            date=date,
            start_time=slot['start_time'],
            end_time=slot['end_time'],
            max_bookings=slot['max_bookings'],
            current_bookings=booking_count,
            available_spots=max(0, available_spots),
            status=status
        ))
    
    return availability


# ==================== COUPON CODES ====================

@router.get("/coupons", response_model=List[CouponCodeResponse])
async def list_coupons(
    is_active: bool = True,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List all coupon codes (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    coupons = await db.coupon_codes.find({"is_active": is_active}, {"_id": 0}).to_list(500)
    return [CouponCodeResponse(**c) for c in coupons]


@router.get("/coupons/{coupon_id}", response_model=CouponCodeResponse)
async def get_coupon(
    coupon_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a coupon by ID (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    coupon = await db.coupon_codes.find_one({"id": coupon_id}, {"_id": 0})
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    return CouponCodeResponse(**coupon)


@router.post("/coupons", response_model=CouponCodeResponse)
async def create_coupon(
    data: CouponCodeCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a coupon code (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check for duplicate code
    existing = await db.coupon_codes.find_one({"code": data.code.upper()})
    if existing:
        raise HTTPException(status_code=400, detail="Coupon code already exists")
    
    coupon = CouponCode(**data.model_dump(), created_by=user.id)
    coupon.code = coupon.code.upper()  # Normalize to uppercase
    
    doc = coupon.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['discount_type'] = doc['discount_type'].value
    if doc.get('valid_from'):
        doc['valid_from'] = doc['valid_from'].isoformat()
    if doc.get('valid_until'):
        doc['valid_until'] = doc['valid_until'].isoformat()
    
    await db.coupon_codes.insert_one(doc)
    return CouponCodeResponse(**coupon.model_dump())


@router.patch("/coupons/{coupon_id}", response_model=CouponCodeResponse)
async def update_coupon(
    coupon_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a coupon (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.coupon_codes.update_one({"id": coupon_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    coupon = await db.coupon_codes.find_one({"id": coupon_id}, {"_id": 0})
    return CouponCodeResponse(**coupon)


@router.delete("/coupons/{coupon_id}")
async def delete_coupon(
    coupon_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Deactivate a coupon (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.coupon_codes.update_one(
        {"id": coupon_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    return {"message": "Coupon deactivated"}


@router.post("/coupons/validate")
async def validate_coupon(
    code: str,
    household_id: str,
    subtotal: float,
    nights: int = 1,
    dog_count: int = 1,
    service_type_id: Optional[str] = None,
    location_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Validate a coupon code and calculate discount"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    coupon = await db.coupon_codes.find_one({"code": code.upper(), "is_active": True}, {"_id": 0})
    if not coupon:
        raise HTTPException(status_code=404, detail="Invalid coupon code")
    
    now = datetime.now(timezone.utc)
    
    # Check validity dates
    if coupon.get('valid_from'):
        valid_from = datetime.fromisoformat(coupon['valid_from'].replace('Z', '+00:00'))
        if now < valid_from:
            raise HTTPException(status_code=400, detail="Coupon not yet valid")
    
    if coupon.get('valid_until'):
        valid_until = datetime.fromisoformat(coupon['valid_until'].replace('Z', '+00:00'))
        if now > valid_until:
            raise HTTPException(status_code=400, detail="Coupon has expired")
    
    # Check max uses
    if coupon.get('max_uses') and coupon.get('current_uses', 0) >= coupon['max_uses']:
        raise HTTPException(status_code=400, detail="Coupon usage limit reached")
    
    # Check per-customer usage
    customer_uses = await db.coupon_usage.count_documents({
        "coupon_id": coupon['id'],
        "household_id": household_id
    })
    if customer_uses >= coupon.get('max_uses_per_customer', 1):
        raise HTTPException(status_code=400, detail="You have already used this coupon")
    
    # Check minimum requirements
    if coupon.get('min_order_amount') and subtotal < coupon['min_order_amount']:
        raise HTTPException(status_code=400, detail=f"Minimum order amount is ${coupon['min_order_amount']}")
    
    if coupon.get('min_nights') and nights < coupon['min_nights']:
        raise HTTPException(status_code=400, detail=f"Minimum {coupon['min_nights']} nights required")
    
    if coupon.get('min_dogs') and dog_count < coupon['min_dogs']:
        raise HTTPException(status_code=400, detail=f"Minimum {coupon['min_dogs']} dogs required")
    
    # Check service/location restrictions
    if coupon.get('service_type_ids') and service_type_id:
        if service_type_id not in coupon['service_type_ids']:
            raise HTTPException(status_code=400, detail="Coupon not valid for this service")
    
    if coupon.get('location_ids') and location_id:
        if location_id not in coupon['location_ids']:
            raise HTTPException(status_code=400, detail="Coupon not valid at this location")
    
    # Check first booking only
    if coupon.get('first_booking_only'):
        previous_bookings = await db.bookings.count_documents({
            "household_id": household_id,
            "status": {"$nin": ["cancelled"]}
        })
        if previous_bookings > 0:
            raise HTTPException(status_code=400, detail="Coupon valid for first booking only")
    
    # Calculate discount
    discount_type = coupon['discount_type']
    discount_value = coupon['discount_value']
    discount_amount = 0.0
    
    if discount_type == "percentage":
        discount_amount = subtotal * (discount_value / 100)
    elif discount_type == "flat_amount":
        discount_amount = min(discount_value, subtotal)
    elif discount_type == "free_night" and coupon.get('buy_nights_get_free'):
        free_nights = nights // (coupon['buy_nights_get_free'] + 1)
        if free_nights > 0:
            nightly_rate = subtotal / nights
            discount_amount = nightly_rate * free_nights
    
    return {
        "valid": True,
        "coupon_id": coupon['id'],
        "coupon_code": coupon['code'],
        "discount_type": discount_type,
        "discount_value": discount_value,
        "discount_amount": round(discount_amount, 2),
        "new_total": round(subtotal - discount_amount, 2),
        "message": coupon.get('description', f"Discount of ${round(discount_amount, 2)} applied")
    }


# ==================== ELIGIBILITY RULES ====================

@router.get("/eligibility-rules", response_model=List[EligibilityRuleResponse])
async def list_eligibility_rules(
    location_id: Optional[str] = None,
    rule_type: Optional[EligibilityRuleType] = None,
    is_active: bool = True,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List eligibility rules"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    query = {"is_active": is_active}
    if location_id:
        query["$or"] = [{"location_id": None}, {"location_id": location_id}]
    if rule_type:
        query["rule_type"] = rule_type.value
    
    rules = await db.eligibility_rules.find(query, {"_id": 0}).to_list(200)
    return [EligibilityRuleResponse(**r) for r in rules]


@router.post("/eligibility-rules", response_model=EligibilityRuleResponse)
async def create_eligibility_rule(
    data: EligibilityRuleCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create an eligibility rule (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rule = EligibilityRule(**data.model_dump())
    doc = rule.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['rule_type'] = doc['rule_type'].value
    
    await db.eligibility_rules.insert_one(doc)
    return EligibilityRuleResponse(**rule.model_dump())


@router.patch("/eligibility-rules/{rule_id}", response_model=EligibilityRuleResponse)
async def update_eligibility_rule(
    rule_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update an eligibility rule (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.eligibility_rules.update_one({"id": rule_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = await db.eligibility_rules.find_one({"id": rule_id}, {"_id": 0})
    return EligibilityRuleResponse(**rule)


@router.delete("/eligibility-rules/{rule_id}")
async def delete_eligibility_rule(
    rule_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Deactivate an eligibility rule (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.eligibility_rules.update_one(
        {"id": rule_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"message": "Eligibility rule deactivated"}


@router.post("/eligibility/check")
async def check_dog_eligibility(
    dog_id: str,
    service_type_id: Optional[str] = None,
    location_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Check if a dog is eligible for booking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    # Get dog
    dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0})
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    
    # Get applicable rules
    rule_query = {"is_active": True}
    if location_id:
        rule_query["$or"] = [{"location_id": None}, {"location_id": location_id}]
    if service_type_id:
        rule_query["$and"] = [
            rule_query.get("$or", {"location_id": None}),
            {"$or": [{"service_type_ids": []}, {"service_type_ids": service_type_id}]}
        ]
    
    rules = await db.eligibility_rules.find(rule_query, {"_id": 0}).to_list(100)
    
    errors = []
    warnings = []
    missing_vaccines = []
    expiring_vaccines = []
    
    for rule in rules:
        rule_type = rule.get('rule_type')
        
        if rule_type == 'vaccination':
            # Check required vaccines
            dog_vaccines = {v.get('vaccine_name', '').lower(): v for v in dog.get('vaccinations', [])}
            for required in rule.get('required_vaccines', []):
                required_lower = required.lower()
                if required_lower not in dog_vaccines:
                    missing_vaccines.append(required)
                    if rule.get('is_hard_block'):
                        errors.append({
                            "rule": rule['name'],
                            "type": "vaccination",
                            "message": rule.get('block_message', f"Missing {required} vaccination")
                        })
                    else:
                        warnings.append({
                            "rule": rule['name'],
                            "type": "vaccination",
                            "message": rule.get('warning_message', f"Missing {required} vaccination")
                        })
                else:
                    # Check expiry
                    vaccine = dog_vaccines[required_lower]
                    if vaccine.get('expiry_date'):
                        expiry = datetime.fromisoformat(vaccine['expiry_date'].replace('Z', '+00:00'))
                        buffer_days = rule.get('vaccine_expiry_buffer_days', 0)
                        if expiry < datetime.now(timezone.utc) + timedelta(days=buffer_days):
                            expiring_vaccines.append({
                                "vaccine": required,
                                "expiry_date": vaccine['expiry_date'],
                                "days_until_expiry": (expiry - datetime.now(timezone.utc)).days
                            })
        
        elif rule_type == 'weight':
            dog_weight = dog.get('weight')
            if dog_weight:
                if rule.get('min_weight') and dog_weight < rule['min_weight']:
                    msg = f"Dog weight ({dog_weight}lb) below minimum ({rule['min_weight']}lb)"
                    if rule.get('is_hard_block'):
                        errors.append({"rule": rule['name'], "type": "weight", "message": msg})
                    else:
                        warnings.append({"rule": rule['name'], "type": "weight", "message": msg})
                
                if rule.get('max_weight') and dog_weight > rule['max_weight']:
                    msg = f"Dog weight ({dog_weight}lb) exceeds maximum ({rule['max_weight']}lb)"
                    if rule.get('is_hard_block'):
                        errors.append({"rule": rule['name'], "type": "weight", "message": msg})
                    else:
                        warnings.append({"rule": rule['name'], "type": "weight", "message": msg})
        
        elif rule_type == 'breed':
            dog_breed = dog.get('breed', '').lower()
            blocked_breeds = [b.lower() for b in rule.get('blocked_breeds', [])]
            allowed_breeds = [b.lower() for b in rule.get('allowed_breeds', [])]
            
            if blocked_breeds and dog_breed in blocked_breeds:
                if rule.get('is_hard_block'):
                    errors.append({
                        "rule": rule['name'],
                        "type": "breed",
                        "message": rule.get('block_message', f"Breed '{dog.get('breed')}' not accepted")
                    })
                else:
                    warnings.append({
                        "rule": rule['name'],
                        "type": "breed",
                        "message": rule.get('warning_message', f"Breed '{dog.get('breed')}' requires review")
                    })
            
            if allowed_breeds and dog_breed not in allowed_breeds:
                warnings.append({
                    "rule": rule['name'],
                    "type": "breed",
                    "message": f"Breed '{dog.get('breed')}' not in allowed list"
                })
        
        elif rule_type == 'behavior':
            if rule.get('requires_dog_friendly') and not dog.get('friendly_with_dogs'):
                warnings.append({
                    "rule": rule['name'],
                    "type": "behavior",
                    "message": "Dog not marked as dog-friendly"
                })
            
            if rule.get('blocks_aggressive') and dog.get('incidents_of_aggression'):
                if rule.get('is_hard_block'):
                    errors.append({
                        "rule": rule['name'],
                        "type": "behavior",
                        "message": "Dog has history of aggression"
                    })
                else:
                    warnings.append({
                        "rule": rule['name'],
                        "type": "behavior",
                        "message": "Dog has history of aggression - requires review"
                    })
    
    return EligibilityCheckResult(
        dog_id=dog_id,
        dog_name=dog.get('name', 'Unknown'),
        is_eligible=len(errors) == 0,
        has_warnings=len(warnings) > 0,
        errors=errors,
        warnings=warnings,
        missing_vaccines=missing_vaccines,
        expiring_vaccines=expiring_vaccines
    )


# ==================== WAITLIST ====================

@router.get("/waitlist", response_model=List[WaitlistEntryResponse])
async def list_waitlist(
    location_id: Optional[str] = None,
    status: Optional[WaitlistStatus] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List waitlist entries (admin/staff)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    query = {}
    if location_id:
        query["location_id"] = location_id
    if status:
        query["status"] = status.value
    
    entries = await db.waitlist.find(query, {"_id": 0}).sort("created_at", 1).to_list(500)
    return [WaitlistEntryResponse(**e) for e in entries]


@router.post("/waitlist", response_model=WaitlistEntryResponse)
async def join_waitlist(
    data: WaitlistEntryCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Add customer to waitlist"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    # Get customer info
    customer = await db.users.find_one({"id": user.id}, {"_id": 0})
    
    # Get current position
    position = await db.waitlist.count_documents({
        "location_id": data.location_id,
        "status": WaitlistStatus.WAITING.value,
        "requested_check_in": {"$lte": data.requested_check_in.isoformat()}
    })
    
    entry = WaitlistEntry(
        **data.model_dump(),
        household_id=user.household_id or user.id,
        customer_name=user.full_name,
        customer_email=user.email,
        customer_phone=user.phone,
        position=position + 1
    )
    
    doc = entry.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['requested_check_in'] = doc['requested_check_in'].isoformat()
    doc['requested_check_out'] = doc['requested_check_out'].isoformat()
    doc['status'] = doc['status'].value
    if doc.get('preferred_kennel_type'):
        doc['preferred_kennel_type'] = doc['preferred_kennel_type'].value
    
    await db.waitlist.insert_one(doc)
    return WaitlistEntryResponse(**entry.model_dump())


@router.post("/waitlist/{entry_id}/offer")
async def offer_waitlist_spot(
    entry_id: str,
    expires_hours: int = 24,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Offer a spot to waitlist entry (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=expires_hours)
    
    result = await db.waitlist.update_one(
        {"id": entry_id, "status": WaitlistStatus.WAITING.value},
        {"$set": {
            "status": WaitlistStatus.OFFERED.value,
            "offered_at": now.isoformat(),
            "offer_expires_at": expires.isoformat(),
            "updated_at": now.isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Waitlist entry not found or not in waiting status")
    
    return {"message": "Offer sent", "expires_at": expires.isoformat()}


@router.post("/waitlist/{entry_id}/respond")
async def respond_to_waitlist_offer(
    entry_id: str,
    accept: bool,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Accept or decline waitlist offer"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    entry = await db.waitlist.find_one({"id": entry_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    
    # Verify ownership
    if entry.get('household_id') != (user.household_id or user.id) and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not your waitlist entry")
    
    if entry.get('status') != WaitlistStatus.OFFERED.value:
        raise HTTPException(status_code=400, detail="No pending offer")
    
    # Check if offer expired
    if entry.get('offer_expires_at'):
        expires = datetime.fromisoformat(entry['offer_expires_at'].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expires:
            await db.waitlist.update_one(
                {"id": entry_id},
                {"$set": {"status": WaitlistStatus.EXPIRED.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            raise HTTPException(status_code=400, detail="Offer has expired")
    
    new_status = WaitlistStatus.ACCEPTED.value if accept else WaitlistStatus.DECLINED.value
    
    await db.waitlist.update_one(
        {"id": entry_id},
        {"$set": {
            "status": new_status,
            "responded_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": f"Offer {'accepted' if accept else 'declined'}"}


# ==================== DAILY OPERATIONS ====================

@router.get("/operations/dogs-on-site")
async def get_dogs_on_site(
    location_id: str,
    date: Optional[datetime] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all dogs currently on site"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    if not date:
        date = datetime.now(timezone.utc)
    
    date_str = date.strftime("%Y-%m-%d")
    
    # Get active bookings (checked in or should be on site)
    bookings = await db.bookings.find({
        "location_id": location_id,
        "status": {"$in": ["confirmed", "checked_in"]},
        "check_in_date": {"$lte": date.isoformat()},
        "check_out_date": {"$gte": date.isoformat()}
    }, {"_id": 0}).to_list(500)
    
    dogs_on_site = []
    
    for booking in bookings:
        # Get dogs
        dog_ids = booking.get('dog_ids', [])
        dogs = await db.dogs.find({"id": {"$in": dog_ids}}, {"_id": 0}).to_list(len(dog_ids))
        
        # Get customer
        customer = await db.users.find_one({"household_id": booking.get('household_id')}, {"_id": 0})
        if not customer:
            customer = await db.users.find_one({"id": booking.get('customer_id')}, {"_id": 0})
        
        # Get kennel
        kennel = None
        if booking.get('kennel_id'):
            kennel = await db.kennels.find_one({"id": booking['kennel_id']}, {"_id": 0})
        
        check_out = datetime.fromisoformat(booking['check_out_date'].replace('Z', '+00:00'))
        nights_remaining = (check_out.date() - date.date()).days
        
        for dog in dogs:
            dogs_on_site.append(DogOnSite(
                dog_id=dog['id'],
                dog_name=dog['name'],
                breed=dog.get('breed', 'Unknown'),
                weight=dog.get('weight'),
                photo_url=dog.get('photo_url'),
                booking_id=booking['id'],
                household_id=booking.get('household_id'),
                customer_name=customer.get('full_name', 'Unknown') if customer else 'Unknown',
                customer_phone=customer.get('phone') if customer else None,
                kennel_id=booking.get('kennel_id'),
                kennel_name=kennel.get('name') if kennel else None,
                check_in_date=datetime.fromisoformat(booking['check_in_date'].replace('Z', '+00:00')),
                check_out_date=check_out,
                nights_remaining=nights_remaining,
                needs_medication=bool(dog.get('medication_requirements')),
                medication_notes=dog.get('medication_requirements'),
                special_diet=bool(dog.get('meal_routine')),
                diet_notes=dog.get('meal_routine'),
                behavioral_flags=dog.get('medical_flags', []),
                bath_scheduled=booking.get('bath_requested', False),
                bath_completed=booking.get('bath_completed', False)
            ))
    
    return dogs_on_site


@router.get("/operations/summary")
async def get_operations_summary(
    location_id: str,
    date: Optional[datetime] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get daily operations summary"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    if not date:
        date = datetime.now(timezone.utc)
    
    date_str = date.strftime("%Y-%m-%d")
    
    # Count kennels
    total_kennels = await db.kennels.count_documents({"location_id": location_id, "is_active": True})
    
    # Count occupied
    occupied = await db.kennels.count_documents({
        "location_id": location_id,
        "is_active": True,
        "status": KennelStatus.OCCUPIED.value
    })
    
    # Check-ins today
    check_ins = await db.bookings.find({
        "location_id": location_id,
        "check_in_date": {"$regex": f"^{date_str}"}
    }, {"_id": 0, "status": 1}).to_list(100)
    
    check_ins_scheduled = len(check_ins)
    check_ins_completed = len([b for b in check_ins if b.get('status') in ['checked_in', 'checked_out']])
    
    # Check-outs today
    check_outs = await db.bookings.find({
        "location_id": location_id,
        "check_out_date": {"$regex": f"^{date_str}"}
    }, {"_id": 0, "status": 1}).to_list(100)
    
    check_outs_scheduled = len(check_outs)
    check_outs_completed = len([b for b in check_outs if b.get('status') == 'checked_out'])
    
    # Dogs on site (from active bookings)
    active_bookings = await db.bookings.find({
        "location_id": location_id,
        "status": {"$in": ["confirmed", "checked_in"]},
        "check_in_date": {"$lte": date.isoformat()},
        "check_out_date": {"$gte": date.isoformat()}
    }, {"_id": 0, "dog_ids": 1, "bath_requested": 1, "bath_completed": 1}).to_list(500)
    
    dogs_on_site = sum(len(b.get('dog_ids', [])) for b in active_bookings)
    baths_scheduled = len([b for b in active_bookings if b.get('bath_requested')])
    baths_completed = len([b for b in active_bookings if b.get('bath_completed')])
    
    return DailyOperationsSummary(
        date=date,
        location_id=location_id,
        total_kennels=total_kennels,
        occupied_kennels=occupied,
        available_kennels=total_kennels - occupied,
        occupancy_rate=round(occupied / total_kennels * 100, 1) if total_kennels > 0 else 0,
        check_ins_scheduled=check_ins_scheduled,
        check_ins_completed=check_ins_completed,
        check_outs_scheduled=check_outs_scheduled,
        check_outs_completed=check_outs_completed,
        dogs_on_site=dogs_on_site,
        dogs_needing_medication=0,  # Would need to aggregate from dogs
        dogs_with_special_diet=0,
        baths_scheduled=baths_scheduled,
        baths_completed=baths_completed,
        vaccines_expiring_soon=0,
        overdue_checkouts=0,
        pending_payments=0
    )


# ==================== PHASE 2: BOOKING & CHECK-IN/OUT ====================

@router.post("/bookings/smart")
async def create_smart_booking(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Smart booking endpoint with eligibility checks and auto-block logic.
    If eligibility fails with hard block, auto-block the booking and require admin approval.
    """
    db = get_db()
    user = await get_current_user(credentials, db)
    
    dog_ids = data.get('dog_ids', [])
    location_id = data.get('location_id')
    check_in_date = data.get('check_in_date')
    check_out_date = data.get('check_out_date')
    kennel_id = data.get('kennel_id')
    bath_before_pickup = data.get('bath_before_pickup', False)
    bath_day = data.get('bath_day', 'checkout')  # 'checkout' or 'day_before'
    check_in_slot_id = data.get('check_in_slot_id')
    check_out_slot_id = data.get('check_out_slot_id')
    notes = data.get('notes', '')
    coupon_code = data.get('coupon_code')
    
    # Parse dates
    if isinstance(check_in_date, str):
        check_in_date = datetime.fromisoformat(check_in_date.replace('Z', '+00:00'))
    if isinstance(check_out_date, str):
        check_out_date = datetime.fromisoformat(check_out_date.replace('Z', '+00:00'))
    
    nights = (check_out_date - check_in_date).days
    if nights <= 0:
        raise HTTPException(status_code=400, detail="Invalid date range")
    
    # Check eligibility for all dogs
    eligibility_results = []
    has_hard_block = False
    all_errors = []
    all_warnings = []
    
    for dog_id in dog_ids:
        dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0})
        if not dog:
            raise HTTPException(status_code=404, detail=f"Dog {dog_id} not found")
        
        # Get applicable rules
        rules = await db.eligibility_rules.find({"is_active": True}, {"_id": 0}).to_list(100)
        
        errors = []
        warnings = []
        missing_vaccines = []
        
        for rule in rules:
            rule_type = rule.get('rule_type')
            
            if rule_type == 'vaccination':
                dog_vaccines = {v.get('vaccine_name', '').lower(): v for v in dog.get('vaccinations', [])}
                for required in rule.get('required_vaccines', []):
                    required_lower = required.lower()
                    if required_lower not in dog_vaccines:
                        missing_vaccines.append(required)
                        if rule.get('is_hard_block'):
                            has_hard_block = True
                            errors.append({
                                "dog_id": dog_id,
                                "dog_name": dog.get('name'),
                                "rule": rule['name'],
                                "type": "vaccination",
                                "message": f"Missing {required} vaccination"
                            })
                        else:
                            warnings.append({
                                "dog_id": dog_id,
                                "dog_name": dog.get('name'),
                                "message": f"Missing {required} vaccination"
                            })
            
            elif rule_type == 'weight':
                dog_weight = dog.get('weight')
                if dog_weight:
                    if rule.get('min_weight') and dog_weight < rule['min_weight']:
                        if rule.get('is_hard_block'):
                            has_hard_block = True
                            errors.append({
                                "dog_id": dog_id,
                                "dog_name": dog.get('name'),
                                "rule": rule['name'],
                                "message": f"Weight {dog_weight}lb below minimum {rule['min_weight']}lb"
                            })
                    if rule.get('max_weight') and dog_weight > rule['max_weight']:
                        if rule.get('is_hard_block'):
                            has_hard_block = True
                            errors.append({
                                "dog_id": dog_id,
                                "dog_name": dog.get('name'),
                                "rule": rule['name'],
                                "message": f"Weight {dog_weight}lb exceeds maximum {rule['max_weight']}lb"
                            })
            
            elif rule_type == 'behavior':
                if rule.get('blocks_aggressive') and dog.get('incidents_of_aggression'):
                    if rule.get('is_hard_block'):
                        has_hard_block = True
                        errors.append({
                            "dog_id": dog_id,
                            "dog_name": dog.get('name'),
                            "rule": rule['name'],
                            "message": "Dog has history of aggression"
                        })
        
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        eligibility_results.append({
            "dog_id": dog_id,
            "dog_name": dog.get('name'),
            "is_eligible": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "missing_vaccines": missing_vaccines
        })
    
    # Calculate pricing
    base_price = 50.0  # Base price per dog per night
    subtotal = base_price * nights * len(dog_ids)
    
    # Add bath fee if requested
    bath_fee = 0
    if bath_before_pickup:
        bath_fee = 25.0 * len(dog_ids)  # $25 per dog
        subtotal += bath_fee
    
    # Apply coupon if provided
    discount_amount = 0
    coupon_data = None
    if coupon_code:
        coupon = await db.coupon_codes.find_one({"code": coupon_code.upper(), "is_active": True}, {"_id": 0})
        if coupon:
            discount_type = coupon.get('discount_type')
            discount_value = coupon.get('discount_value', 0)
            if discount_type == 'percentage':
                discount_amount = subtotal * (discount_value / 100)
            elif discount_type == 'flat_amount':
                discount_amount = min(discount_value, subtotal)
            coupon_data = {
                "coupon_id": coupon['id'],
                "code": coupon['code'],
                "discount_amount": round(discount_amount, 2)
            }
    
    total_price = subtotal - discount_amount
    
    # Determine booking status based on eligibility
    requires_approval = has_hard_block
    booking_status = "pending_approval" if requires_approval else "confirmed"
    
    # Create booking document
    booking_id = str(uuid.uuid4())
    household_id = user.household_id or user.id
    
    # Get customer info
    customer = await db.users.find_one({"id": user.id}, {"_id": 0})
    
    booking_doc = {
        "id": booking_id,
        "household_id": household_id,
        "customer_id": user.id,
        "customer_name": customer.get('full_name', 'Unknown'),
        "customer_email": customer.get('email', ''),
        "customer_phone": customer.get('phone'),
        "dog_ids": dog_ids,
        "location_id": location_id,
        "kennel_id": kennel_id,
        "check_in_date": check_in_date.isoformat(),
        "check_out_date": check_out_date.isoformat(),
        "check_in_slot_id": check_in_slot_id,
        "check_out_slot_id": check_out_slot_id,
        "nights": nights,
        "status": booking_status,
        "accommodation_type": "room",
        "base_price": base_price,
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "total_price": round(total_price, 2),
        "coupon_data": coupon_data,
        "bath_before_pickup": bath_before_pickup,
        "bath_day": bath_day if bath_before_pickup else None,
        "bath_fee": bath_fee,
        "bath_scheduled": bath_before_pickup,
        "bath_completed": False,
        "requires_approval": requires_approval,
        "approval_reason": "Eligibility check failed" if requires_approval else None,
        "eligibility_errors": all_errors,
        "eligibility_warnings": all_warnings,
        "approved_by": None,
        "approved_at": None,
        "notes": notes,
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.id
    }
    
    await db.bookings.insert_one(booking_doc)
    
    # If kennel was assigned, mark it as reserved
    if kennel_id and not requires_approval:
        await db.kennels.update_one(
            {"id": kennel_id},
            {"$set": {"status": "reserved", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    # Get dog names for notifications
    dogs_for_notif = await db.dogs.find({"id": {"$in": dog_ids}}, {"_id": 0, "name": 1}).to_list(len(dog_ids))
    dog_names = [d['name'] for d in dogs_for_notif]
    
    # Send notifications if booking was auto-blocked
    if requires_approval:
        # Notify customer
        await notify_booking_auto_blocked(
            db=db,
            customer_id=user.id,
            customer_name=customer.get('full_name', 'Customer'),
            booking_id=booking_id,
            dog_names=dog_names,
            errors=all_errors
        )
        
        # Notify all admins
        admin_users = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(100)
        admin_ids = [a['id'] for a in admin_users]
        if admin_ids:
            await notify_admin_pending_approval(
                db=db,
                admin_ids=admin_ids,
                booking_id=booking_id,
                customer_name=customer.get('full_name', 'Customer'),
                dog_names=dog_names,
                error_count=len(all_errors)
            )
    
    # Remove _id from response
    booking_doc.pop('_id', None)
    
    return {
        "booking": booking_doc,
        "eligibility_results": eligibility_results,
        "requires_approval": requires_approval,
        "auto_blocked": requires_approval,
        "message": "Booking requires admin approval" if requires_approval else "Booking confirmed"
    }


@router.get("/bookings/pending-approval")
async def get_pending_approval_bookings(
    location_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all bookings pending admin approval"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {"requires_approval": True, "status": "pending_approval"}
    if location_id:
        query["location_id"] = location_id
    
    bookings = await db.bookings.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Enrich with dog names
    for booking in bookings:
        dog_ids = booking.get('dog_ids', [])
        dogs = await db.dogs.find({"id": {"$in": dog_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(len(dog_ids))
        booking['dog_names'] = [d['name'] for d in dogs]
    
    return bookings


@router.post("/bookings/{booking_id}/approve")
async def approve_booking(
    booking_id: str,
    kennel_id: Optional[str] = None,
    notes: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Approve a pending booking (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get('status') != 'pending_approval':
        raise HTTPException(status_code=400, detail="Booking is not pending approval")
    
    update_data = {
        "status": "confirmed",
        "requires_approval": False,
        "approved_by": user.id,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "admin_notes": notes,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if kennel_id:
        update_data["kennel_id"] = kennel_id
        # Reserve the kennel
        await db.kennels.update_one(
            {"id": kennel_id},
            {"$set": {"status": "reserved", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    return {"message": "Booking approved", "booking_id": booking_id}


@router.post("/bookings/{booking_id}/reject")
async def reject_booking(
    booking_id: str,
    reason: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Reject a pending booking (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    await db.bookings.update_one(
        {"id": booking_id},
        {"$set": {
            "status": "cancelled",
            "rejection_reason": reason,
            "rejected_by": user.id,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Booking rejected", "booking_id": booking_id}


# ==================== CHECK-IN / CHECK-OUT OPERATIONS ====================

@router.get("/operations/check-ins")
async def get_todays_check_ins(
    location_id: str,
    date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get bookings scheduled for check-in today"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    bookings = await db.bookings.find({
        "location_id": location_id,
        "status": {"$in": ["confirmed", "checked_in"]},
        "check_in_date": {"$regex": f"^{date}"}
    }, {"_id": 0}).to_list(100)
    
    result = []
    for booking in bookings:
        dog_ids = booking.get('dog_ids', [])
        dogs = await db.dogs.find({"id": {"$in": dog_ids}}, {"_id": 0}).to_list(len(dog_ids))
        
        kennel = None
        if booking.get('kennel_id'):
            kennel = await db.kennels.find_one({"id": booking['kennel_id']}, {"_id": 0})
        
        result.append({
            "booking_id": booking['id'],
            "customer_name": booking.get('customer_name', 'Unknown'),
            "customer_phone": booking.get('customer_phone'),
            "dogs": [{"id": d['id'], "name": d['name'], "breed": d.get('breed', ''), "weight": d.get('weight')} for d in dogs],
            "kennel_id": booking.get('kennel_id'),
            "kennel_name": kennel.get('name') if kennel else None,
            "check_in_date": booking['check_in_date'],
            "check_out_date": booking['check_out_date'],
            "status": booking['status'],
            "checked_in": booking['status'] == 'checked_in',
            "notes": booking.get('notes'),
            "special_needs": [d.get('medication_requirements') for d in dogs if d.get('medication_requirements')],
            "bath_scheduled": booking.get('bath_scheduled', False),
            "bath_day": booking.get('bath_day'),
            "payment_status": booking.get('payment_status', 'pending'),
            "total_price": booking.get('total_price', 0)
        })
    
    return result


@router.get("/operations/check-outs")
async def get_todays_check_outs(
    location_id: str,
    date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get bookings scheduled for check-out today"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    bookings = await db.bookings.find({
        "location_id": location_id,
        "status": {"$in": ["checked_in"]},
        "check_out_date": {"$regex": f"^{date}"}
    }, {"_id": 0}).to_list(100)
    
    result = []
    for booking in bookings:
        dog_ids = booking.get('dog_ids', [])
        dogs = await db.dogs.find({"id": {"$in": dog_ids}}, {"_id": 0}).to_list(len(dog_ids))
        
        kennel = None
        if booking.get('kennel_id'):
            kennel = await db.kennels.find_one({"id": booking['kennel_id']}, {"_id": 0})
        
        result.append({
            "booking_id": booking['id'],
            "customer_name": booking.get('customer_name', 'Unknown'),
            "customer_phone": booking.get('customer_phone'),
            "dogs": [{"id": d['id'], "name": d['name'], "breed": d.get('breed', '')} for d in dogs],
            "kennel_id": booking.get('kennel_id'),
            "kennel_name": kennel.get('name') if kennel else None,
            "check_in_date": booking['check_in_date'],
            "check_out_date": booking['check_out_date'],
            "bath_scheduled": booking.get('bath_scheduled', False),
            "bath_completed": booking.get('bath_completed', False),
            "bath_day": booking.get('bath_day'),
            "payment_status": booking.get('payment_status', 'pending'),
            "balance_due": booking.get('balance_due', booking.get('total_price', 0)),
            "total_price": booking.get('total_price', 0),
            "notes": booking.get('notes')
        })
    
    return result


@router.post("/operations/check-in/{booking_id}")
async def perform_check_in(
    booking_id: str,
    data: dict = {},
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Perform check-in for a booking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get('status') not in ['confirmed', 'pending']:
        raise HTTPException(status_code=400, detail=f"Cannot check in booking with status: {booking.get('status')}")
    
    kennel_id = data.get('kennel_id') or booking.get('kennel_id')
    check_in_notes = data.get('notes', '')
    items_received = data.get('items_received', [])  # List of items customer brought
    
    now = datetime.now(timezone.utc)
    
    # Update booking
    update_data = {
        "status": "checked_in",
        "checked_in_at": now.isoformat(),
        "checked_in_by": user.id,
        "check_in_notes": check_in_notes,
        "items_received": items_received,
        "updated_at": now.isoformat()
    }
    
    if kennel_id:
        update_data["kennel_id"] = kennel_id
        # Update kennel status to occupied
        await db.kennels.update_one(
            {"id": kennel_id},
            {"$set": {"status": "occupied", "updated_at": now.isoformat()}}
        )
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    return {
        "message": "Check-in completed",
        "booking_id": booking_id,
        "checked_in_at": now.isoformat(),
        "kennel_id": kennel_id
    }


@router.post("/operations/check-out/{booking_id}")
async def perform_check_out(
    booking_id: str,
    data: dict = {},
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Perform check-out for a booking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get('status') != 'checked_in':
        raise HTTPException(status_code=400, detail="Booking must be checked in first")
    
    # Check if bath was completed if scheduled
    if booking.get('bath_scheduled') and not booking.get('bath_completed'):
        if not data.get('skip_bath_check'):
            raise HTTPException(
                status_code=400, 
                detail="Bath scheduled but not completed. Set skip_bath_check=true to proceed anyway."
            )
    
    check_out_notes = data.get('notes', '')
    items_returned = data.get('items_returned', [])
    payment_collected = data.get('payment_collected', False)
    
    now = datetime.now(timezone.utc)
    
    # Update booking
    update_data = {
        "status": "checked_out",
        "checked_out_at": now.isoformat(),
        "checked_out_by": user.id,
        "check_out_notes": check_out_notes,
        "items_returned": items_returned,
        "updated_at": now.isoformat()
    }
    
    if payment_collected:
        update_data["payment_status"] = "paid"
        update_data["payment_collected_at"] = now.isoformat()
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    # Free up the kennel
    kennel_id = booking.get('kennel_id')
    if kennel_id:
        await db.kennels.update_one(
            {"id": kennel_id},
            {"$set": {"status": "cleaning", "updated_at": now.isoformat()}}
        )
    
    return {
        "message": "Check-out completed",
        "booking_id": booking_id,
        "checked_out_at": now.isoformat(),
        "kennel_id": kennel_id,
        "kennel_status": "cleaning"
    }


@router.post("/operations/bath/{booking_id}")
async def mark_bath_completed(
    booking_id: str,
    notes: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Mark bath as completed for a booking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if not booking.get('bath_scheduled'):
        raise HTTPException(status_code=400, detail="No bath scheduled for this booking")
    
    now = datetime.now(timezone.utc)
    
    await db.bookings.update_one(
        {"id": booking_id},
        {"$set": {
            "bath_completed": True,
            "bath_completed_at": now.isoformat(),
            "bath_completed_by": user.id,
            "bath_notes": notes,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Bath marked as completed", "booking_id": booking_id}


@router.get("/operations/baths-due")
async def get_baths_due_today(
    location_id: str,
    date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all baths due today (checkout day or day before)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    target_date = datetime.strptime(date, "%Y-%m-%d")
    next_date = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Find bookings where:
    # 1. Bath scheduled and not completed
    # 2. bath_day is 'checkout' and checkout is today, OR
    # 3. bath_day is 'day_before' and checkout is tomorrow
    bookings = await db.bookings.find({
        "location_id": location_id,
        "status": "checked_in",
        "bath_scheduled": True,
        "bath_completed": {"$ne": True},
        "$or": [
            {"bath_day": "checkout", "check_out_date": {"$regex": f"^{date}"}},
            {"bath_day": "day_before", "check_out_date": {"$regex": f"^{next_date}"}}
        ]
    }, {"_id": 0}).to_list(100)
    
    result = []
    for booking in bookings:
        dog_ids = booking.get('dog_ids', [])
        dogs = await db.dogs.find({"id": {"$in": dog_ids}}, {"_id": 0, "id": 1, "name": 1, "breed": 1}).to_list(len(dog_ids))
        
        kennel = None
        if booking.get('kennel_id'):
            kennel = await db.kennels.find_one({"id": booking['kennel_id']}, {"_id": 0, "name": 1})
        
        result.append({
            "booking_id": booking['id'],
            "customer_name": booking.get('customer_name'),
            "dogs": [{"id": d['id'], "name": d['name'], "breed": d.get('breed', '')} for d in dogs],
            "kennel_name": kennel.get('name') if kennel else None,
            "check_out_date": booking['check_out_date'],
            "bath_day": booking.get('bath_day'),
            "bath_fee": booking.get('bath_fee', 0)
        })
    
    return result
