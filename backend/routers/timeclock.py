"""
Time Clock & Attendance Router - Connecteam Parity
Handles GPS clock in/out, breaks, geofencing, timesheets
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from math import radians, sin, cos, sqrt, atan2
import uuid

from models import (
    UserRole,
    # GPS & Geofencing
    GPSRecord, GeofenceZone, GeofenceZoneCreate, GeofenceZoneResponse,
    # Enhanced Time Clock
    EnhancedTimeEntry, EnhancedTimeEntryCreate, EnhancedTimeEntryResponse,
    ClockEventType, ClockEventSource, DiscrepancyType,
    # Breaks
    BreakEntry, BreakEntryCreate, BreakEntryResponse, BreakType,
    BreakPolicy, BreakPolicyCreate, BreakPolicyResponse,
    # Overtime
    OvertimeRule, OvertimeRuleCreate, OvertimeRuleResponse,
    # Punch Rounding
    PunchRoundingRule, PunchRoundingRuleCreate, PunchRoundingRuleResponse, RoundingDirection,
    # Pay Periods
    PayPeriod, PayPeriodCreate, PayPeriodResponse, PayPeriodStatus, TimesheetSummary,
)
from auth import get_current_user

router = APIRouter(prefix="/api/timeclock", tags=["Time Clock"])
security = HTTPBearer()


def get_db():
    """Get database connection - will be injected"""
    from server import db
    return db


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS coordinates in meters"""
    R = 6371000  # Earth's radius in meters
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def round_time(dt: datetime, interval_minutes: int, direction: RoundingDirection) -> datetime:
    """Round datetime to nearest interval"""
    minutes = dt.minute + dt.second / 60
    
    if direction == RoundingDirection.UP:
        rounded = ((minutes // interval_minutes) + 1) * interval_minutes
    elif direction == RoundingDirection.DOWN:
        rounded = (minutes // interval_minutes) * interval_minutes
    else:  # NEAREST
        rounded = round(minutes / interval_minutes) * interval_minutes
    
    if rounded >= 60:
        return dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    
    return dt.replace(minute=int(rounded), second=0, microsecond=0)


# ==================== GEOFENCE ZONES ====================

@router.get("/geofences", response_model=List[GeofenceZoneResponse])
async def list_geofences(
    location_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List geofence zones (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if location_id:
        query["location_id"] = location_id
    
    zones = await db.geofence_zones.find(query, {"_id": 0}).to_list(100)
    return [GeofenceZoneResponse(**z) for z in zones]


@router.post("/geofences", response_model=GeofenceZoneResponse)
async def create_geofence(
    data: GeofenceZoneCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a geofence zone (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    zone = GeofenceZone(**data.model_dump())
    doc = zone.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.geofence_zones.insert_one(doc)
    return GeofenceZoneResponse(**zone.model_dump())


@router.patch("/geofences/{zone_id}", response_model=GeofenceZoneResponse)
async def update_geofence(
    zone_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a geofence zone (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.geofence_zones.update_one(
        {"id": zone_id},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Geofence zone not found")
    
    zone = await db.geofence_zones.find_one({"id": zone_id}, {"_id": 0})
    return GeofenceZoneResponse(**zone)


@router.delete("/geofences/{zone_id}")
async def delete_geofence(
    zone_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a geofence zone (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.geofence_zones.delete_one({"id": zone_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Geofence zone not found")
    
    return {"message": "Geofence zone deleted"}


async def check_geofence(db, location_id: str, latitude: float, longitude: float) -> tuple[bool, Optional[str]]:
    """Check if coordinates are within any active geofence for location"""
    zones = await db.geofence_zones.find({
        "location_id": location_id,
        "is_active": True,
        "require_within": True
    }, {"_id": 0}).to_list(100)
    
    if not zones:
        # No geofences configured, allow by default
        return True, None
    
    for zone in zones:
        distance = haversine_distance(latitude, longitude, zone['latitude'], zone['longitude'])
        if distance <= zone['radius']:
            return True, zone['id']
    
    return False, None


# ==================== ENHANCED CLOCK IN/OUT ====================

@router.post("/clock-in", response_model=EnhancedTimeEntryResponse)
async def clock_in(
    data: EnhancedTimeEntryCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Clock in with GPS capture"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    # Check for existing open time entry
    existing = await db.enhanced_time_entries.find_one({
        "staff_id": user.id,
        "clock_out": None
    }, {"_id": 0})
    
    if existing:
        raise HTTPException(status_code=400, detail="Already clocked in. Please clock out first.")
    
    # Record GPS if provided
    gps_id = None
    within_geofence = True
    
    if data.latitude and data.longitude:
        gps_record = GPSRecord(
            staff_id=user.id,
            latitude=data.latitude,
            longitude=data.longitude,
            accuracy=data.accuracy or 0,
            source=data.source.value,
            event_type="clock_in"
        )
        gps_doc = gps_record.model_dump()
        gps_doc['timestamp'] = gps_doc['timestamp'].isoformat()
        gps_doc['created_at'] = gps_doc['created_at'].isoformat()
        gps_doc['updated_at'] = gps_doc['updated_at'].isoformat()
        await db.gps_records.insert_one(gps_doc)
        gps_id = gps_record.id
        
        # Check geofence
        within_geofence, _ = await check_geofence(db, data.location_id, data.latitude, data.longitude)
    
    # Apply punch rounding if configured
    clock_in_time = datetime.now(timezone.utc)
    rounded_clock_in = None
    rounding_rule_applied = None
    
    rounding_rule = await db.punch_rounding_rules.find_one({
        "$or": [
            {"location_id": data.location_id},
            {"location_id": None}
        ],
        "is_active": True
    }, {"_id": 0})
    
    if rounding_rule:
        rounded_clock_in = round_time(
            clock_in_time,
            rounding_rule['interval_minutes'],
            RoundingDirection(rounding_rule['clock_in_direction'])
        )
        rounding_rule_applied = rounding_rule['id']
    
    # Check for discrepancies
    discrepancies = []
    
    if not within_geofence:
        discrepancies.append(DiscrepancyType.OUTSIDE_GEOFENCE.value)
    
    # Check if outside scheduled shift
    if data.shift_id:
        shift = await db.shifts.find_one({"id": data.shift_id}, {"_id": 0})
        if shift:
            shift_start = datetime.fromisoformat(shift['start_time']) if isinstance(shift['start_time'], str) else shift['start_time']
            # Allow 15 minute grace before shift
            if clock_in_time < shift_start - timedelta(minutes=15):
                discrepancies.append(DiscrepancyType.OUTSIDE_SCHEDULED_SHIFT.value)
    
    # Create time entry
    entry = EnhancedTimeEntry(
        staff_id=user.id,
        staff_name=user.full_name,
        location_id=data.location_id,
        clock_in=clock_in_time,
        clock_in_gps_id=gps_id,
        clock_in_within_geofence=within_geofence,
        clock_in_source=data.source,
        shift_id=data.shift_id,
        rounded_clock_in=rounded_clock_in,
        rounding_rule_applied=rounding_rule_applied,
        discrepancies=discrepancies,
        notes=data.notes
    )
    
    doc = entry.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['clock_in'] = doc['clock_in'].isoformat()
    if doc['rounded_clock_in']:
        doc['rounded_clock_in'] = doc['rounded_clock_in'].isoformat()
    doc['clock_in_source'] = doc['clock_in_source'].value
    
    await db.enhanced_time_entries.insert_one(doc)
    
    return EnhancedTimeEntryResponse(**entry.model_dump())


@router.post("/clock-out", response_model=EnhancedTimeEntryResponse)
async def clock_out(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    accuracy: Optional[float] = None,
    source: ClockEventSource = ClockEventSource.MOBILE,
    notes: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Clock out with GPS capture"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    # Find open time entry
    entry = await db.enhanced_time_entries.find_one({
        "staff_id": user.id,
        "clock_out": None
    }, {"_id": 0})
    
    if not entry:
        raise HTTPException(status_code=400, detail="No active clock-in found")
    
    # Record GPS if provided
    gps_id = None
    within_geofence = True
    
    if latitude and longitude:
        gps_record = GPSRecord(
            staff_id=user.id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy or 0,
            source=source.value,
            event_type="clock_out"
        )
        gps_doc = gps_record.model_dump()
        gps_doc['timestamp'] = gps_doc['timestamp'].isoformat()
        gps_doc['created_at'] = gps_doc['created_at'].isoformat()
        gps_doc['updated_at'] = gps_doc['updated_at'].isoformat()
        await db.gps_records.insert_one(gps_doc)
        gps_id = gps_record.id
        
        # Check geofence
        within_geofence, _ = await check_geofence(db, entry['location_id'], latitude, longitude)
    
    # Calculate clock out time and rounding
    clock_out_time = datetime.now(timezone.utc)
    rounded_clock_out = None
    
    if entry.get('rounding_rule_applied'):
        rounding_rule = await db.punch_rounding_rules.find_one({
            "id": entry['rounding_rule_applied']
        }, {"_id": 0})
        
        if rounding_rule:
            rounded_clock_out = round_time(
                clock_out_time,
                rounding_rule['interval_minutes'],
                RoundingDirection(rounding_rule['clock_out_direction'])
            )
    
    # Calculate hours
    clock_in = datetime.fromisoformat(entry['clock_in']) if isinstance(entry['clock_in'], str) else entry['clock_in']
    effective_clock_in = datetime.fromisoformat(entry['rounded_clock_in']) if entry.get('rounded_clock_in') else clock_in
    effective_clock_out = rounded_clock_out or clock_out_time
    
    total_seconds = (effective_clock_out - effective_clock_in).total_seconds()
    total_hours = total_seconds / 3600
    
    # Subtract breaks
    breaks = await db.break_entries.find({
        "time_entry_id": entry['id']
    }, {"_id": 0}).to_list(100)
    
    total_break_minutes = 0
    paid_break_minutes = 0
    unpaid_break_minutes = 0
    
    for brk in breaks:
        if brk.get('duration_minutes'):
            total_break_minutes += brk['duration_minutes']
            if brk.get('is_paid'):
                paid_break_minutes += brk['duration_minutes']
            else:
                unpaid_break_minutes += brk['duration_minutes']
    
    # Adjust hours for unpaid breaks
    adjusted_hours = total_hours - (unpaid_break_minutes / 60)
    
    # Calculate overtime
    overtime_rule = await db.overtime_rules.find_one({
        "$or": [
            {"location_id": entry['location_id']},
            {"location_id": None}
        ],
        "is_active": True
    }, {"_id": 0})
    
    regular_hours = adjusted_hours
    overtime_hours = 0.0
    double_time_hours = 0.0
    
    # For now, just track daily hours. Weekly calculation happens in timesheet summary
    if overtime_rule and overtime_rule.get('daily_regular_hours'):
        daily_limit = overtime_rule['daily_regular_hours']
        if adjusted_hours > daily_limit:
            regular_hours = daily_limit
            overtime_hours = adjusted_hours - daily_limit
    
    # Update discrepancies
    discrepancies = entry.get('discrepancies', [])
    if not within_geofence and DiscrepancyType.OUTSIDE_GEOFENCE.value not in discrepancies:
        discrepancies.append(DiscrepancyType.OUTSIDE_GEOFENCE.value)
    
    # Update entry
    updates = {
        "clock_out": clock_out_time.isoformat(),
        "clock_out_gps_id": gps_id,
        "clock_out_within_geofence": within_geofence,
        "clock_out_source": source.value,
        "rounded_clock_out": rounded_clock_out.isoformat() if rounded_clock_out else None,
        "regular_hours": round(regular_hours, 2),
        "overtime_hours": round(overtime_hours, 2),
        "double_time_hours": round(double_time_hours, 2),
        "total_break_minutes": total_break_minutes,
        "paid_break_minutes": paid_break_minutes,
        "unpaid_break_minutes": unpaid_break_minutes,
        "discrepancies": discrepancies,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if notes:
        updates["notes"] = (entry.get('notes', '') + '\n' + notes).strip()
    
    await db.enhanced_time_entries.update_one(
        {"id": entry['id']},
        {"$set": updates}
    )
    
    updated_entry = await db.enhanced_time_entries.find_one({"id": entry['id']}, {"_id": 0})
    return EnhancedTimeEntryResponse(**updated_entry)


@router.get("/entries", response_model=List[EnhancedTimeEntryResponse])
async def list_time_entries(
    staff_id: Optional[str] = None,
    location_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    pay_period_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List time entries with filters"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {}
    
    # Staff can only see their own entries
    if user.role == UserRole.STAFF:
        query["staff_id"] = user.id
    elif staff_id:
        query["staff_id"] = staff_id
    
    if location_id:
        query["location_id"] = location_id
    
    if start_date:
        query["clock_in"] = {"$gte": start_date}
    
    if end_date:
        if "clock_in" in query:
            query["clock_in"]["$lte"] = end_date
        else:
            query["clock_in"] = {"$lte": end_date}
    
    if status:
        query["status"] = status
    
    if pay_period_id:
        query["pay_period_id"] = pay_period_id
    
    entries = await db.enhanced_time_entries.find(query, {"_id": 0}).sort("clock_in", -1).to_list(500)
    return [EnhancedTimeEntryResponse(**e) for e in entries]


@router.get("/entries/current", response_model=Optional[EnhancedTimeEntryResponse])
async def get_current_entry(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get current active time entry for logged in user"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    entry = await db.enhanced_time_entries.find_one({
        "staff_id": user.id,
        "clock_out": None
    }, {"_id": 0})
    
    if not entry:
        return None
    
    return EnhancedTimeEntryResponse(**entry)


# ==================== BREAKS ====================

@router.post("/breaks/start", response_model=BreakEntryResponse)
async def start_break(
    data: BreakEntryCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Start a break"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    # Verify time entry exists and belongs to user
    entry = await db.enhanced_time_entries.find_one({
        "id": data.time_entry_id,
        "staff_id": user.id,
        "clock_out": None
    }, {"_id": 0})
    
    if not entry:
        raise HTTPException(status_code=404, detail="Active time entry not found")
    
    # Check for existing active break
    active_break = await db.break_entries.find_one({
        "time_entry_id": data.time_entry_id,
        "end_time": None
    }, {"_id": 0})
    
    if active_break:
        raise HTTPException(status_code=400, detail="Break already in progress")
    
    # Record GPS if provided
    gps_id = None
    if data.latitude and data.longitude:
        gps_record = GPSRecord(
            staff_id=user.id,
            latitude=data.latitude,
            longitude=data.longitude,
            accuracy=data.accuracy or 0,
            event_type="break_start"
        )
        gps_doc = gps_record.model_dump()
        gps_doc['timestamp'] = gps_doc['timestamp'].isoformat()
        gps_doc['created_at'] = gps_doc['created_at'].isoformat()
        gps_doc['updated_at'] = gps_doc['updated_at'].isoformat()
        await db.gps_records.insert_one(gps_doc)
        gps_id = gps_record.id
    
    # Determine if break is paid based on policy
    break_policy = await db.break_policies.find_one({
        "$or": [
            {"location_id": entry['location_id']},
            {"location_id": None}
        ],
        "is_active": True
    }, {"_id": 0})
    
    is_paid = break_policy.get('is_paid', False) if break_policy else False
    
    break_entry = BreakEntry(
        time_entry_id=data.time_entry_id,
        staff_id=user.id,
        break_type=data.break_type,
        start_time=datetime.now(timezone.utc),
        is_paid=is_paid,
        start_gps_id=gps_id,
        notes=data.notes
    )
    
    doc = break_entry.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['start_time'] = doc['start_time'].isoformat()
    doc['break_type'] = doc['break_type'].value
    
    await db.break_entries.insert_one(doc)
    
    return BreakEntryResponse(**break_entry.model_dump())


@router.post("/breaks/end", response_model=BreakEntryResponse)
async def end_break(
    time_entry_id: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    accuracy: Optional[float] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """End current break"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    # Find active break
    active_break = await db.break_entries.find_one({
        "time_entry_id": time_entry_id,
        "staff_id": user.id,
        "end_time": None
    }, {"_id": 0})
    
    if not active_break:
        raise HTTPException(status_code=404, detail="No active break found")
    
    # Record GPS if provided
    gps_id = None
    if latitude and longitude:
        gps_record = GPSRecord(
            staff_id=user.id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy or 0,
            event_type="break_end"
        )
        gps_doc = gps_record.model_dump()
        gps_doc['timestamp'] = gps_doc['timestamp'].isoformat()
        gps_doc['created_at'] = gps_doc['created_at'].isoformat()
        gps_doc['updated_at'] = gps_doc['updated_at'].isoformat()
        await db.gps_records.insert_one(gps_doc)
        gps_id = gps_record.id
    
    end_time = datetime.now(timezone.utc)
    start_time = datetime.fromisoformat(active_break['start_time']) if isinstance(active_break['start_time'], str) else active_break['start_time']
    duration_minutes = int((end_time - start_time).total_seconds() / 60)
    
    await db.break_entries.update_one(
        {"id": active_break['id']},
        {"$set": {
            "end_time": end_time.isoformat(),
            "end_gps_id": gps_id,
            "duration_minutes": duration_minutes,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    updated = await db.break_entries.find_one({"id": active_break['id']}, {"_id": 0})
    return BreakEntryResponse(**updated)


@router.get("/breaks", response_model=List[BreakEntryResponse])
async def list_breaks(
    time_entry_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List breaks for a time entry"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    # Verify access
    entry = await db.enhanced_time_entries.find_one({"id": time_entry_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    if user.role == UserRole.STAFF and entry['staff_id'] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    breaks = await db.break_entries.find({"time_entry_id": time_entry_id}, {"_id": 0}).to_list(100)
    return [BreakEntryResponse(**b) for b in breaks]


# ==================== BREAK POLICIES ====================

@router.get("/break-policies", response_model=List[BreakPolicyResponse])
async def list_break_policies(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List break policies (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    policies = await db.break_policies.find({"is_active": True}, {"_id": 0}).to_list(100)
    return [BreakPolicyResponse(**p) for p in policies]


@router.post("/break-policies", response_model=BreakPolicyResponse)
async def create_break_policy(
    data: BreakPolicyCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a break policy (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    policy = BreakPolicy(**data.model_dump())
    doc = policy.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.break_policies.insert_one(doc)
    return BreakPolicyResponse(**policy.model_dump())


# ==================== OVERTIME RULES ====================

@router.get("/overtime-rules", response_model=List[OvertimeRuleResponse])
async def list_overtime_rules(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List overtime rules (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rules = await db.overtime_rules.find({"is_active": True}, {"_id": 0}).to_list(100)
    return [OvertimeRuleResponse(**r) for r in rules]


@router.post("/overtime-rules", response_model=OvertimeRuleResponse)
async def create_overtime_rule(
    data: OvertimeRuleCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create an overtime rule (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rule = OvertimeRule(**data.model_dump())
    doc = rule.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.overtime_rules.insert_one(doc)
    return OvertimeRuleResponse(**rule.model_dump())


@router.patch("/overtime-rules/{rule_id}", response_model=OvertimeRuleResponse)
async def update_overtime_rule(
    rule_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update an overtime rule (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.overtime_rules.update_one(
        {"id": rule_id},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Overtime rule not found")
    
    rule = await db.overtime_rules.find_one({"id": rule_id}, {"_id": 0})
    return OvertimeRuleResponse(**rule)


# ==================== PUNCH ROUNDING ====================

@router.get("/rounding-rules", response_model=List[PunchRoundingRuleResponse])
async def list_rounding_rules(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List punch rounding rules (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rules = await db.punch_rounding_rules.find({"is_active": True}, {"_id": 0}).to_list(100)
    return [PunchRoundingRuleResponse(**r) for r in rules]


@router.post("/rounding-rules", response_model=PunchRoundingRuleResponse)
async def create_rounding_rule(
    data: PunchRoundingRuleCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a punch rounding rule (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rule = PunchRoundingRule(**data.model_dump())
    doc = rule.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['clock_in_direction'] = doc['clock_in_direction'].value
    doc['clock_out_direction'] = doc['clock_out_direction'].value
    
    await db.punch_rounding_rules.insert_one(doc)
    return PunchRoundingRuleResponse(**rule.model_dump())


# ==================== PAY PERIODS & TIMESHEETS ====================

@router.get("/pay-periods", response_model=List[PayPeriodResponse])
async def list_pay_periods(
    status: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List pay periods"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if status:
        query["status"] = status
    
    periods = await db.pay_periods.find(query, {"_id": 0}).sort("start_date", -1).to_list(100)
    return [PayPeriodResponse(**p) for p in periods]


@router.post("/pay-periods", response_model=PayPeriodResponse)
async def create_pay_period(
    data: PayPeriodCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a pay period (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    period = PayPeriod(**data.model_dump())
    doc = period.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['start_date'] = doc['start_date'].isoformat()
    doc['end_date'] = doc['end_date'].isoformat()
    doc['period_type'] = doc['period_type'].value
    doc['status'] = doc['status'].value
    
    await db.pay_periods.insert_one(doc)
    return PayPeriodResponse(**period.model_dump())


@router.post("/pay-periods/{period_id}/approve")
async def approve_pay_period(
    period_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Approve all time entries in a pay period"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    period = await db.pay_periods.find_one({"id": period_id}, {"_id": 0})
    if not period:
        raise HTTPException(status_code=404, detail="Pay period not found")
    
    if period['status'] == PayPeriodStatus.LOCKED.value:
        raise HTTPException(status_code=400, detail="Pay period is locked")
    
    # Approve all entries in period
    result = await db.enhanced_time_entries.update_many(
        {"pay_period_id": period_id, "status": {"$ne": "approved"}},
        {"$set": {
            "status": "approved",
            "approved_by": user.id,
            "approved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update period status
    await db.pay_periods.update_one(
        {"id": period_id},
        {"$set": {
            "status": PayPeriodStatus.APPROVED.value,
            "approved_by": user.id,
            "approved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": f"Approved {result.modified_count} time entries"}


@router.post("/pay-periods/{period_id}/lock")
async def lock_pay_period(
    period_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Lock a pay period (no more edits allowed)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    period = await db.pay_periods.find_one({"id": period_id}, {"_id": 0})
    if not period:
        raise HTTPException(status_code=404, detail="Pay period not found")
    
    # Lock all entries
    await db.enhanced_time_entries.update_many(
        {"pay_period_id": period_id},
        {"$set": {"status": "locked"}}
    )
    
    # Lock period
    await db.pay_periods.update_one(
        {"id": period_id},
        {"$set": {
            "status": PayPeriodStatus.LOCKED.value,
            "locked_by": user.id,
            "locked_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Pay period locked"}


@router.get("/pay-periods/{period_id}/summary", response_model=List[TimesheetSummary])
async def get_pay_period_summary(
    period_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get timesheet summary for all staff in a pay period"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    period = await db.pay_periods.find_one({"id": period_id}, {"_id": 0})
    if not period:
        raise HTTPException(status_code=404, detail="Pay period not found")
    
    # Get all entries in period
    entries = await db.enhanced_time_entries.find({
        "clock_in": {
            "$gte": period['start_date'],
            "$lte": period['end_date']
        }
    }, {"_id": 0}).to_list(5000)
    
    # Group by staff
    staff_entries = {}
    for entry in entries:
        sid = entry['staff_id']
        if sid not in staff_entries:
            staff_entries[sid] = {
                "staff_id": sid,
                "staff_name": entry.get('staff_name', 'Unknown'),
                "entries": []
            }
        staff_entries[sid]['entries'].append(entry)
    
    # Calculate summaries
    summaries = []
    for sid, data in staff_entries.items():
        summary = TimesheetSummary(
            staff_id=sid,
            staff_name=data['staff_name'],
            pay_period_id=period_id,
            entry_count=len(data['entries'])
        )
        
        for entry in data['entries']:
            summary.regular_hours += entry.get('regular_hours', 0)
            summary.overtime_hours += entry.get('overtime_hours', 0)
            summary.double_time_hours += entry.get('double_time_hours', 0)
            summary.total_break_minutes += entry.get('total_break_minutes', 0)
            summary.paid_break_minutes += entry.get('paid_break_minutes', 0)
            summary.unpaid_break_minutes += entry.get('unpaid_break_minutes', 0)
            
            if entry.get('status') == 'approved':
                summary.entries_approved += 1
            elif entry.get('discrepancies'):
                summary.entries_flagged += 1
            else:
                summary.entries_pending += 1
            
            if entry.get('discrepancies'):
                summary.discrepancy_count += len(entry['discrepancies'])
                summary.discrepancies.append({
                    "entry_id": entry['id'],
                    "types": entry['discrepancies']
                })
        
        summary.total_hours = summary.regular_hours + summary.overtime_hours + summary.double_time_hours
        summaries.append(summary)
    
    return summaries
