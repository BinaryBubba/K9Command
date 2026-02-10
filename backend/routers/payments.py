"""
Payments Router - K9Command
Handles Square payments, card-on-file, deposits, refunds
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timezone

from models import UserRole
from auth import get_current_user
from services.payments import SquarePaymentService as PaymentService

router = APIRouter(prefix="/api/k9", tags=["Payments"])
security = HTTPBearer()


def get_db():
    """Get database connection"""
    from server import db
    return db


@router.get("/payments/config")
async def get_payment_config():
    """Get payment configuration (Square app ID for frontend)"""
    service = PaymentService(get_db())
    return service.get_config()


@router.post("/payments/cards")
async def save_payment_card(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Save a payment card for future use"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    source_id = data.get("source_id")
    if not source_id:
        raise HTTPException(status_code=400, detail="source_id required")
    
    service = PaymentService(db)
    
    result = await service.save_card(
        customer_id=user.id,
        source_id=source_id,
        cardholder_name=data.get("cardholder_name"),
        billing_address=data.get("billing_address")
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to save card"))
    
    return result


@router.get("/payments/cards")
async def get_saved_cards(
    customer_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get saved payment cards"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    target_id = customer_id if (customer_id and user.role == UserRole.ADMIN) else user.id
    
    service = PaymentService(db)
    cards = await service.get_customer_cards(target_id)
    
    return {"cards": cards}


@router.delete("/payments/cards/{card_id}")
async def delete_saved_card(
    card_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a saved payment card"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    service = PaymentService(db)
    result = await service.delete_card(user.id, card_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to delete card"))
    
    return {"message": "Card deleted"}


@router.post("/payments/deposit-hold")
async def create_deposit_hold(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a deposit hold (authorization) on a card"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    card_id = data.get("card_id")
    amount_cents = data.get("amount_cents")
    booking_id = data.get("booking_id")
    
    if not card_id or not amount_cents:
        raise HTTPException(status_code=400, detail="card_id and amount_cents required")
    
    service = PaymentService(db)
    result = await service.create_authorization(
        customer_id=user.id,
        card_id=card_id,
        amount_cents=amount_cents,
        booking_id=booking_id
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create hold"))
    
    return result


@router.post("/payments/capture/{authorization_id}")
async def capture_deposit(
    authorization_id: str,
    data: Optional[dict] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Capture a previously authorized payment"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    amount_cents = data.get("amount_cents") if data else None
    
    service = PaymentService(db)
    result = await service.capture_authorization(authorization_id, amount_cents)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to capture"))
    
    return result


@router.post("/payments/cancel/{authorization_id}")
async def cancel_authorization(
    authorization_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Cancel a pending authorization"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = PaymentService(db)
    result = await service.cancel_authorization(authorization_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to cancel"))
    
    return result


@router.post("/payments/charge")
async def charge_card(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Charge a saved card directly"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    card_id = data.get("card_id")
    amount_cents = data.get("amount_cents")
    booking_id = data.get("booking_id")
    note = data.get("note")
    
    if not card_id or not amount_cents:
        raise HTTPException(status_code=400, detail="card_id and amount_cents required")
    
    customer_id = data.get("customer_id") if user.role == UserRole.ADMIN else user.id
    
    service = PaymentService(db)
    result = await service.charge_card(
        customer_id=customer_id,
        card_id=card_id,
        amount_cents=amount_cents,
        booking_id=booking_id,
        note=note
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Charge failed"))
    
    return result


@router.post("/payments/refund")
async def process_refund(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Process a refund"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    payment_id = data.get("payment_id")
    amount_cents = data.get("amount_cents")
    reason = data.get("reason")
    
    if not payment_id:
        raise HTTPException(status_code=400, detail="payment_id required")
    
    service = PaymentService(db)
    result = await service.refund_payment(payment_id, amount_cents, reason)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Refund failed"))
    
    return result


@router.get("/payments/booking/{booking_id}")
async def get_booking_payments(
    booking_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all payments for a booking"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    payments = await db.payments.find(
        {"booking_id": booking_id},
        {"_id": 0}
    ).to_list(50)
    
    return {"payments": payments, "booking_id": booking_id}
