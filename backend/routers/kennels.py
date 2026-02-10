"""
Kennels Router - K9Command
Handles kennel/run management, availability, time slots
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid

from models import (
    UserRole,
    Kennel, KennelCreate, KennelResponse, KennelType, KennelStatus,
    TimeSlot, TimeSlotCreate, TimeSlotResponse, SlotType, SlotAvailability,
)
from auth import get_current_user

router = APIRouter(prefix="/api/k9", tags=["Kennels & Slots"])
security = HTTPBearer()


def get_db():
    """Get database connection"""
    from server import db
    return db


# ==================== KENNELS / RUNS ====================

@router.get("/kennels", response_model=List[KennelResponse])
async def list_kennels(
    location_id: Optional[str] = None,
    kennel_type: Optional[KennelType] = None,
    status: Optional[KennelStatus] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List all kennels with optional filters"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {}
    if location_id:
        query["location_id"] = location_id
    if kennel_type:
        query["kennel_type"] = kennel_type.value
    if status:
        query["status"] = status.value
    
    kennels = await db.kennels.find(query, {"_id": 0}).to_list(100)
    return kennels


@router.get("/kennels/{kennel_id}", response_model=KennelResponse)
async def get_kennel(
    kennel_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a specific kennel"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    kennel = await db.kennels.find_one({"id": kennel_id}, {"_id": 0})
    if not kennel:
        raise HTTPException(status_code=404, detail="Kennel not found")
    
    return kennel


@router.post("/kennels", response_model=KennelResponse)
async def create_kennel(
    kennel: KennelCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new kennel (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    kennel_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    kennel_doc = {
        "id": kennel_id,
        **kennel.dict(),
        "status": KennelStatus.AVAILABLE.value,
        "current_booking_id": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.kennels.insert_one(kennel_doc)
    kennel_doc.pop('_id', None)
    
    return kennel_doc


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
    
    kennel = await db.kennels.find_one({"id": kennel_id})
    if not kennel:
        raise HTTPException(status_code=404, detail="Kennel not found")
    
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    updates.pop("id", None)
    updates.pop("_id", None)
    
    await db.kennels.update_one({"id": kennel_id}, {"$set": updates})
    
    updated = await db.kennels.find_one({"id": kennel_id}, {"_id": 0})
    return updated


@router.delete("/kennels/{kennel_id}")
async def delete_kennel(
    kennel_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Soft delete a kennel (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    kennel = await db.kennels.find_one({"id": kennel_id})
    if not kennel:
        raise HTTPException(status_code=404, detail="Kennel not found")
    
    await db.kennels.update_one(
        {"id": kennel_id},
        {"$set": {"status": KennelStatus.MAINTENANCE.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Kennel deactivated", "kennel_id": kennel_id}


@router.get("/kennels/availability/{location_id}")
async def get_kennel_availability(
    location_id: str,
    check_in: str,
    check_out: str,
    dog_weight: Optional[float] = None,
    kennel_type: Optional[KennelType] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get available kennels for a date range"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {
        "location_id": location_id,
        "status": {"$in": [KennelStatus.AVAILABLE.value, KennelStatus.RESERVED.value]}
    }
    
    if kennel_type:
        query["kennel_type"] = kennel_type.value
    
    kennels = await db.kennels.find(query, {"_id": 0}).to_list(100)
    
    check_in_dt = datetime.fromisoformat(check_in.replace('Z', '+00:00'))
    check_out_dt = datetime.fromisoformat(check_out.replace('Z', '+00:00'))
    
    available = []
    for kennel in kennels:
        if dog_weight:
            max_weight = kennel.get("max_weight")
            if max_weight and dog_weight > max_weight:
                continue
        
        conflicts = await db.bookings.count_documents({
            "kennel_id": kennel["id"],
            "status": {"$in": ["confirmed", "checked_in"]},
            "$or": [
                {"check_in_date": {"$lt": check_out_dt.isoformat()}, "check_out_date": {"$gt": check_in_dt.isoformat()}}
            ]
        })
        
        if conflicts == 0:
            available.append(kennel)
    
    return {"available_kennels": available, "count": len(available)}


# ==================== TIME SLOTS ====================

@router.get("/slots", response_model=List[TimeSlotResponse])
async def list_time_slots(
    location_id: Optional[str] = None,
    slot_type: Optional[SlotType] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List all time slots"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {}
    if location_id:
        query["location_id"] = location_id
    if slot_type:
        query["slot_type"] = slot_type.value
    
    slots = await db.time_slots.find(query, {"_id": 0}).to_list(100)
    return slots


@router.post("/slots", response_model=TimeSlotResponse)
async def create_time_slot(
    slot: TimeSlotCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a time slot (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    slot_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    slot_doc = {
        "id": slot_id,
        **slot.dict(),
        "created_at": now
    }
    
    await db.time_slots.insert_one(slot_doc)
    slot_doc.pop('_id', None)
    
    return slot_doc


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
    
    slot = await db.time_slots.find_one({"id": slot_id})
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")
    
    updates.pop("id", None)
    await db.time_slots.update_one({"id": slot_id}, {"$set": updates})
    
    updated = await db.time_slots.find_one({"id": slot_id}, {"_id": 0})
    return updated


@router.delete("/slots/{slot_id}")
async def delete_time_slot(
    slot_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a time slot (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.time_slots.delete_one({"id": slot_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Time slot not found")
    
    return {"message": "Time slot deleted", "slot_id": slot_id}


@router.get("/slots/availability/{location_id}")
async def get_slot_availability(
    location_id: str,
    date: str,
    slot_type: Optional[SlotType] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get slot availability for a specific date"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {"location_id": location_id, "is_active": True}
    if slot_type:
        query["slot_type"] = slot_type.value
    
    slots = await db.time_slots.find(query, {"_id": 0}).to_list(50)
    
    target_date = datetime.fromisoformat(date.replace('Z', '+00:00')).date()
    day_of_week = target_date.strftime("%A").lower()
    
    available_slots = []
    for slot in slots:
        allowed_days = slot.get("days_of_week", [])
        if allowed_days and day_of_week not in allowed_days:
            continue
        
        date_prefix = target_date.isoformat()
        
        if slot.get("slot_type") == SlotType.CHECK_IN.value:
            booking_count = await db.bookings.count_documents({
                "check_in_date": {"$regex": f"^{date_prefix}"},
                "check_in_slot_id": slot["id"],
                "status": {"$in": ["confirmed", "pending_approval"]}
            })
        else:
            booking_count = await db.bookings.count_documents({
                "check_out_date": {"$regex": f"^{date_prefix}"},
                "check_out_slot_id": slot["id"],
                "status": {"$in": ["confirmed", "checked_in"]}
            })
        
        capacity = slot.get("capacity", 10)
        remaining = max(0, capacity - booking_count)
        
        available_slots.append({
            **slot,
            "booked_count": booking_count,
            "remaining_capacity": remaining,
            "availability": SlotAvailability.AVAILABLE.value if remaining > 0 else SlotAvailability.FULL.value
        })
    
    return {"slots": available_slots, "date": date}
