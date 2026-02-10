"""
Operations Router - K9Command
Handles check-in/out, daily operations, dogs on site, baths
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid

from models import (
    UserRole,
    KennelStatus,
    DogOnSite, DailyOperationsSummary,
)
from auth import get_current_user
from services.push_notifications import send_booking_status_push

router = APIRouter(prefix="/api/k9", tags=["Operations"])
security = HTTPBearer()


def get_db():
    """Get database connection"""
    from server import db
    return db


# ==================== DOGS ON SITE ====================

@router.get("/operations/dogs-on-site")
async def get_dogs_on_site(
    location_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all dogs currently on site"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    query = {
        "status": {"$in": ["confirmed", "checked_in"]},
        "check_in_date": {"$lte": datetime.now(timezone.utc).isoformat()},
        "check_out_date": {"$gte": datetime.now(timezone.utc).isoformat()}
    }
    
    bookings = await db.bookings.find(query, {"_id": 0}).to_list(200)
    
    dogs_on_site = []
    for booking in bookings:
        kennel = None
        if booking.get("kennel_id"):
            kennel = await db.kennels.find_one({"id": booking["kennel_id"]}, {"_id": 0, "name": 1, "kennel_type": 1})
        
        customer = await db.users.find_one({"id": booking.get("customer_id")}, {"_id": 0, "full_name": 1, "phone": 1})
        
        for dog_id in booking.get("dog_ids", []):
            dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0})
            if dog:
                dogs_on_site.append({
                    "dog_id": dog_id,
                    "dog_name": dog.get("name"),
                    "breed": dog.get("breed"),
                    "weight": dog.get("weight"),
                    "booking_id": booking["id"],
                    "kennel": kennel,
                    "customer": customer,
                    "check_in_date": booking["check_in_date"],
                    "check_out_date": booking["check_out_date"],
                    "status": booking["status"],
                    "add_ons": booking.get("add_ons", []),
                    "notes": booking.get("notes"),
                    "special_needs": dog.get("special_needs"),
                    "feeding_instructions": dog.get("feeding_instructions"),
                    "medication": dog.get("medication")
                })
    
    return {"dogs": dogs_on_site, "count": len(dogs_on_site)}


# ==================== DAILY SUMMARY ====================

@router.get("/operations/summary")
async def get_daily_summary(
    date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get daily operations summary"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    if date:
        target_date = datetime.fromisoformat(date.replace('Z', '+00:00')).date()
    else:
        target_date = datetime.now(timezone.utc).date()
    
    date_prefix = target_date.isoformat()
    
    check_ins = await db.bookings.count_documents({
        "check_in_date": {"$regex": f"^{date_prefix}"},
        "status": {"$in": ["confirmed", "checked_in"]}
    })
    
    check_outs = await db.bookings.count_documents({
        "check_out_date": {"$regex": f"^{date_prefix}"},
        "status": {"$in": ["confirmed", "checked_in"]}
    })
    
    on_site_query = {
        "status": {"$in": ["confirmed", "checked_in"]},
        "check_in_date": {"$lte": f"{date_prefix}T23:59:59"},
        "check_out_date": {"$gte": f"{date_prefix}T00:00:00"}
    }
    on_site_bookings = await db.bookings.find(on_site_query, {"_id": 0, "dog_ids": 1}).to_list(200)
    dogs_on_site = sum(len(b.get("dog_ids", [])) for b in on_site_bookings)
    
    pending_approval = await db.bookings.count_documents({"status": "pending_approval"})
    
    total_kennels = await db.kennels.count_documents({})
    occupied_kennels = await db.kennels.count_documents({"status": KennelStatus.OCCUPIED.value})
    
    return {
        "date": date_prefix,
        "check_ins_today": check_ins,
        "check_outs_today": check_outs,
        "dogs_on_site": dogs_on_site,
        "pending_approvals": pending_approval,
        "total_kennels": total_kennels,
        "occupied_kennels": occupied_kennels,
        "occupancy_rate": round(occupied_kennels / total_kennels * 100, 1) if total_kennels > 0 else 0
    }


# ==================== CHECK-INS ====================

@router.get("/operations/check-ins")
async def get_check_ins_today(
    date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get today's check-ins"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    if date:
        target_date = date
    else:
        target_date = datetime.now(timezone.utc).date().isoformat()
    
    bookings = await db.bookings.find({
        "check_in_date": {"$regex": f"^{target_date}"},
        "status": {"$in": ["confirmed", "pending_approval"]}
    }, {"_id": 0}).to_list(100)
    
    enriched = []
    for booking in bookings:
        customer = await db.users.find_one({"id": booking.get("customer_id")}, {"_id": 0, "full_name": 1, "phone": 1, "email": 1})
        dogs = []
        for dog_id in booking.get("dog_ids", []):
            dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0})
            if dog:
                dogs.append(dog)
        
        kennel = None
        if booking.get("kennel_id"):
            kennel = await db.kennels.find_one({"id": booking["kennel_id"]}, {"_id": 0, "name": 1, "kennel_type": 1})
        
        slot = None
        if booking.get("check_in_slot_id"):
            slot = await db.time_slots.find_one({"id": booking["check_in_slot_id"]}, {"_id": 0})
        
        enriched.append({
            **booking,
            "customer": customer,
            "dogs": dogs,
            "kennel": kennel,
            "check_in_slot": slot
        })
    
    return {"check_ins": enriched, "count": len(enriched), "date": target_date}


@router.get("/operations/check-outs")
async def get_check_outs_today(
    date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get today's check-outs"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    if date:
        target_date = date
    else:
        target_date = datetime.now(timezone.utc).date().isoformat()
    
    bookings = await db.bookings.find({
        "check_out_date": {"$regex": f"^{target_date}"},
        "status": "checked_in"
    }, {"_id": 0}).to_list(100)
    
    enriched = []
    for booking in bookings:
        customer = await db.users.find_one({"id": booking.get("customer_id")}, {"_id": 0, "full_name": 1, "phone": 1, "email": 1})
        dogs = []
        for dog_id in booking.get("dog_ids", []):
            dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0})
            if dog:
                dogs.append(dog)
        
        kennel = None
        if booking.get("kennel_id"):
            kennel = await db.kennels.find_one({"id": booking["kennel_id"]}, {"_id": 0, "name": 1})
        
        enriched.append({
            **booking,
            "customer": customer,
            "dogs": dogs,
            "kennel": kennel
        })
    
    return {"check_outs": enriched, "count": len(enriched), "date": target_date}


@router.post("/operations/check-in/{booking_id}")
async def perform_check_in(
    booking_id: str,
    data: Optional[dict] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Perform check-in for a booking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get("status") not in ["confirmed", "pending"]:
        raise HTTPException(status_code=400, detail=f"Cannot check in booking with status: {booking.get('status')}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "status": "checked_in",
        "checked_in_at": now,
        "checked_in_by": user.id,
        "updated_at": now
    }
    
    if data:
        if data.get("kennel_id"):
            update_data["kennel_id"] = data["kennel_id"]
        if data.get("notes"):
            update_data["check_in_notes"] = data["notes"]
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    kennel_id = data.get("kennel_id") if data else booking.get("kennel_id")
    if kennel_id:
        await db.kennels.update_one(
            {"id": kennel_id},
            {"$set": {"status": KennelStatus.OCCUPIED.value, "current_booking_id": booking_id}}
        )
    
    dog_names = []
    for dog_id in booking.get("dog_ids", []):
        dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
        if dog:
            dog_names.append(dog["name"])
    
    await send_booking_status_push(
        db=db,
        user_id=booking.get("customer_id"),
        status="checked_in",
        booking_id=booking_id,
        dog_names=dog_names
    )
    
    updated = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    return {"message": "Check-in complete", "booking": updated}


@router.post("/operations/check-out/{booking_id}")
async def perform_check_out(
    booking_id: str,
    data: Optional[dict] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Perform check-out for a booking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get("status") != "checked_in":
        raise HTTPException(status_code=400, detail=f"Cannot check out booking with status: {booking.get('status')}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "status": "checked_out",
        "checked_out_at": now,
        "checked_out_by": user.id,
        "updated_at": now
    }
    
    if data:
        if data.get("notes"):
            update_data["check_out_notes"] = data["notes"]
        if data.get("final_amount_cents"):
            update_data["final_amount_cents"] = data["final_amount_cents"]
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    if booking.get("kennel_id"):
        await db.kennels.update_one(
            {"id": booking["kennel_id"]},
            {"$set": {"status": KennelStatus.CLEANING.value, "current_booking_id": None}}
        )
    
    dog_names = []
    for dog_id in booking.get("dog_ids", []):
        dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
        if dog:
            dog_names.append(dog["name"])
    
    await send_booking_status_push(
        db=db,
        user_id=booking.get("customer_id"),
        status="checked_out",
        booking_id=booking_id,
        dog_names=dog_names
    )
    
    updated = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    return {"message": "Check-out complete", "booking": updated}


# ==================== BATHS ====================

@router.post("/operations/bath/{booking_id}")
async def mark_bath_complete(
    booking_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Mark bath add-on as complete for a booking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.bookings.update_one(
        {"id": booking_id},
        {"$set": {
            "bath_completed_at": now,
            "bath_completed_by": user.id,
            "updated_at": now
        }}
    )
    
    return {"message": "Bath marked complete", "booking_id": booking_id}


@router.get("/operations/baths-due")
async def get_baths_due(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get bookings with bath add-on due today"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    bookings = await db.bookings.find({
        "check_out_date": {"$regex": f"^{today}"},
        "status": "checked_in",
        "add_ons": {"$elemMatch": {"type": "bath"}},
        "bath_completed_at": None
    }, {"_id": 0}).to_list(50)
    
    enriched = []
    for booking in bookings:
        dogs = []
        for dog_id in booking.get("dog_ids", []):
            dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1, "breed": 1, "weight": 1})
            if dog:
                dogs.append(dog)
        
        kennel = None
        if booking.get("kennel_id"):
            kennel = await db.kennels.find_one({"id": booking["kennel_id"]}, {"_id": 0, "name": 1})
        
        enriched.append({
            "booking_id": booking["id"],
            "dogs": dogs,
            "kennel": kennel,
            "check_out_date": booking["check_out_date"]
        })
    
    return {"baths_due": enriched, "count": len(enriched)}
