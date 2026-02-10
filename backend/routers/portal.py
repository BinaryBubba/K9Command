"""
Portal Router - K9Command
Handles customer portal - service history, upcoming bookings, invoices, rebooking
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timezone
import uuid

from models import UserRole
from auth import get_current_user

router = APIRouter(prefix="/api/k9", tags=["Customer Portal"])
security = HTTPBearer()


def get_db():
    """Get database connection"""
    from server import db
    return db


@router.get("/portal/service-history")
async def get_service_history(
    limit: int = 50,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get customer's service history"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    bookings = await db.bookings.find(
        {
            "$or": [
                {"customer_id": user.id},
                {"household_id": user.household_id}
            ],
            "status": {"$in": ["checked_out", "completed"]}
        },
        {"_id": 0}
    ).sort("check_out_date", -1).limit(limit).to_list(limit)
    
    enriched = []
    for booking in bookings:
        dogs = []
        for dog_id in booking.get("dog_ids", []):
            dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1, "breed": 1})
            if dog:
                dogs.append(dog)
        
        kennel = None
        if booking.get("kennel_id"):
            kennel = await db.kennels.find_one({"id": booking["kennel_id"]}, {"_id": 0, "name": 1, "kennel_type": 1})
        
        enriched.append({
            **booking,
            "dogs": dogs,
            "kennel": kennel
        })
    
    return {"history": enriched, "count": len(enriched)}


@router.get("/portal/upcoming")
async def get_upcoming_bookings(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get customer's upcoming bookings"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    now = datetime.now(timezone.utc).isoformat()
    
    bookings = await db.bookings.find(
        {
            "$or": [
                {"customer_id": user.id},
                {"household_id": user.household_id}
            ],
            "status": {"$in": ["confirmed", "pending_approval", "checked_in"]},
            "check_out_date": {"$gte": now}
        },
        {"_id": 0}
    ).sort("check_in_date", 1).to_list(20)
    
    enriched = []
    for booking in bookings:
        dogs = []
        for dog_id in booking.get("dog_ids", []):
            dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1, "breed": 1})
            if dog:
                dogs.append(dog)
        
        kennel = None
        if booking.get("kennel_id"):
            kennel = await db.kennels.find_one({"id": booking["kennel_id"]}, {"_id": 0, "name": 1, "kennel_type": 1})
        
        enriched.append({
            **booking,
            "dogs": dogs,
            "kennel": kennel
        })
    
    return {"upcoming": enriched, "count": len(enriched)}


@router.post("/portal/rebook/{booking_id}")
async def rebook_from_history(
    booking_id: str,
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Rebook based on a previous booking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    original = await db.bookings.find_one(
        {
            "id": booking_id,
            "$or": [
                {"customer_id": user.id},
                {"household_id": user.household_id}
            ]
        },
        {"_id": 0}
    )
    
    if not original:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    new_check_in = data.get("check_in_date")
    new_check_out = data.get("check_out_date")
    
    if not new_check_in or not new_check_out:
        raise HTTPException(status_code=400, detail="check_in_date and check_out_date required")
    
    new_booking_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    new_booking = {
        "id": new_booking_id,
        "customer_id": user.id,
        "household_id": user.household_id,
        "dog_ids": original.get("dog_ids", []),
        "kennel_id": None,
        "check_in_date": new_check_in,
        "check_out_date": new_check_out,
        "check_in_slot_id": original.get("check_in_slot_id"),
        "check_out_slot_id": original.get("check_out_slot_id"),
        "status": "confirmed",
        "add_ons": original.get("add_ons", []),
        "notes": original.get("notes", ""),
        "rebooked_from": booking_id,
        "created_at": now,
        "updated_at": now
    }
    
    await db.bookings.insert_one(new_booking)
    new_booking.pop('_id', None)
    
    return {"message": "Booking created", "booking": new_booking}


@router.get("/portal/invoices")
async def get_invoices(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get customer's invoices"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    invoices = await db.invoices.find(
        {
            "$or": [
                {"customer_id": user.id},
                {"household_id": user.household_id}
            ]
        },
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    if not invoices:
        completed_bookings = await db.bookings.find(
            {
                "$or": [
                    {"customer_id": user.id},
                    {"household_id": user.household_id}
                ],
                "status": {"$in": ["checked_out", "completed"]}
            },
            {"_id": 0}
        ).sort("check_out_date", -1).limit(10).to_list(10)
        
        for booking in completed_bookings:
            dogs = []
            for dog_id in booking.get("dog_ids", []):
                dog = await db.dogs.find_one({"id": dog_id}, {"_id": 0, "name": 1})
                if dog:
                    dogs.append(dog["name"])
            
            nights = 1
            try:
                ci = datetime.fromisoformat(booking["check_in_date"].replace('Z', '+00:00'))
                co = datetime.fromisoformat(booking["check_out_date"].replace('Z', '+00:00'))
                nights = max(1, (co - ci).days)
            except:
                pass
            
            base_rate = 5500
            total = base_rate * nights * len(booking.get("dog_ids", []))
            
            for addon in booking.get("add_ons", []):
                if addon.get("type") == "bath":
                    total += 2500
            
            invoices.append({
                "id": f"inv-{booking['id'][:8]}",
                "booking_id": booking["id"],
                "description": f"Boarding for {', '.join(dogs)} ({nights} nights)",
                "amount_cents": total,
                "status": "paid",
                "created_at": booking.get("check_out_date") or booking.get("created_at"),
                "paid_at": booking.get("check_out_date")
            })
    
    return {"invoices": invoices, "count": len(invoices)}
