"""
CRM Router - K9Command
Handles leads, customer lifecycle, retention metrics
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timezone

from models import UserRole
from auth import get_current_user
from services.pos_crm import CRMService

router = APIRouter(prefix="/api/k9", tags=["CRM & Leads"])
security = HTTPBearer()


def get_db():
    """Get database connection"""
    from server import db
    return db


@router.post("/crm/leads")
async def create_lead(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new lead"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = CRMService(db)
    lead = await service.create_lead(data, user.id)
    
    return {"message": "Lead created", "lead": lead}


@router.get("/crm/leads")
async def list_leads(
    status: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 100,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get leads with optional filters"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = CRMService(db)
    leads = await service.get_leads(status, source, limit)
    
    return {"leads": leads, "count": len(leads)}


@router.put("/crm/leads/{lead_id}/status")
async def update_lead_status(
    lead_id: str,
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update lead status"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = CRMService(db)
    result = await service.update_lead_status(
        lead_id,
        data.get('status', 'new'),
        data.get('notes')
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Lead updated", "lead": result}


@router.post("/crm/leads/{lead_id}/convert")
async def convert_lead(
    lead_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Convert a lead to a customer"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = CRMService(db)
    result = await service.convert_lead_to_customer(lead_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Lead converted to customer", "lead": result}


@router.get("/crm/customers/{customer_id}/metrics")
async def get_customer_metrics(
    customer_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get CRM metrics for a customer"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = CRMService(db)
    metrics = await service.get_customer_metrics(customer_id)
    
    if not metrics:
        return {
            "customer_id": customer_id,
            "total_visits": 0,
            "total_spent_cents": 0,
            "lifecycle_stage": "new",
            "message": "No activity recorded"
        }
    
    return metrics.dict()


@router.get("/crm/retention-metrics")
async def get_retention_metrics(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get overall retention and CRM metrics"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = CRMService(db)
    metrics = await service.get_retention_metrics()
    
    return metrics
