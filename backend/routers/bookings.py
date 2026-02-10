"""
Bookings Router - K9Command
Handles smart booking, eligibility, coupons, waitlist, approvals
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid

from models import (
    UserRole,
    KennelStatus,
    CouponCode, CouponCodeCreate, CouponCodeResponse, CouponUsage, DiscountType,
    EligibilityRule, EligibilityRuleCreate, EligibilityRuleResponse,
    EligibilityRuleType, EligibilityCheckResult,
    WaitlistEntry, WaitlistEntryCreate, WaitlistEntryResponse, WaitlistStatus,
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
from services.push_notifications import (
    send_booking_status_push,
    send_admin_alert_push
)
from services.reminders import schedule_reminders_for_booking
from services.email import EmailService

router = APIRouter(prefix="/api/k9", tags=["Bookings"])
security = HTTPBearer()


def get_db():
    """Get database connection"""
    from server import db
    return db


# ==================== COUPONS ====================

@router.get("/coupons", response_model=List[CouponCodeResponse])
async def list_coupons(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List all coupons (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    coupons = await db.coupons.find({}, {"_id": 0}).to_list(100)
    return coupons


@router.get("/coupons/{coupon_id}", response_model=CouponCodeResponse)
async def get_coupon(
    coupon_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a specific coupon"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    coupon = await db.coupons.find_one({"id": coupon_id}, {"_id": 0})
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    return coupon


@router.post("/coupons", response_model=CouponCodeResponse)
async def create_coupon(
    coupon: CouponCodeCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new coupon (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    existing = await db.coupons.find_one({"code": coupon.code.upper()})
    if existing:
        raise HTTPException(status_code=400, detail="Coupon code already exists")
    
    coupon_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    coupon_doc = {
        "id": coupon_id,
        **coupon.dict(),
        "code": coupon.code.upper(),
        "times_used": 0,
        "created_at": now
    }
    
    await db.coupons.insert_one(coupon_doc)
    coupon_doc.pop('_id', None)
    
    return coupon_doc


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
    
    coupon = await db.coupons.find_one({"id": coupon_id})
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    updates.pop("id", None)
    updates.pop("code", None)
    
    await db.coupons.update_one({"id": coupon_id}, {"$set": updates})
    
    updated = await db.coupons.find_one({"id": coupon_id}, {"_id": 0})
    return updated


@router.delete("/coupons/{coupon_id}")
async def delete_coupon(
    coupon_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a coupon (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.coupons.delete_one({"id": coupon_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    return {"message": "Coupon deleted", "coupon_id": coupon_id}


@router.post("/coupons/validate")
async def validate_coupon(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Validate a coupon code"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    code = data.get("code", "").upper()
    subtotal_cents = data.get("subtotal_cents", 0)
    service_ids = data.get("service_ids", [])
    
    coupon = await db.coupons.find_one({"code": code, "is_active": True}, {"_id": 0})
    if not coupon:
        raise HTTPException(status_code=404, detail="Invalid or inactive coupon code")
    
    now = datetime.now(timezone.utc)
    
    if coupon.get("valid_from"):
        valid_from = datetime.fromisoformat(coupon["valid_from"].replace('Z', '+00:00'))
        if now < valid_from:
            raise HTTPException(status_code=400, detail="Coupon not yet valid")
    
    if coupon.get("valid_until"):
        valid_until = datetime.fromisoformat(coupon["valid_until"].replace('Z', '+00:00'))
        if now > valid_until:
            raise HTTPException(status_code=400, detail="Coupon has expired")
    
    if coupon.get("max_uses") and coupon.get("times_used", 0) >= coupon["max_uses"]:
        raise HTTPException(status_code=400, detail="Coupon usage limit reached")
    
    if coupon.get("min_purchase_cents") and subtotal_cents < coupon["min_purchase_cents"]:
        min_amount = coupon["min_purchase_cents"] / 100
        raise HTTPException(status_code=400, detail=f"Minimum purchase of ${min_amount:.2f} required")
    
    applicable_services = coupon.get("applicable_services", [])
    if applicable_services and service_ids:
        if not any(sid in applicable_services for sid in service_ids):
            raise HTTPException(status_code=400, detail="Coupon not valid for selected services")
    
    discount_type = coupon.get("discount_type", DiscountType.PERCENTAGE.value)
    discount_value = coupon.get("discount_value", 0)
    
    if discount_type == DiscountType.PERCENTAGE.value:
        discount_cents = int(subtotal_cents * (discount_value / 100))
    elif discount_type == DiscountType.FIXED_AMOUNT.value:
        discount_cents = min(discount_value, subtotal_cents)
    elif discount_type == DiscountType.FREE_NIGHT.value:
        discount_cents = discount_value
    else:
        discount_cents = 0
    
    max_discount = coupon.get("max_discount_cents")
    if max_discount and discount_cents > max_discount:
        discount_cents = max_discount
    
    return {
        "valid": True,
        "coupon": coupon,
        "discount_cents": discount_cents,
        "new_total_cents": max(0, subtotal_cents - discount_cents)
    }


# ==================== ELIGIBILITY RULES ====================

@router.get("/eligibility-rules", response_model=List[EligibilityRuleResponse])
async def list_eligibility_rules(
    rule_type: Optional[EligibilityRuleType] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List all eligibility rules"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    query = {}
    if rule_type:
        query["rule_type"] = rule_type.value
    
    rules = await db.eligibility_rules.find(query, {"_id": 0}).to_list(100)
    return rules


@router.post("/eligibility-rules", response_model=EligibilityRuleResponse)
async def create_eligibility_rule(
    rule: EligibilityRuleCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create an eligibility rule (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rule_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    rule_doc = {
        "id": rule_id,
        **rule.dict(),
        "created_at": now
    }
    
    await db.eligibility_rules.insert_one(rule_doc)
    rule_doc.pop('_id', None)
    
    return rule_doc


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
    
    rule = await db.eligibility_rules.find_one({"id": rule_id})
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    updates.pop("id", None)
    await db.eligibility_rules.update_one({"id": rule_id}, {"$set": updates})
    
    updated = await db.eligibility_rules.find_one({"id": rule_id}, {"_id": 0})
    return updated


@router.delete("/eligibility-rules/{rule_id}")
async def delete_eligibility_rule(
    rule_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete an eligibility rule (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.eligibility_rules.delete_one({"id": rule_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"message": "Rule deleted", "rule_id": rule_id}


async def check_dog_eligibility(db, dog_id: str, check_in_date: datetime, check_out_date: datetime) -> EligibilityCheckResult:
    """Check if a dog is eligible for boarding"""
    dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0})
    if not dog:
        return EligibilityCheckResult(
            is_eligible=False,
            dog_id=dog_id,
            errors=[{"code": "DOG_NOT_FOUND", "message": "Dog not found"}]
        )
    
    rules = await db.eligibility_rules.find({"is_active": True}, {"_id": 0}).to_list(50)
    errors = []
    warnings = []
    
    for rule in rules:
        rule_type = rule.get("rule_type")
        config = rule.get("config", {})
        
        if rule_type == EligibilityRuleType.VACCINATION.value:
            required_vaccines = config.get("required_vaccines", [])
            dog_vaccines = dog.get("vaccinations", [])
            
            for vaccine in required_vaccines:
                vax_record = next((v for v in dog_vaccines if v.get("type") == vaccine), None)
                if not vax_record:
                    if rule.get("blocking"):
                        errors.append({
                            "code": "MISSING_VACCINE",
                            "message": f"Missing required vaccination: {vaccine}",
                            "rule_id": rule["id"]
                        })
                    else:
                        warnings.append({
                            "code": "MISSING_VACCINE",
                            "message": f"Missing vaccination: {vaccine}"
                        })
                elif vax_record.get("expires_at"):
                    exp_date = datetime.fromisoformat(vax_record["expires_at"].replace('Z', '+00:00'))
                    if exp_date < check_out_date:
                        if rule.get("blocking"):
                            errors.append({
                                "code": "EXPIRED_VACCINE",
                                "message": f"Vaccination expired: {vaccine}",
                                "rule_id": rule["id"]
                            })
                        else:
                            warnings.append({
                                "code": "EXPIRED_VACCINE",
                                "message": f"Vaccination expires during stay: {vaccine}"
                            })
        
        elif rule_type == EligibilityRuleType.AGE_RESTRICTION.value:
            min_age_months = config.get("min_age_months", 0)
            max_age_months = config.get("max_age_months")
            
            birth_date_str = dog.get("birth_date")
            if birth_date_str:
                birth_date = datetime.fromisoformat(birth_date_str.replace('Z', '+00:00'))
                age_months = (check_in_date - birth_date).days / 30
                
                if age_months < min_age_months:
                    if rule.get("blocking"):
                        errors.append({
                            "code": "TOO_YOUNG",
                            "message": f"Dog must be at least {min_age_months} months old",
                            "rule_id": rule["id"]
                        })
                
                if max_age_months and age_months > max_age_months:
                    warnings.append({
                        "code": "SENIOR_DOG",
                        "message": "Senior dog - special care may be needed"
                    })
        
        elif rule_type == EligibilityRuleType.SPAY_NEUTER.value:
            if config.get("required") and not dog.get("is_spayed_neutered"):
                if rule.get("blocking"):
                    errors.append({
                        "code": "NOT_FIXED",
                        "message": "Dog must be spayed/neutered",
                        "rule_id": rule["id"]
                    })
                else:
                    warnings.append({
                        "code": "NOT_FIXED",
                        "message": "Spay/neuter recommended"
                    })
        
        elif rule_type == EligibilityRuleType.BEHAVIOR_FLAG.value:
            blocked_flags = config.get("blocked_flags", [])
            dog_flags = dog.get("behavior_flags", [])
            
            for flag in blocked_flags:
                if flag in dog_flags:
                    if rule.get("blocking"):
                        errors.append({
                            "code": "BEHAVIOR_FLAG",
                            "message": f"Behavior flag: {flag}",
                            "rule_id": rule["id"]
                        })
    
    return EligibilityCheckResult(
        is_eligible=len(errors) == 0,
        dog_id=dog_id,
        dog_name=dog.get("name"),
        errors=errors,
        warnings=warnings
    )


@router.post("/eligibility/check")
async def check_eligibility(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Check eligibility for one or more dogs"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    dog_ids = data.get("dog_ids", [])
    check_in = data.get("check_in_date")
    check_out = data.get("check_out_date")
    
    if not dog_ids or not check_in or not check_out:
        raise HTTPException(status_code=400, detail="dog_ids, check_in_date, and check_out_date required")
    
    check_in_dt = datetime.fromisoformat(check_in.replace('Z', '+00:00'))
    check_out_dt = datetime.fromisoformat(check_out.replace('Z', '+00:00'))
    
    results = []
    all_eligible = True
    
    for dog_id in dog_ids:
        result = await check_dog_eligibility(db, dog_id, check_in_dt, check_out_dt)
        results.append(result.dict())
        if not result.is_eligible:
            all_eligible = False
    
    return {
        "all_eligible": all_eligible,
        "results": results
    }


# ==================== WAITLIST ====================

@router.get("/waitlist", response_model=List[WaitlistEntryResponse])
async def list_waitlist(
    status: Optional[WaitlistStatus] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List waitlist entries"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    query = {}
    if status:
        query["status"] = status.value
    
    entries = await db.waitlist.find(query, {"_id": 0}).sort("created_at", 1).to_list(100)
    return entries


@router.post("/waitlist", response_model=WaitlistEntryResponse)
async def add_to_waitlist(
    entry: WaitlistEntryCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Add a customer to the waitlist"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    entry_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    entry_doc = {
        "id": entry_id,
        **entry.dict(),
        "customer_id": user.id,
        "household_id": user.household_id,
        "status": WaitlistStatus.WAITING.value,
        "created_at": now,
        "offer_expires_at": None,
        "offered_kennel_id": None
    }
    
    await db.waitlist.insert_one(entry_doc)
    entry_doc.pop('_id', None)
    
    return entry_doc


@router.post("/waitlist/{entry_id}/offer")
async def offer_spot_to_waitlist(
    entry_id: str,
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Offer a spot to a waitlist entry (staff/admin)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    entry = await db.waitlist.find_one({"id": entry_id})
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    
    kennel_id = data.get("kennel_id")
    hours_to_respond = data.get("hours_to_respond", 24)
    
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours_to_respond)
    
    await db.waitlist.update_one(
        {"id": entry_id},
        {"$set": {
            "status": WaitlistStatus.OFFERED.value,
            "offered_kennel_id": kennel_id,
            "offer_expires_at": expires_at.isoformat()
        }}
    )
    
    updated = await db.waitlist.find_one({"id": entry_id}, {"_id": 0})
    return {"message": "Spot offered", "entry": updated}


@router.post("/waitlist/{entry_id}/respond")
async def respond_to_waitlist_offer(
    entry_id: str,
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Respond to a waitlist offer (accept/decline)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    entry = await db.waitlist.find_one({"id": entry_id})
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    
    if entry.get("customer_id") != user.id and entry.get("household_id") != user.household_id:
        if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    accept = data.get("accept", False)
    
    if accept:
        new_status = WaitlistStatus.ACCEPTED.value
    else:
        new_status = WaitlistStatus.DECLINED.value
    
    await db.waitlist.update_one(
        {"id": entry_id},
        {"$set": {"status": new_status}}
    )
    
    updated = await db.waitlist.find_one({"id": entry_id}, {"_id": 0})
    return {"message": f"Offer {'accepted' if accept else 'declined'}", "entry": updated}


# ==================== SMART BOOKING ====================

@router.post("/bookings/smart")
async def create_smart_booking(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a booking with smart eligibility checking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    dog_ids = data.get("dog_ids", [])
    check_in = data.get("check_in_date")
    check_out = data.get("check_out_date")
    kennel_id = data.get("kennel_id")
    check_in_slot_id = data.get("check_in_slot_id")
    check_out_slot_id = data.get("check_out_slot_id")
    add_ons = data.get("add_ons", [])
    notes = data.get("notes", "")
    
    if not dog_ids or not check_in or not check_out:
        raise HTTPException(status_code=400, detail="dog_ids, check_in_date, and check_out_date required")
    
    check_in_dt = datetime.fromisoformat(check_in.replace('Z', '+00:00'))
    check_out_dt = datetime.fromisoformat(check_out.replace('Z', '+00:00'))
    
    eligibility_results = []
    requires_approval = False
    blocking_errors = []
    
    for dog_id in dog_ids:
        result = await check_dog_eligibility(db, dog_id, check_in_dt, check_out_dt)
        eligibility_results.append(result.dict())
        if not result.is_eligible:
            requires_approval = True
            blocking_errors.extend([
                {"dog_id": dog_id, "dog_name": result.dog_name, **e} 
                for e in result.errors
            ])
    
    booking_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    booking_status = "pending_approval" if requires_approval else "confirmed"
    
    dog_names = []
    for dog_id in dog_ids:
        dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
        if dog:
            dog_names.append(dog["name"])
    
    booking_doc = {
        "id": booking_id,
        "customer_id": user.id,
        "household_id": user.household_id,
        "dog_ids": dog_ids,
        "kennel_id": kennel_id,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "check_in_slot_id": check_in_slot_id,
        "check_out_slot_id": check_out_slot_id,
        "status": booking_status,
        "add_ons": add_ons,
        "notes": notes,
        "eligibility_errors": blocking_errors if requires_approval else [],
        "approved_by": None,
        "approved_at": None,
        "checked_in_at": None,
        "checked_out_at": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.bookings.insert_one(booking_doc)
    
    if kennel_id and not requires_approval:
        await db.kennels.update_one(
            {"id": kennel_id},
            {"$set": {"status": KennelStatus.RESERVED.value, "current_booking_id": booking_id}}
        )
    
    if requires_approval:
        await notify_booking_auto_blocked(
            db=db,
            customer_id=user.id,
            customer_name=user.full_name,
            booking_id=booking_id,
            dog_names=dog_names,
            errors=blocking_errors
        )
        
        admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(10)
        admin_ids = [a["id"] for a in admins]
        
        if admin_ids:
            await notify_admin_pending_approval(
                db=db,
                admin_ids=admin_ids,
                booking_id=booking_id,
                customer_name=user.full_name,
                dog_names=dog_names,
                error_count=len(blocking_errors)
            )
            
            await send_admin_alert_push(
                db=db,
                admin_ids=admin_ids,
                title="New Booking Needs Approval",
                body=f"{user.full_name}'s booking for {', '.join(dog_names)} requires review",
                action_url="/admin/booking-approvals",
                data={"booking_id": booking_id}
            )
        
        await send_booking_status_push(
            db=db,
            user_id=user.id,
            status="pending_approval",
            booking_id=booking_id,
            dog_names=dog_names
        )
    else:
        await send_booking_status_push(
            db=db,
            user_id=user.id,
            status="confirmed",
            booking_id=booking_id,
            dog_names=dog_names
        )
        
        try:
            await schedule_reminders_for_booking(db, booking_doc, dog_names)
        except Exception as e:
            print(f"Failed to schedule reminders: {e}")
    
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
    
    query = {"status": "pending_approval"}
    if location_id:
        query["location_id"] = location_id
    
    bookings = await db.bookings.find(query, {"_id": 0}).sort("created_at", 1).to_list(100)
    
    enriched = []
    for booking in bookings:
        customer = await db.users.find_one({"id": booking.get("customer_id")}, {"_id": 0, "full_name": 1, "email": 1})
        dogs = []
        for dog_id in booking.get("dog_ids", []):
            dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1, "breed": 1})
            if dog:
                dogs.append(dog)
        
        enriched.append({
            **booking,
            "customer": customer,
            "dogs": dogs
        })
    
    return {"bookings": enriched, "count": len(enriched)}


@router.post("/bookings/{booking_id}/approve")
async def approve_booking(
    booking_id: str,
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
    
    if booking.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="Booking is not pending approval")
    
    update_data = {
        "status": "confirmed",
        "eligibility_errors": [],
        "approved_by": user.id,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    if booking.get("kennel_id"):
        await db.kennels.update_one(
            {"id": booking["kennel_id"]},
            {"$set": {"status": KennelStatus.RESERVED.value, "current_booking_id": booking_id}}
        )
    
    dog_names = []
    for dog_id in booking.get("dog_ids", []):
        dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
        if dog:
            dog_names.append(dog["name"])
    
    await notify_booking_approved(
        db=db,
        customer_id=booking.get("customer_id"),
        booking_id=booking_id,
        check_in_date=booking.get("check_in_date", "")[:10],
        dog_names=dog_names
    )
    
    await send_booking_status_push(
        db=db,
        user_id=booking.get("customer_id"),
        status="approved",
        booking_id=booking_id,
        dog_names=dog_names
    )
    
    try:
        await schedule_reminders_for_booking(db, booking, dog_names)
    except Exception as e:
        print(f"Failed to schedule reminders: {e}")
    
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
            "status": "rejected",
            "rejection_reason": reason,
            "rejected_by": user.id,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    dog_names = []
    for dog_id in booking.get("dog_ids", []):
        dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
        if dog:
            dog_names.append(dog["name"])
    
    await notify_booking_rejected(
        db=db,
        customer_id=booking.get("customer_id"),
        booking_id=booking_id,
        reason=reason,
        dog_names=dog_names
    )
    
    await send_booking_status_push(
        db=db,
        user_id=booking.get("customer_id"),
        status="rejected",
        booking_id=booking_id,
        dog_names=dog_names,
        extra_info=reason
    )
    
    return {"message": "Booking rejected", "booking_id": booking_id}
