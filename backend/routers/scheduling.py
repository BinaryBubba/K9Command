"""
Scheduling Router - Connecteam Parity Phase 2
Handles shift templates, scheduled shifts, shift swaps, and kiosk mode
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import secrets
import hashlib

from models import (
    UserRole,
    # Shift Templates
    ShiftTemplate, ShiftTemplateCreate, ShiftTemplateResponse,
    # Shift Swaps
    ShiftSwapRequest, ShiftSwapRequestCreate, ShiftSwapRequestResponse, ShiftSwapStatus,
    # Scheduled Shifts
    ScheduledShift, ScheduledShiftCreate, ScheduledShiftResponse,
    ShiftStatus, RecurrencePattern,
    # Kiosk
    KioskDevice, KioskDeviceCreate, KioskDeviceResponse,
    StaffKioskPin, KioskClockRequest,
    # Reports
    PlannedVsActualReport,
    # Time entries
    EnhancedTimeEntry, ClockEventSource,
    GPSRecord,
)
from auth import get_current_user

router = APIRouter(prefix="/api/scheduling", tags=["Scheduling"])
security = HTTPBearer()


def get_db():
    """Get database connection"""
    from server import db
    return db


def hash_pin(pin: str) -> str:
    """Hash a PIN for storage"""
    return hashlib.sha256(pin.encode()).hexdigest()


def verify_pin(pin: str, pin_hash: str) -> bool:
    """Verify a PIN against its hash"""
    return hash_pin(pin) == pin_hash


# ==================== SHIFT TEMPLATES ====================

@router.get("/templates", response_model=List[ShiftTemplateResponse])
async def list_shift_templates(
    location_id: Optional[str] = None,
    is_active: bool = True,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List shift templates"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {"is_active": is_active}
    if location_id:
        query["location_id"] = location_id
    
    templates = await db.shift_templates.find(query, {"_id": 0}).to_list(100)
    return [ShiftTemplateResponse(**t) for t in templates]


@router.get("/templates/{template_id}", response_model=ShiftTemplateResponse)
async def get_shift_template(
    template_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single shift template"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    template = await db.shift_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Shift template not found")
    
    return ShiftTemplateResponse(**template)


@router.post("/templates", response_model=ShiftTemplateResponse)
async def create_shift_template(
    data: ShiftTemplateCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a shift template (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    template = ShiftTemplate(**data.model_dump())
    doc = template.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.shift_templates.insert_one(doc)
    return ShiftTemplateResponse(**template.model_dump())


@router.patch("/templates/{template_id}", response_model=ShiftTemplateResponse)
async def update_shift_template(
    template_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a shift template (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.shift_templates.update_one(
        {"id": template_id},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Shift template not found")
    
    template = await db.shift_templates.find_one({"id": template_id}, {"_id": 0})
    return ShiftTemplateResponse(**template)


@router.delete("/templates/{template_id}")
async def delete_shift_template(
    template_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Deactivate a shift template (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.shift_templates.update_one(
        {"id": template_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Shift template not found")
    
    return {"message": "Shift template deactivated"}


@router.post("/templates/{template_id}/generate-shifts")
async def generate_shifts_from_template(
    template_id: str,
    start_date: str,
    end_date: str,
    staff_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Generate shifts from a template for a date range"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    template = await db.shift_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Shift template not found")
    
    # Parse dates
    start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    # Get staff info
    target_staff_id = staff_id or template.get('default_staff_id')
    if not target_staff_id:
        raise HTTPException(status_code=400, detail="No staff specified and template has no default")
    
    staff = await db.users.find_one({"id": target_staff_id}, {"_id": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Parse template times
    start_hour, start_min = map(int, template['start_time'].split(':'))
    end_hour, end_min = map(int, template['end_time'].split(':'))
    
    days_of_week = template.get('days_of_week', [0, 1, 2, 3, 4])  # Default Mon-Fri
    
    # Generate shifts
    shifts_created = []
    current = start
    while current <= end:
        if current.weekday() in days_of_week:
            shift_start = current.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
            shift_end = current.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
            
            # Handle overnight shifts
            if shift_end <= shift_start:
                shift_end += timedelta(days=1)
            
            shift = ScheduledShift(
                template_id=template_id,
                staff_id=target_staff_id,
                staff_name=staff['full_name'],
                location_id=template['location_id'],
                start_time=shift_start,
                end_time=shift_end,
                status=ShiftStatus.DRAFT,
                task_ids=template.get('task_template_ids', []),
                notes=template.get('notes'),
                color=template.get('color', '#3B82F6')
            )
            
            doc = shift.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            doc['start_time'] = doc['start_time'].isoformat()
            doc['end_time'] = doc['end_time'].isoformat()
            doc['status'] = doc['status'].value
            doc['recurrence_pattern'] = doc['recurrence_pattern'].value
            
            await db.scheduled_shifts.insert_one(doc)
            shifts_created.append(shift.id)
        
        current += timedelta(days=1)
    
    return {"message": f"Created {len(shifts_created)} shifts", "shift_ids": shifts_created}


# ==================== SCHEDULED SHIFTS ====================

@router.get("/shifts", response_model=List[ScheduledShiftResponse])
async def list_shifts(
    location_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List scheduled shifts"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {}
    
    # Staff can only see their own shifts
    if user.role == UserRole.STAFF:
        query["staff_id"] = user.id
    elif staff_id:
        query["staff_id"] = staff_id
    
    if location_id:
        query["location_id"] = location_id
    
    if start_date:
        query["start_time"] = {"$gte": start_date}
    
    if end_date:
        if "start_time" in query:
            query["start_time"]["$lte"] = end_date
        else:
            query["start_time"] = {"$lte": end_date}
    
    if status:
        query["status"] = status
    
    shifts = await db.scheduled_shifts.find(query, {"_id": 0}).sort("start_time", 1).to_list(500)
    return [ScheduledShiftResponse(**s) for s in shifts]


@router.get("/shifts/{shift_id}", response_model=ScheduledShiftResponse)
async def get_shift(
    shift_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single shift"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    shift = await db.scheduled_shifts.find_one({"id": shift_id}, {"_id": 0})
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    # Check access
    if user.role == UserRole.STAFF and shift['staff_id'] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ScheduledShiftResponse(**shift)


@router.post("/shifts", response_model=ScheduledShiftResponse)
async def create_shift(
    data: ScheduledShiftCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a scheduled shift (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get staff info
    staff = await db.users.find_one({"id": data.staff_id}, {"_id": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    shift = ScheduledShift(
        **data.model_dump(),
        staff_name=staff['full_name']
    )
    
    doc = shift.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['start_time'] = doc['start_time'].isoformat()
    doc['end_time'] = doc['end_time'].isoformat()
    doc['status'] = doc['status'].value
    doc['recurrence_pattern'] = doc['recurrence_pattern'].value
    if doc['recurrence_end_date']:
        doc['recurrence_end_date'] = doc['recurrence_end_date'].isoformat()
    
    await db.scheduled_shifts.insert_one(doc)
    
    # Generate recurring instances if needed
    if data.recurrence_pattern != RecurrencePattern.NONE and data.recurrence_end_date:
        await generate_recurring_shifts(db, shift, data.recurrence_end_date)
    
    return ScheduledShiftResponse(**shift.model_dump())


async def generate_recurring_shifts(db, parent_shift: ScheduledShift, end_date: datetime):
    """Generate recurring shift instances"""
    pattern = parent_shift.recurrence_pattern
    
    if pattern == RecurrencePattern.DAILY:
        delta = timedelta(days=1)
    elif pattern == RecurrencePattern.WEEKLY:
        delta = timedelta(weeks=1)
    elif pattern == RecurrencePattern.BIWEEKLY:
        delta = timedelta(weeks=2)
    elif pattern == RecurrencePattern.MONTHLY:
        delta = timedelta(days=30)  # Approximate
    else:
        return
    
    current_start = parent_shift.start_time + delta
    current_end = parent_shift.end_time + delta
    
    while current_start <= end_date:
        instance = ScheduledShift(
            template_id=parent_shift.template_id,
            staff_id=parent_shift.staff_id,
            staff_name=parent_shift.staff_name,
            location_id=parent_shift.location_id,
            start_time=current_start,
            end_time=current_end,
            recurrence_pattern=RecurrencePattern.NONE,
            parent_shift_id=parent_shift.id,
            status=parent_shift.status,
            task_ids=parent_shift.task_ids,
            notes=parent_shift.notes,
            color=parent_shift.color
        )
        
        doc = instance.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        doc['start_time'] = doc['start_time'].isoformat()
        doc['end_time'] = doc['end_time'].isoformat()
        doc['status'] = doc['status'].value
        doc['recurrence_pattern'] = doc['recurrence_pattern'].value
        
        await db.scheduled_shifts.insert_one(doc)
        
        current_start += delta
        current_end += delta


@router.patch("/shifts/{shift_id}", response_model=ScheduledShiftResponse)
async def update_shift(
    shift_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a shift (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Convert datetime fields
    for field in ['start_time', 'end_time', 'recurrence_end_date']:
        if field in updates and updates[field]:
            if isinstance(updates[field], datetime):
                updates[field] = updates[field].isoformat()
    
    result = await db.scheduled_shifts.update_one(
        {"id": shift_id},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    shift = await db.scheduled_shifts.find_one({"id": shift_id}, {"_id": 0})
    return ScheduledShiftResponse(**shift)


@router.delete("/shifts/{shift_id}")
async def delete_shift(
    shift_id: str,
    delete_recurring: bool = False,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete/cancel a shift (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    shift = await db.scheduled_shifts.find_one({"id": shift_id}, {"_id": 0})
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    # Cancel instead of delete to preserve history
    await db.scheduled_shifts.update_one(
        {"id": shift_id},
        {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    deleted_count = 1
    
    # Optionally delete all recurring instances
    if delete_recurring:
        result = await db.scheduled_shifts.update_many(
            {"parent_shift_id": shift_id},
            {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        deleted_count += result.modified_count
    
    return {"message": f"Cancelled {deleted_count} shift(s)"}


@router.post("/shifts/publish")
async def publish_shifts(
    shift_ids: List[str],
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Publish draft shifts (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.scheduled_shifts.update_many(
        {"id": {"$in": shift_ids}, "status": "draft"},
        {"$set": {
            "status": "published",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "published_by": user.id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify affected staff
    from automation_service import AutomationService
    automation = AutomationService(db)
    
    shifts = await db.scheduled_shifts.find({"id": {"$in": shift_ids}}, {"_id": 0}).to_list(100)
    staff_ids = list(set(s['staff_id'] for s in shifts))
    
    for staff_id in staff_ids:
        staff_shifts = [s for s in shifts if s['staff_id'] == staff_id]
        await automation.log_event(
            event_type="shift.published",
            event_source="scheduling",
            source_id=shift_ids[0] if shift_ids else None,
            user_id=staff_id,
            data={
                "shift_count": len(staff_shifts),
                "published_by": user.full_name
            }
        )
    
    return {"message": f"Published {result.modified_count} shifts"}


# ==================== SHIFT SWAP REQUESTS ====================

@router.get("/swap-requests", response_model=List[ShiftSwapRequestResponse])
async def list_swap_requests(
    status: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List shift swap requests"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {}
    
    # Staff see requests involving them
    if user.role == UserRole.STAFF:
        query["$or"] = [
            {"requesting_staff_id": user.id},
            {"target_staff_id": user.id}
        ]
    
    if status:
        query["status"] = status
    
    requests = await db.shift_swap_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [ShiftSwapRequestResponse(**r) for r in requests]


@router.post("/swap-requests", response_model=ShiftSwapRequestResponse)
async def create_swap_request(
    data: ShiftSwapRequestCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a shift swap request"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    # Verify shift exists and belongs to requesting user
    shift = await db.scheduled_shifts.find_one({"id": data.shift_id}, {"_id": 0})
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    if shift['staff_id'] != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Can only swap your own shifts")
    
    # Verify target staff exists
    target_staff = await db.users.find_one({"id": data.target_staff_id}, {"_id": 0})
    if not target_staff:
        raise HTTPException(status_code=404, detail="Target staff not found")
    
    # Check for swap shift if provided
    if data.swap_shift_id:
        swap_shift = await db.scheduled_shifts.find_one({"id": data.swap_shift_id}, {"_id": 0})
        if not swap_shift:
            raise HTTPException(status_code=404, detail="Swap shift not found")
        if swap_shift['staff_id'] != data.target_staff_id:
            raise HTTPException(status_code=400, detail="Swap shift doesn't belong to target staff")
    
    swap_request = ShiftSwapRequest(
        shift_id=data.shift_id,
        requesting_staff_id=user.id,
        requesting_staff_name=user.full_name,
        target_staff_id=data.target_staff_id,
        target_staff_name=target_staff['full_name'],
        swap_shift_id=data.swap_shift_id,
        reason=data.reason
    )
    
    doc = swap_request.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['status'] = doc['status'].value
    
    await db.shift_swap_requests.insert_one(doc)
    
    return ShiftSwapRequestResponse(**swap_request.model_dump())


@router.post("/swap-requests/{request_id}/review")
async def review_swap_request(
    request_id: str,
    action: str,  # approved, rejected
    notes: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Approve or reject a swap request (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if action not in ['approved', 'rejected']:
        raise HTTPException(status_code=400, detail="Action must be 'approved' or 'rejected'")
    
    request = await db.shift_swap_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Swap request not found")
    
    if request['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Request is not pending")
    
    await db.shift_swap_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": action,
            "reviewed_by": user.id,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_notes": notes,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # If approved, perform the swap
    if action == 'approved':
        # Update the main shift
        await db.scheduled_shifts.update_one(
            {"id": request['shift_id']},
            {"$set": {
                "staff_id": request['target_staff_id'],
                "staff_name": request['target_staff_name'],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # If there's a swap shift, update it too
        if request.get('swap_shift_id'):
            await db.scheduled_shifts.update_one(
                {"id": request['swap_shift_id']},
                {"$set": {
                    "staff_id": request['requesting_staff_id'],
                    "staff_name": request['requesting_staff_name'],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
    
    return {"message": f"Swap request {action}"}


# ==================== KIOSK MODE ====================

@router.post("/kiosk/devices", response_model=KioskDeviceResponse)
async def register_kiosk_device(
    data: KioskDeviceCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Register a new kiosk device (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Generate unique device code
    device_code = secrets.token_urlsafe(16)
    
    device = KioskDevice(
        name=data.name,
        location_id=data.location_id,
        device_code=device_code
    )
    
    doc = device.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.kiosk_devices.insert_one(doc)
    
    return KioskDeviceResponse(**device.model_dump())


@router.get("/kiosk/devices", response_model=List[KioskDeviceResponse])
async def list_kiosk_devices(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List kiosk devices (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    devices = await db.kiosk_devices.find({"is_active": True}, {"_id": 0}).to_list(100)
    return [KioskDeviceResponse(**d) for d in devices]


@router.post("/kiosk/staff/{staff_id}/set-pin")
async def set_staff_kiosk_pin(
    staff_id: str,
    pin: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Set or update staff kiosk PIN (admin or self)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    # Admin can set anyone's PIN, staff can only set their own
    if user.role != UserRole.ADMIN and user.id != staff_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate PIN format (4-6 digits)
    if not pin.isdigit() or len(pin) < 4 or len(pin) > 6:
        raise HTTPException(status_code=400, detail="PIN must be 4-6 digits")
    
    pin_hash = hash_pin(pin)
    
    # Upsert the PIN record
    await db.staff_kiosk_pins.update_one(
        {"staff_id": staff_id},
        {"$set": {
            "staff_id": staff_id,
            "pin_hash": pin_hash,
            "is_active": True,
            "failed_attempts": 0,
            "locked_until": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"message": "PIN set successfully"}


@router.post("/kiosk/clock")
async def kiosk_clock_action(data: KioskClockRequest):
    """Perform clock action from kiosk (no auth required, uses device code + PIN)"""
    db = get_db()
    
    # Verify kiosk device
    device = await db.kiosk_devices.find_one({
        "device_code": data.device_code,
        "is_active": True
    }, {"_id": 0})
    
    if not device:
        raise HTTPException(status_code=401, detail="Invalid or inactive kiosk device")
    
    # Find staff by PIN
    staff_pins = await db.staff_kiosk_pins.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    staff_id = None
    for pin_record in staff_pins:
        # Check if locked
        if pin_record.get('locked_until'):
            locked_until = datetime.fromisoformat(pin_record['locked_until'])
            if locked_until > datetime.now(timezone.utc):
                continue
        
        if verify_pin(data.staff_pin, pin_record['pin_hash']):
            staff_id = pin_record['staff_id']
            # Reset failed attempts on success
            await db.staff_kiosk_pins.update_one(
                {"staff_id": staff_id},
                {"$set": {"failed_attempts": 0}}
            )
            break
    
    if not staff_id:
        # Increment failed attempts for all matching PINs (can't know which one was tried)
        raise HTTPException(status_code=401, detail="Invalid PIN")
    
    # Get staff info
    staff = await db.users.find_one({"id": staff_id}, {"_id": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Update kiosk last activity
    await db.kiosk_devices.update_one(
        {"device_code": data.device_code},
        {"$set": {"last_activity": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Perform the action
    if data.action == "clock_in":
        # Check for existing open entry
        existing = await db.enhanced_time_entries.find_one({
            "staff_id": staff_id,
            "clock_out": None
        }, {"_id": 0})
        
        if existing:
            raise HTTPException(status_code=400, detail="Already clocked in")
        
        # Record GPS if provided
        gps_id = None
        if data.latitude and data.longitude:
            gps_record = GPSRecord(
                staff_id=staff_id,
                latitude=data.latitude,
                longitude=data.longitude,
                accuracy=0,
                source="kiosk",
                event_type="clock_in"
            )
            gps_doc = gps_record.model_dump()
            gps_doc['timestamp'] = gps_doc['timestamp'].isoformat()
            gps_doc['created_at'] = gps_doc['created_at'].isoformat()
            gps_doc['updated_at'] = gps_doc['updated_at'].isoformat()
            await db.gps_records.insert_one(gps_doc)
            gps_id = gps_record.id
        
        entry = EnhancedTimeEntry(
            staff_id=staff_id,
            staff_name=staff['full_name'],
            location_id=device['location_id'],
            clock_in=datetime.now(timezone.utc),
            clock_in_gps_id=gps_id,
            clock_in_source=ClockEventSource.KIOSK
        )
        
        doc = entry.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        doc['clock_in'] = doc['clock_in'].isoformat()
        doc['clock_in_source'] = doc['clock_in_source'].value
        
        await db.enhanced_time_entries.insert_one(doc)
        
        return {
            "message": f"Welcome, {staff['full_name']}! Clocked in at {entry.clock_in.strftime('%I:%M %p')}",
            "staff_name": staff['full_name'],
            "action": "clock_in",
            "time": entry.clock_in.isoformat()
        }
    
    elif data.action == "clock_out":
        entry = await db.enhanced_time_entries.find_one({
            "staff_id": staff_id,
            "clock_out": None
        }, {"_id": 0})
        
        if not entry:
            raise HTTPException(status_code=400, detail="Not clocked in")
        
        clock_out_time = datetime.now(timezone.utc)
        
        # Calculate hours
        clock_in = datetime.fromisoformat(entry['clock_in']) if isinstance(entry['clock_in'], str) else entry['clock_in']
        total_hours = (clock_out_time - clock_in).total_seconds() / 3600
        
        await db.enhanced_time_entries.update_one(
            {"id": entry['id']},
            {"$set": {
                "clock_out": clock_out_time.isoformat(),
                "clock_out_source": "kiosk",
                "regular_hours": round(total_hours, 2),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "message": f"Goodbye, {staff['full_name']}! Worked {total_hours:.1f} hours",
            "staff_name": staff['full_name'],
            "action": "clock_out",
            "time": clock_out_time.isoformat(),
            "hours_worked": round(total_hours, 2)
        }
    
    elif data.action == "break_start":
        entry = await db.enhanced_time_entries.find_one({
            "staff_id": staff_id,
            "clock_out": None
        }, {"_id": 0})
        
        if not entry:
            raise HTTPException(status_code=400, detail="Not clocked in")
        
        # Check for active break
        active_break = await db.break_entries.find_one({
            "time_entry_id": entry['id'],
            "end_time": None
        }, {"_id": 0})
        
        if active_break:
            raise HTTPException(status_code=400, detail="Break already in progress")
        
        from models import BreakEntry, BreakType
        break_entry = BreakEntry(
            time_entry_id=entry['id'],
            staff_id=staff_id,
            break_type=BreakType.REST,
            start_time=datetime.now(timezone.utc)
        )
        
        doc = break_entry.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        doc['start_time'] = doc['start_time'].isoformat()
        doc['break_type'] = doc['break_type'].value
        
        await db.break_entries.insert_one(doc)
        
        return {
            "message": f"Break started for {staff['full_name']}",
            "staff_name": staff['full_name'],
            "action": "break_start",
            "time": break_entry.start_time.isoformat()
        }
    
    elif data.action == "break_end":
        entry = await db.enhanced_time_entries.find_one({
            "staff_id": staff_id,
            "clock_out": None
        }, {"_id": 0})
        
        if not entry:
            raise HTTPException(status_code=400, detail="Not clocked in")
        
        active_break = await db.break_entries.find_one({
            "time_entry_id": entry['id'],
            "end_time": None
        }, {"_id": 0})
        
        if not active_break:
            raise HTTPException(status_code=400, detail="No active break")
        
        end_time = datetime.now(timezone.utc)
        start_time = datetime.fromisoformat(active_break['start_time']) if isinstance(active_break['start_time'], str) else active_break['start_time']
        duration = int((end_time - start_time).total_seconds() / 60)
        
        await db.break_entries.update_one(
            {"id": active_break['id']},
            {"$set": {
                "end_time": end_time.isoformat(),
                "duration_minutes": duration,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "message": f"Break ended for {staff['full_name']} ({duration} minutes)",
            "staff_name": staff['full_name'],
            "action": "break_end",
            "time": end_time.isoformat(),
            "duration_minutes": duration
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")


@router.get("/kiosk/{device_code}/status")
async def get_kiosk_status(device_code: str):
    """Get kiosk status and current staff on site (public endpoint)"""
    db = get_db()
    
    device = await db.kiosk_devices.find_one({
        "device_code": device_code,
        "is_active": True
    }, {"_id": 0})
    
    if not device:
        raise HTTPException(status_code=404, detail="Kiosk not found")
    
    # Get staff currently clocked in at this location
    active_entries = await db.enhanced_time_entries.find({
        "location_id": device['location_id'],
        "clock_out": None
    }, {"_id": 0}).to_list(100)
    
    staff_on_site = [
        {"staff_name": e['staff_name'], "clock_in": e['clock_in']}
        for e in active_entries
    ]
    
    return {
        "device_name": device['name'],
        "location_id": device['location_id'],
        "staff_on_site": staff_on_site,
        "staff_count": len(staff_on_site),
        "current_time": datetime.now(timezone.utc).isoformat()
    }


# ==================== REPORTS ====================

@router.get("/reports/planned-vs-actual", response_model=List[PlannedVsActualReport])
async def get_planned_vs_actual_report(
    start_date: str,
    end_date: str,
    staff_id: Optional[str] = None,
    location_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get planned vs actual hours report"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Build queries
    shift_query = {
        "start_time": {"$gte": start_date, "$lte": end_date},
        "status": {"$ne": "cancelled"}
    }
    entry_query = {
        "clock_in": {"$gte": start_date, "$lte": end_date}
    }
    
    if staff_id:
        shift_query["staff_id"] = staff_id
        entry_query["staff_id"] = staff_id
    
    if location_id:
        shift_query["location_id"] = location_id
        entry_query["location_id"] = location_id
    
    # Get shifts and entries
    shifts = await db.scheduled_shifts.find(shift_query, {"_id": 0}).to_list(5000)
    entries = await db.enhanced_time_entries.find(entry_query, {"_id": 0}).to_list(5000)
    
    # Group by staff
    staff_data = {}
    
    for shift in shifts:
        sid = shift['staff_id']
        if sid not in staff_data:
            staff_data[sid] = {
                "staff_id": sid,
                "staff_name": shift.get('staff_name', 'Unknown'),
                "shifts": [],
                "entries": []
            }
        staff_data[sid]['shifts'].append(shift)
    
    for entry in entries:
        sid = entry['staff_id']
        if sid not in staff_data:
            staff_data[sid] = {
                "staff_id": sid,
                "staff_name": entry.get('staff_name', 'Unknown'),
                "shifts": [],
                "entries": []
            }
        staff_data[sid]['entries'].append(entry)
    
    # Calculate reports
    reports = []
    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    for sid, data in staff_data.items():
        planned_hours = 0
        for shift in data['shifts']:
            shift_start = datetime.fromisoformat(shift['start_time']) if isinstance(shift['start_time'], str) else shift['start_time']
            shift_end = datetime.fromisoformat(shift['end_time']) if isinstance(shift['end_time'], str) else shift['end_time']
            planned_hours += (shift_end - shift_start).total_seconds() / 3600
        
        actual_hours = sum(e.get('regular_hours', 0) + e.get('overtime_hours', 0) for e in data['entries'])
        
        variance = actual_hours - planned_hours
        variance_pct = (variance / planned_hours * 100) if planned_hours > 0 else 0
        
        # Count issues
        shift_ids = [s['id'] for s in data['shifts']]
        entries_with_shift = [e for e in data['entries'] if e.get('shift_id') in shift_ids]
        
        report = PlannedVsActualReport(
            staff_id=sid,
            staff_name=data['staff_name'],
            period_start=start_dt,
            period_end=end_dt,
            planned_shifts=len(data['shifts']),
            planned_hours=round(planned_hours, 2),
            actual_entries=len(data['entries']),
            actual_hours=round(actual_hours, 2),
            hours_variance=round(variance, 2),
            variance_percentage=round(variance_pct, 1),
            missed_shifts=len(data['shifts']) - len(entries_with_shift),
            unscheduled_entries=len(data['entries']) - len(entries_with_shift)
        )
        reports.append(report)
    
    return reports


@router.get("/reports/discrepancies")
async def get_discrepancy_report(
    start_date: str,
    end_date: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get time entry discrepancy report"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    entries = await db.enhanced_time_entries.find({
        "clock_in": {"$gte": start_date, "$lte": end_date},
        "discrepancies": {"$ne": []}
    }, {"_id": 0}).to_list(1000)
    
    # Group by discrepancy type
    by_type = {}
    by_staff = {}
    
    for entry in entries:
        for disc in entry.get('discrepancies', []):
            by_type[disc] = by_type.get(disc, 0) + 1
        
        staff_name = entry.get('staff_name', 'Unknown')
        by_staff[staff_name] = by_staff.get(staff_name, 0) + len(entry.get('discrepancies', []))
    
    return {
        "total_entries_with_discrepancies": len(entries),
        "by_type": by_type,
        "by_staff": dict(sorted(by_staff.items(), key=lambda x: x[1], reverse=True)),
        "entries": entries[:50]  # Return first 50 for detail view
    }
