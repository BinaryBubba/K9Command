"""
HR & Time Off Router - Connecteam Parity
Handles time off policies, requests, balances, and accruals
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from models import (
    UserRole,
    TimeOffPolicy, TimeOffPolicyCreate, TimeOffPolicyResponse, TimeOffType, AccrualFrequency,
    TimeOffRequest, TimeOffRequestCreate, TimeOffRequestResponse, TimeOffRequestStatus,
    TimeOffBalance, TimeOffBalanceResponse,
)
from auth import get_current_user

router = APIRouter(prefix="/api/hr", tags=["HR / Time Off"])
security = HTTPBearer()


def get_db():
    """Get database connection - will be injected"""
    from server import db
    return db


# ==================== TIME OFF POLICIES ====================

@router.get("/time-off-policies", response_model=List[TimeOffPolicyResponse])
async def list_time_off_policies(
    time_off_type: Optional[str] = None,
    is_active: bool = True,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List time off policies"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {"is_active": is_active}
    if time_off_type:
        query["time_off_type"] = time_off_type
    
    policies = await db.time_off_policies.find(query, {"_id": 0}).to_list(100)
    return [TimeOffPolicyResponse(**p) for p in policies]


@router.get("/time-off-policies/{policy_id}", response_model=TimeOffPolicyResponse)
async def get_time_off_policy(
    policy_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single time off policy"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    policy = await db.time_off_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Time off policy not found")
    
    return TimeOffPolicyResponse(**policy)


@router.post("/time-off-policies", response_model=TimeOffPolicyResponse)
async def create_time_off_policy(
    data: TimeOffPolicyCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a time off policy (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    policy = TimeOffPolicy(**data.model_dump())
    doc = policy.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['time_off_type'] = doc['time_off_type'].value
    doc['accrual_frequency'] = doc['accrual_frequency'].value
    
    await db.time_off_policies.insert_one(doc)
    return TimeOffPolicyResponse(**policy.model_dump())


@router.patch("/time-off-policies/{policy_id}", response_model=TimeOffPolicyResponse)
async def update_time_off_policy(
    policy_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a time off policy (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.time_off_policies.update_one(
        {"id": policy_id},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Time off policy not found")
    
    policy = await db.time_off_policies.find_one({"id": policy_id}, {"_id": 0})
    return TimeOffPolicyResponse(**policy)


@router.delete("/time-off-policies/{policy_id}")
async def delete_time_off_policy(
    policy_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Deactivate a time off policy (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.time_off_policies.update_one(
        {"id": policy_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Time off policy not found")
    
    return {"message": "Time off policy deactivated"}


# ==================== TIME OFF REQUESTS ====================

@router.get("/time-off-requests", response_model=List[TimeOffRequestResponse])
async def list_time_off_requests(
    staff_id: Optional[str] = None,
    status: Optional[str] = None,
    time_off_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List time off requests"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {}
    
    # Staff can only see their own requests
    if user.role == UserRole.STAFF:
        query["staff_id"] = user.id
    elif staff_id:
        query["staff_id"] = staff_id
    
    if status:
        query["status"] = status
    if time_off_type:
        query["time_off_type"] = time_off_type
    if start_date:
        query["start_date"] = {"$gte": start_date}
    if end_date:
        if "end_date" not in query:
            query["end_date"] = {}
        query["end_date"]["$lte"] = end_date
    
    requests = await db.time_off_requests.find(query, {"_id": 0}).sort("start_date", -1).to_list(500)
    return [TimeOffRequestResponse(**r) for r in requests]


@router.get("/time-off-requests/{request_id}", response_model=TimeOffRequestResponse)
async def get_time_off_request(
    request_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single time off request"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    request = await db.time_off_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Time off request not found")
    
    # Check access
    if user.role == UserRole.STAFF and request['staff_id'] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return TimeOffRequestResponse(**request)


@router.post("/time-off-requests", response_model=TimeOffRequestResponse)
async def create_time_off_request(
    data: TimeOffRequestCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Submit a time off request"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    # Get policy
    policy = await db.time_off_policies.find_one({"id": data.policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Time off policy not found")
    
    if not policy.get('is_active'):
        raise HTTPException(status_code=400, detail="Time off policy is inactive")
    
    # Check advance notice
    if policy.get('advance_notice_days', 0) > 0:
        min_start = datetime.now(timezone.utc) + timedelta(days=policy['advance_notice_days'])
        # Ensure start_date is timezone-aware for comparison
        start_date_aware = data.start_date
        if start_date_aware.tzinfo is None:
            start_date_aware = start_date_aware.replace(tzinfo=timezone.utc)
        if start_date_aware < min_start:
            raise HTTPException(
                status_code=400, 
                detail=f"Request must be at least {policy['advance_notice_days']} days in advance"
            )
    
    # Check hours requested
    if policy.get('min_request_hours') and data.hours_requested < policy['min_request_hours']:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum request is {policy['min_request_hours']} hours"
        )
    
    # Get current balance
    balance = await db.time_off_balances.find_one({
        "staff_id": user.id,
        "policy_id": data.policy_id
    }, {"_id": 0})
    
    current_balance = balance.get('balance_hours', 0) if balance else 0
    pending_hours = balance.get('pending_hours', 0) if balance else 0
    
    available_balance = current_balance - pending_hours
    
    if data.hours_requested > available_balance:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: {available_balance} hours"
        )
    
    # Determine if auto-approve
    status = TimeOffRequestStatus.PENDING
    if not policy.get('requires_approval'):
        status = TimeOffRequestStatus.APPROVED
    elif policy.get('auto_approve_under_hours') and data.hours_requested <= policy['auto_approve_under_hours']:
        status = TimeOffRequestStatus.APPROVED
    
    request = TimeOffRequest(
        staff_id=user.id,
        staff_name=user.full_name,
        policy_id=data.policy_id,
        time_off_type=TimeOffType(policy['time_off_type']),
        start_date=data.start_date,
        end_date=data.end_date,
        hours_requested=data.hours_requested,
        reason=data.reason,
        status=status,
        balance_before=current_balance,
        balance_after=current_balance - data.hours_requested if status == TimeOffRequestStatus.APPROVED else current_balance
    )
    
    doc = request.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['start_date'] = doc['start_date'].isoformat()
    doc['end_date'] = doc['end_date'].isoformat()
    doc['time_off_type'] = doc['time_off_type'].value
    doc['status'] = doc['status'].value
    
    await db.time_off_requests.insert_one(doc)
    
    # Update pending hours or balance
    if status == TimeOffRequestStatus.APPROVED:
        # Deduct from balance
        await update_staff_balance(db, user.id, data.policy_id, -data.hours_requested, data.hours_requested)
    else:
        # Add to pending
        await db.time_off_balances.update_one(
            {"staff_id": user.id, "policy_id": data.policy_id},
            {"$inc": {"pending_hours": data.hours_requested}},
            upsert=True
        )
    
    # Trigger notification
    from automation_service import AutomationService
    automation = AutomationService(db)
    await automation.log_event(
        event_type="time_off.requested",
        event_source="hr",
        source_id=request.id,
        user_id=user.id,
        data={
            "staff_name": user.full_name,
            "time_off_type": policy['time_off_type'],
            "start_date": data.start_date.isoformat(),
            "end_date": data.end_date.isoformat(),
            "hours": data.hours_requested,
            "status": status.value
        }
    )
    
    return TimeOffRequestResponse(**request.model_dump())


@router.post("/time-off-requests/{request_id}/review")
async def review_time_off_request(
    request_id: str,
    status: str,  # approved or rejected
    notes: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Review (approve/reject) a time off request (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if status not in ['approved', 'rejected']:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")
    
    request = await db.time_off_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Time off request not found")
    
    if request['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Request is not pending")
    
    # Get current balance for balance_after calculation
    balance = await db.time_off_balances.find_one({
        "staff_id": request['staff_id'],
        "policy_id": request['policy_id']
    }, {"_id": 0})
    
    current_balance = balance.get('balance_hours', 0) if balance else 0
    
    await db.time_off_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": status,
            "reviewed_by": user.id,
            "reviewed_by_name": user.full_name,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_notes": notes,
            "balance_after": current_balance - request['hours_requested'] if status == 'approved' else current_balance,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update balance
    if status == 'approved':
        # Deduct hours and clear pending
        await update_staff_balance(
            db, 
            request['staff_id'], 
            request['policy_id'], 
            -request['hours_requested'],
            request['hours_requested']
        )
        # Remove from pending
        await db.time_off_balances.update_one(
            {"staff_id": request['staff_id'], "policy_id": request['policy_id']},
            {"$inc": {"pending_hours": -request['hours_requested']}}
        )
    else:
        # Just clear pending
        await db.time_off_balances.update_one(
            {"staff_id": request['staff_id'], "policy_id": request['policy_id']},
            {"$inc": {"pending_hours": -request['hours_requested']}}
        )
    
    # Trigger notification
    from automation_service import AutomationService
    automation = AutomationService(db)
    await automation.log_event(
        event_type=f"time_off.{status}",
        event_source="hr",
        source_id=request_id,
        user_id=request['staff_id'],
        data={
            "reviewed_by": user.full_name,
            "status": status,
            "notes": notes
        }
    )
    
    return {"message": f"Time off request {status}"}


@router.post("/time-off-requests/{request_id}/cancel")
async def cancel_time_off_request(
    request_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Cancel a pending time off request"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    request = await db.time_off_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Time off request not found")
    
    # Check access
    if user.role == UserRole.STAFF and request['staff_id'] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if request['status'] not in ['pending', 'approved']:
        raise HTTPException(status_code=400, detail="Request cannot be cancelled")
    
    # If approved, restore balance
    if request['status'] == 'approved':
        await update_staff_balance(
            db,
            request['staff_id'],
            request['policy_id'],
            request['hours_requested'],  # Add back
            -request['hours_requested']  # Reduce used
        )
    else:
        # Clear pending
        await db.time_off_balances.update_one(
            {"staff_id": request['staff_id'], "policy_id": request['policy_id']},
            {"$inc": {"pending_hours": -request['hours_requested']}}
        )
    
    await db.time_off_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "cancelled",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Time off request cancelled"}


# ==================== TIME OFF BALANCES ====================

async def update_staff_balance(db, staff_id: str, policy_id: str, balance_delta: float, used_delta: float):
    """Update staff time off balance"""
    await db.time_off_balances.update_one(
        {"staff_id": staff_id, "policy_id": policy_id},
        {
            "$inc": {
                "balance_hours": balance_delta,
                "used_ytd": used_delta
            },
            "$set": {
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )


@router.get("/balances", response_model=List[TimeOffBalanceResponse])
async def get_my_balances(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get current user's time off balances"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    balances = await db.time_off_balances.find(
        {"staff_id": user.id}, {"_id": 0}
    ).to_list(100)
    
    return [TimeOffBalanceResponse(**b) for b in balances]


@router.get("/balances/{staff_id}", response_model=List[TimeOffBalanceResponse])
async def get_staff_balances(
    staff_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a staff member's time off balances (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    if user.role != UserRole.ADMIN and user.id != staff_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    balances = await db.time_off_balances.find(
        {"staff_id": staff_id}, {"_id": 0}
    ).to_list(100)
    
    return [TimeOffBalanceResponse(**b) for b in balances]


@router.post("/balances/{staff_id}/adjust")
async def adjust_staff_balance(
    staff_id: str,
    policy_id: str,
    adjustment: float,
    reason: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Manually adjust a staff member's time off balance (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Verify staff exists
    staff = await db.users.find_one({"id": staff_id}, {"_id": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Verify policy exists
    policy = await db.time_off_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Time off policy not found")
    
    # Get or create balance record
    balance = await db.time_off_balances.find_one({
        "staff_id": staff_id,
        "policy_id": policy_id
    }, {"_id": 0})
    
    if balance:
        new_balance = balance.get('balance_hours', 0) + adjustment
        await db.time_off_balances.update_one(
            {"staff_id": staff_id, "policy_id": policy_id},
            {"$set": {
                "balance_hours": new_balance,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    else:
        new_balance = max(0, adjustment)
        balance_doc = TimeOffBalance(
            staff_id=staff_id,
            policy_id=policy_id,
            time_off_type=TimeOffType(policy['time_off_type']),
            balance_hours=new_balance
        ).model_dump()
        balance_doc['created_at'] = balance_doc['created_at'].isoformat()
        balance_doc['updated_at'] = balance_doc['updated_at'].isoformat()
        balance_doc['time_off_type'] = balance_doc['time_off_type'].value
        await db.time_off_balances.insert_one(balance_doc)
    
    # Log adjustment in audit
    from models import AuditAction, AuditLog
    audit = AuditLog(
        user_id=user.id,
        action=AuditAction.UPDATE,
        resource_type="time_off_balance",
        resource_id=staff_id,
        details={
            "policy_id": policy_id,
            "adjustment": adjustment,
            "reason": reason,
            "new_balance": new_balance
        }
    )
    audit_doc = audit.model_dump()
    audit_doc['created_at'] = audit_doc['created_at'].isoformat()
    audit_doc['updated_at'] = audit_doc['updated_at'].isoformat()
    audit_doc['action'] = audit_doc['action'].value
    await db.audit_logs.insert_one(audit_doc)
    
    return {
        "message": f"Balance adjusted by {adjustment} hours",
        "new_balance": new_balance
    }


@router.post("/balances/run-accrual")
async def run_accrual(
    policy_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Run time off accrual for all staff (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get active policies
    policy_query = {"is_active": True}
    if policy_id:
        policy_query["id"] = policy_id
    
    policies = await db.time_off_policies.find(policy_query, {"_id": 0}).to_list(100)
    
    # Get all active staff
    staff_members = await db.users.find({
        "is_active": True,
        "role": {"$in": ["staff", "admin"]}
    }, {"_id": 0}).to_list(1000)
    
    accrued_count = 0
    
    for policy in policies:
        accrual_rate = policy.get('accrual_rate', 0)
        if accrual_rate <= 0:
            continue
        
        for staff in staff_members:
            # Get current balance
            balance = await db.time_off_balances.find_one({
                "staff_id": staff['id'],
                "policy_id": policy['id']
            }, {"_id": 0})
            
            current_balance = balance.get('balance_hours', 0) if balance else 0
            current_accrued = balance.get('accrued_ytd', 0) if balance else 0
            
            # Check max balance
            max_balance = policy.get('max_balance')
            if max_balance and current_balance >= max_balance:
                continue
            
            # Calculate accrual
            new_accrual = accrual_rate
            if max_balance:
                new_accrual = min(new_accrual, max_balance - current_balance)
            
            # Update balance
            await db.time_off_balances.update_one(
                {"staff_id": staff['id'], "policy_id": policy['id']},
                {
                    "$inc": {
                        "balance_hours": new_accrual,
                        "accrued_ytd": new_accrual
                    },
                    "$set": {
                        "time_off_type": policy['time_off_type'],
                        "last_accrual_date": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                },
                upsert=True
            )
            accrued_count += 1
    
    return {
        "message": f"Accrual completed for {accrued_count} balance records",
        "policies_processed": len(policies),
        "staff_processed": len(staff_members)
    }


# ==================== REPORTS ====================

@router.get("/reports/time-off-summary")
async def get_time_off_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get time off summary report (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {"status": "approved"}
    if start_date:
        query["start_date"] = {"$gte": start_date}
    if end_date:
        if "end_date" not in query:
            query["end_date"] = {}
        query["end_date"]["$lte"] = end_date
    
    requests = await db.time_off_requests.find(query, {"_id": 0}).to_list(5000)
    
    # Aggregate by type and staff
    by_type = {}
    by_staff = {}
    total_hours = 0
    
    for req in requests:
        time_off_type = req.get('time_off_type', 'unknown')
        staff_name = req.get('staff_name', 'Unknown')
        hours = req.get('hours_requested', 0)
        
        by_type[time_off_type] = by_type.get(time_off_type, 0) + hours
        by_staff[staff_name] = by_staff.get(staff_name, 0) + hours
        total_hours += hours
    
    return {
        "total_requests": len(requests),
        "total_hours": round(total_hours, 2),
        "by_type": by_type,
        "by_staff": dict(sorted(by_staff.items(), key=lambda x: x[1], reverse=True)[:20])
    }
