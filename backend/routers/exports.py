"""
Exports Router - Connecteam Parity Phase 2
Handles CSV and PDF exports for timesheets, schedules, time off
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timezone
import io
import csv

from models import UserRole
from auth import get_current_user

router = APIRouter(prefix="/api/exports", tags=["Exports"])
security = HTTPBearer()


def get_db():
    """Get database connection"""
    from server import db
    return db


@router.get("/timesheets/csv")
async def export_timesheets_csv(
    pay_period_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Export timesheets to CSV"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    
    if pay_period_id:
        query["pay_period_id"] = pay_period_id
    elif start_date and end_date:
        query["clock_in"] = {"$gte": start_date, "$lte": end_date}
    else:
        raise HTTPException(status_code=400, detail="Provide pay_period_id or date range")
    
    entries = await db.enhanced_time_entries.find(query, {"_id": 0}).sort("clock_in", 1).to_list(10000)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Staff ID", "Staff Name", "Date", "Clock In", "Clock Out",
        "Regular Hours", "Overtime Hours", "Double Time Hours",
        "Total Break Minutes", "Status", "Discrepancies", "Location ID"
    ])
    
    for entry in entries:
        clock_in = entry.get('clock_in', '')
        date_str = clock_in[:10] if clock_in else ''
        
        writer.writerow([
            entry.get('staff_id', ''),
            entry.get('staff_name', ''),
            date_str,
            clock_in,
            entry.get('clock_out', ''),
            entry.get('regular_hours', 0),
            entry.get('overtime_hours', 0),
            entry.get('double_time_hours', 0),
            entry.get('total_break_minutes', 0),
            entry.get('status', ''),
            ', '.join(entry.get('discrepancies', [])),
            entry.get('location_id', '')
        ])
    
    output.seek(0)
    
    filename = f"timesheets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/timesheets/summary/csv")
async def export_timesheet_summary_csv(
    pay_period_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Export timesheet summary by staff to CSV"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    period = await db.pay_periods.find_one({"id": pay_period_id}, {"_id": 0})
    if not period:
        raise HTTPException(status_code=404, detail="Pay period not found")
    
    entries = await db.enhanced_time_entries.find({
        "clock_in": {"$gte": period['start_date'], "$lte": period['end_date']}
    }, {"_id": 0}).to_list(10000)
    
    # Aggregate by staff
    staff_totals = {}
    for entry in entries:
        sid = entry['staff_id']
        if sid not in staff_totals:
            staff_totals[sid] = {
                "staff_name": entry.get('staff_name', 'Unknown'),
                "regular_hours": 0,
                "overtime_hours": 0,
                "double_time_hours": 0,
                "total_break_minutes": 0,
                "entry_count": 0
            }
        
        staff_totals[sid]['regular_hours'] += entry.get('regular_hours', 0)
        staff_totals[sid]['overtime_hours'] += entry.get('overtime_hours', 0)
        staff_totals[sid]['double_time_hours'] += entry.get('double_time_hours', 0)
        staff_totals[sid]['total_break_minutes'] += entry.get('total_break_minutes', 0)
        staff_totals[sid]['entry_count'] += 1
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Staff ID", "Staff Name", "Regular Hours", "Overtime Hours",
        "Double Time Hours", "Total Hours", "Total Break Minutes", "Entry Count"
    ])
    
    for sid, totals in staff_totals.items():
        total_hours = totals['regular_hours'] + totals['overtime_hours'] + totals['double_time_hours']
        writer.writerow([
            sid,
            totals['staff_name'],
            round(totals['regular_hours'], 2),
            round(totals['overtime_hours'], 2),
            round(totals['double_time_hours'], 2),
            round(total_hours, 2),
            totals['total_break_minutes'],
            totals['entry_count']
        ])
    
    output.seek(0)
    
    filename = f"timesheet_summary_{period['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/schedules/csv")
async def export_schedules_csv(
    start_date: str,
    end_date: str,
    location_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Export scheduled shifts to CSV"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {
        "start_time": {"$gte": start_date, "$lte": end_date},
        "status": {"$ne": "cancelled"}
    }
    
    if location_id:
        query["location_id"] = location_id
    
    shifts = await db.scheduled_shifts.find(query, {"_id": 0}).sort("start_time", 1).to_list(5000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Shift ID", "Staff ID", "Staff Name", "Date", "Start Time", "End Time",
        "Planned Hours", "Actual Start", "Actual End", "Actual Hours", "Status", "Location ID"
    ])
    
    for shift in shifts:
        start = shift.get('start_time', '')
        end = shift.get('end_time', '')
        date_str = start[:10] if start else ''
        
        # Calculate planned hours
        try:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00')) if start else None
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')) if end else None
            planned_hours = (end_dt - start_dt).total_seconds() / 3600 if start_dt and end_dt else 0
        except:
            planned_hours = 0
        
        # Calculate actual hours
        actual_start = shift.get('actual_start', '')
        actual_end = shift.get('actual_end', '')
        actual_hours = 0
        if actual_start and actual_end:
            try:
                as_dt = datetime.fromisoformat(actual_start.replace('Z', '+00:00'))
                ae_dt = datetime.fromisoformat(actual_end.replace('Z', '+00:00'))
                actual_hours = (ae_dt - as_dt).total_seconds() / 3600
            except:
                pass
        
        writer.writerow([
            shift.get('id', ''),
            shift.get('staff_id', ''),
            shift.get('staff_name', ''),
            date_str,
            start,
            end,
            round(planned_hours, 2),
            actual_start,
            actual_end,
            round(actual_hours, 2),
            shift.get('status', ''),
            shift.get('location_id', '')
        ])
    
    output.seek(0)
    
    filename = f"schedules_{start_date[:10]}_{end_date[:10]}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/time-off/csv")
async def export_time_off_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Export time off requests to CSV"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if start_date:
        query["start_date"] = {"$gte": start_date}
    if end_date:
        if "end_date" not in query:
            query["end_date"] = {}
        query["end_date"]["$lte"] = end_date
    if status:
        query["status"] = status
    
    requests = await db.time_off_requests.find(query, {"_id": 0}).sort("start_date", 1).to_list(5000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Request ID", "Staff ID", "Staff Name", "Time Off Type",
        "Start Date", "End Date", "Hours Requested", "Status",
        "Reason", "Reviewed By", "Reviewed At", "Balance Before", "Balance After"
    ])
    
    for req in requests:
        writer.writerow([
            req.get('id', ''),
            req.get('staff_id', ''),
            req.get('staff_name', ''),
            req.get('time_off_type', ''),
            req.get('start_date', '')[:10] if req.get('start_date') else '',
            req.get('end_date', '')[:10] if req.get('end_date') else '',
            req.get('hours_requested', 0),
            req.get('status', ''),
            req.get('reason', ''),
            req.get('reviewed_by_name', ''),
            req.get('reviewed_at', ''),
            req.get('balance_before', 0),
            req.get('balance_after', 0)
        ])
    
    output.seek(0)
    
    filename = f"time_off_requests_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/form-submissions/csv")
async def export_form_submissions_csv(
    template_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Export form submissions to CSV"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if template_id:
        query["template_id"] = template_id
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    submissions = await db.form_submissions.find(query, {"_id": 0}).sort("created_at", 1).to_list(5000)
    
    if not submissions:
        raise HTTPException(status_code=404, detail="No submissions found")
    
    # Get all unique field keys
    all_fields = set()
    for sub in submissions:
        all_fields.update(sub.get('values', {}).keys())
    
    field_list = sorted(list(all_fields))
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    header = ["Submission ID", "Template Name", "Submitted By", "Submitted At", "Status"] + field_list
    writer.writerow(header)
    
    for sub in submissions:
        row = [
            sub.get('id', ''),
            sub.get('template_name', ''),
            sub.get('submitted_by_name', ''),
            sub.get('submitted_at', ''),
            sub.get('status', '')
        ]
        
        values = sub.get('values', {})
        for field in field_list:
            val = values.get(field, '')
            if isinstance(val, (list, dict)):
                val = str(val)
            row.append(val)
        
        writer.writerow(row)
    
    output.seek(0)
    
    filename = f"form_submissions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )



@router.get("/bookings/csv")
async def export_bookings_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Export bookings to CSV"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if start_date:
        query["check_in_date"] = {"$gte": start_date}
    if end_date:
        if "check_in_date" in query:
            query["check_in_date"]["$lte"] = end_date
        else:
            query["check_in_date"] = {"$lte": end_date}
    if status:
        query["status"] = status
    
    bookings = await db.bookings.find(query, {"_id": 0}).sort("check_in_date", -1).to_list(10000)
    
    # Get customer and dog lookup maps
    customers = await db.users.find({"role": "customer"}, {"_id": 0}).to_list(10000)
    customer_map = {c.get('id'): c for c in customers}
    household_map = {c.get('household_id'): c for c in customers if c.get('household_id')}
    
    dogs = await db.dogs.find({}, {"_id": 0}).to_list(10000)
    dog_map = {d.get('id'): d for d in dogs}
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Booking ID", "Customer Name", "Customer Email", "Dog Names",
        "Booking Type", "Check In", "Check Out", "Status",
        "Total Price", "Payment Type", "Payment Status",
        "Accommodation", "Created At"
    ])
    
    for booking in bookings:
        # Get customer info
        customer = customer_map.get(booking.get('customer_id')) or household_map.get(booking.get('household_id'))
        customer_name = customer.get('full_name', 'Unknown') if customer else 'Unknown'
        customer_email = customer.get('email', '') if customer else ''
        
        # Get dog names
        dog_names = ', '.join([
            dog_map.get(did, {}).get('name', 'Unknown') 
            for did in booking.get('dog_ids', [])
        ])
        
        writer.writerow([
            booking.get('id', ''),
            customer_name,
            customer_email,
            dog_names,
            booking.get('booking_type', 'stay'),
            booking.get('check_in_date', '')[:10] if booking.get('check_in_date') else '',
            booking.get('check_out_date', '')[:10] if booking.get('check_out_date') else '',
            booking.get('status', ''),
            booking.get('total_price', 0),
            booking.get('payment_type', ''),
            booking.get('payment_status', ''),
            booking.get('accommodation_type', ''),
            booking.get('created_at', '')[:19] if booking.get('created_at') else ''
        ])
    
    output.seek(0)
    filename = f"bookings_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/customers/csv")
async def export_customers_csv(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Export customers to CSV"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    customers = await db.users.find({"role": "customer"}, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
    # Get dog counts per household
    dogs = await db.dogs.find({}, {"_id": 0}).to_list(10000)
    dog_counts = {}
    for dog in dogs:
        hid = dog.get('household_id')
        if hid:
            dog_counts[hid] = dog_counts.get(hid, 0) + 1
    
    # Get booking counts per household
    bookings = await db.bookings.find({}, {"_id": 0, "household_id": 1, "status": 1}).to_list(10000)
    booking_counts = {}
    for booking in bookings:
        hid = booking.get('household_id')
        if hid:
            booking_counts[hid] = booking_counts.get(hid, 0) + 1
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Customer ID", "Full Name", "Email", "Phone",
        "Address", "City", "State", "Zip Code",
        "Emergency Contact", "Emergency Phone",
        "Dogs Count", "Bookings Count", "Active", "Created At"
    ])
    
    for customer in customers:
        hid = customer.get('household_id', '')
        writer.writerow([
            customer.get('id', ''),
            customer.get('full_name', ''),
            customer.get('email', ''),
            customer.get('phone', ''),
            customer.get('address', ''),
            customer.get('city', ''),
            customer.get('state', ''),
            customer.get('zip_code', ''),
            customer.get('emergency_contact', ''),
            customer.get('emergency_phone', ''),
            dog_counts.get(hid, 0),
            booking_counts.get(hid, 0),
            'Yes' if customer.get('is_active', True) else 'No',
            customer.get('created_at', '')[:19] if customer.get('created_at') else ''
        ])
    
    output.seek(0)
    filename = f"customers_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
