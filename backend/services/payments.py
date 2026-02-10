"""
Square Payment Service
Handles card-on-file vaulting, deposits, pre-authorization holds, and payment processing.
"""
import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from enum import Enum

# Square SDK - optional import for when credentials are configured
try:
    from square.client import Client as SquareClient
    SQUARE_AVAILABLE = True
except ImportError:
    SQUARE_AVAILABLE = False


class PaymentStatus(str, Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled"


class CardStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    EXPIRED = "expired"


class SavedCardCreate(BaseModel):
    source_id: str  # Token from frontend
    customer_id: str
    customer_email: str
    cardholder_name: Optional[str] = None
    billing_postal_code: Optional[str] = None


class SavedCardResponse(BaseModel):
    id: str
    card_id: str
    customer_id: str
    card_brand: str
    last_4: str
    exp_month: int
    exp_year: int
    status: CardStatus
    created_at: str


class DepositHoldCreate(BaseModel):
    customer_id: str
    card_id: str
    booking_id: str
    amount_cents: int
    currency: str = "USD"
    note: Optional[str] = None


class PaymentCreate(BaseModel):
    customer_id: str
    card_id: str
    booking_id: str
    amount_cents: int
    authorization_id: Optional[str] = None  # If completing a pre-auth
    currency: str = "USD"
    note: Optional[str] = None


class RefundCreate(BaseModel):
    payment_id: str
    amount_cents: int
    reason: Optional[str] = None


class SquarePaymentService:
    """
    Square payment service with fallback to mock mode when credentials aren't configured.
    """
    
    def __init__(self, db):
        self.db = db
        self.square_client = None
        self.mock_mode = True
        
        # Initialize Square client if credentials are available
        access_token = os.environ.get('SQUARE_ACCESS_TOKEN')
        environment = os.environ.get('SQUARE_ENVIRONMENT', 'sandbox')
        
        if SQUARE_AVAILABLE and access_token:
            try:
                self.square_client = SquareClient(
                    access_token=access_token,
                    environment=environment
                )
                self.mock_mode = False
            except Exception as e:
                print(f"Square client initialization failed: {e}")
                self.mock_mode = True
        
        self.location_id = os.environ.get('SQUARE_LOCATION_ID', 'MOCK_LOCATION')
        self.application_id = os.environ.get('SQUARE_APPLICATION_ID', 'MOCK_APP_ID')
    
    def get_config(self) -> Dict[str, Any]:
        """Get Square configuration for frontend"""
        return {
            "application_id": self.application_id,
            "location_id": self.location_id,
            "environment": os.environ.get('SQUARE_ENVIRONMENT', 'sandbox'),
            "mock_mode": self.mock_mode
        }
    
    async def save_card(self, data: SavedCardCreate) -> SavedCardResponse:
        """Save a card on file for a customer"""
        card_record_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        if self.mock_mode:
            # Mock card saving
            card_id = f"ccof:{uuid.uuid4().hex[:20]}"
            card_data = {
                "id": card_record_id,
                "card_id": card_id,
                "square_card_id": card_id,
                "customer_id": data.customer_id,
                "card_brand": "VISA",
                "last_4": "1111",
                "exp_month": 12,
                "exp_year": 2027,
                "status": CardStatus.ACTIVE,
                "created_at": now,
                "mock": True
            }
        else:
            # Real Square API call
            try:
                # First ensure customer exists in Square
                square_customer_id = await self._ensure_square_customer(
                    data.customer_id, 
                    data.customer_email
                )
                
                # Create card on file
                result = self.square_client.cards.create_card(
                    body={
                        "idempotency_key": str(uuid.uuid4()),
                        "source_id": data.source_id,
                        "card": {
                            "customer_id": square_customer_id,
                            "cardholder_name": data.cardholder_name or "Card Holder",
                            "billing_address": {
                                "postal_code": data.billing_postal_code or "00000"
                            }
                        }
                    }
                )
                
                if result.is_error():
                    raise Exception(f"Square API error: {result.errors}")
                
                card = result.body.get('card', {})
                card_id = card.get('id')
                
                card_data = {
                    "id": card_record_id,
                    "card_id": card_id,
                    "square_card_id": card_id,
                    "square_customer_id": square_customer_id,
                    "customer_id": data.customer_id,
                    "card_brand": card.get('card_brand', 'UNKNOWN'),
                    "last_4": card.get('last_4', '****'),
                    "exp_month": int(card.get('exp_month', 12)),
                    "exp_year": int(card.get('exp_year', 2025)),
                    "status": CardStatus.ACTIVE,
                    "created_at": now,
                    "mock": False
                }
            except Exception as e:
                raise Exception(f"Failed to save card: {str(e)}")
        
        # Store in database
        await self.db.saved_cards.insert_one(card_data)
        
        return SavedCardResponse(**card_data)
    
    async def _ensure_square_customer(self, customer_id: str, email: str) -> str:
        """Ensure customer exists in Square, create if not"""
        if self.mock_mode:
            return f"MOCK_CUSTOMER_{customer_id}"
        
        # Check if we have a mapping
        mapping = await self.db.square_customer_mappings.find_one(
            {"customer_id": customer_id},
            {"_id": 0}
        )
        
        if mapping:
            return mapping['square_customer_id']
        
        # Create new Square customer
        result = self.square_client.customers.create_customer(
            body={
                "idempotency_key": str(uuid.uuid4()),
                "email_address": email,
                "reference_id": customer_id
            }
        )
        
        if result.is_error():
            raise Exception(f"Failed to create Square customer: {result.errors}")
        
        square_customer_id = result.body.get('customer', {}).get('id')
        
        # Save mapping
        await self.db.square_customer_mappings.insert_one({
            "customer_id": customer_id,
            "square_customer_id": square_customer_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return square_customer_id
    
    async def get_customer_cards(self, customer_id: str) -> List[SavedCardResponse]:
        """Get all saved cards for a customer"""
        cards = await self.db.saved_cards.find(
            {"customer_id": customer_id, "status": CardStatus.ACTIVE},
            {"_id": 0}
        ).to_list(50)
        
        return [SavedCardResponse(**card) for card in cards]
    
    async def delete_card(self, customer_id: str, card_id: str) -> bool:
        """Disable a saved card"""
        result = await self.db.saved_cards.update_one(
            {"customer_id": customer_id, "card_id": card_id},
            {"$set": {"status": CardStatus.DISABLED, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        if not self.mock_mode and result.modified_count > 0:
            # Also disable in Square
            try:
                self.square_client.cards.disable_card(card_id=card_id)
            except:
                pass  # Card may already be disabled
        
        return result.modified_count > 0
    
    async def create_deposit_hold(self, data: DepositHoldCreate) -> Dict[str, Any]:
        """Create a pre-authorization hold (delayed capture) for a deposit"""
        authorization_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        hold_expires = now + timedelta(days=7)
        
        if self.mock_mode:
            # Mock authorization
            auth_data = {
                "id": authorization_id,
                "square_payment_id": f"mock_auth_{authorization_id[:8]}",
                "customer_id": data.customer_id,
                "card_id": data.card_id,
                "booking_id": data.booking_id,
                "amount_cents": data.amount_cents,
                "currency": data.currency,
                "status": PaymentStatus.AUTHORIZED,
                "hold_expires_at": hold_expires.isoformat(),
                "created_at": now.isoformat(),
                "mock": True
            }
        else:
            # Real Square API - delayed capture
            try:
                # Get the Square card ID
                card = await self.db.saved_cards.find_one(
                    {"card_id": data.card_id},
                    {"_id": 0}
                )
                
                if not card:
                    raise Exception("Card not found")
                
                result = self.square_client.payments.create_payment(
                    body={
                        "source_id": card['square_card_id'],
                        "idempotency_key": str(uuid.uuid4()),
                        "amount_money": {
                            "amount": data.amount_cents,
                            "currency": data.currency
                        },
                        "autocomplete": False,  # Delayed capture
                        "customer_id": card.get('square_customer_id'),
                        "reference_id": data.booking_id,
                        "note": data.note or f"Deposit hold for booking {data.booking_id}",
                        "location_id": self.location_id
                    }
                )
                
                if result.is_error():
                    raise Exception(f"Square API error: {result.errors}")
                
                payment = result.body.get('payment', {})
                
                auth_data = {
                    "id": authorization_id,
                    "square_payment_id": payment.get('id'),
                    "customer_id": data.customer_id,
                    "card_id": data.card_id,
                    "booking_id": data.booking_id,
                    "amount_cents": data.amount_cents,
                    "currency": data.currency,
                    "status": PaymentStatus.AUTHORIZED,
                    "hold_expires_at": hold_expires.isoformat(),
                    "created_at": now.isoformat(),
                    "receipt_url": payment.get('receipt_url'),
                    "mock": False
                }
            except Exception as e:
                raise Exception(f"Failed to create deposit hold: {str(e)}")
        
        # Store authorization
        await self.db.payment_authorizations.insert_one(auth_data)
        
        # Remove MongoDB _id before returning
        auth_data.pop('_id', None)
        return auth_data
    
    async def capture_authorization(self, authorization_id: str) -> Dict[str, Any]:
        """Capture a previously authorized payment"""
        auth = await self.db.payment_authorizations.find_one(
            {"id": authorization_id},
            {"_id": 0}
        )
        
        if not auth:
            raise Exception("Authorization not found")
        
        if auth['status'] != PaymentStatus.AUTHORIZED:
            raise Exception(f"Cannot capture authorization with status: {auth['status']}")
        
        now = datetime.now(timezone.utc)
        
        if self.mock_mode or auth.get('mock'):
            # Mock capture
            payment_id = f"mock_payment_{uuid.uuid4().hex[:8]}"
        else:
            # Real Square API capture
            try:
                result = self.square_client.payments.complete_payment(
                    payment_id=auth['square_payment_id']
                )
                
                if result.is_error():
                    raise Exception(f"Square API error: {result.errors}")
                
                payment_id = result.body.get('payment', {}).get('id')
            except Exception as e:
                raise Exception(f"Failed to capture payment: {str(e)}")
        
        # Update authorization status
        await self.db.payment_authorizations.update_one(
            {"id": authorization_id},
            {"$set": {
                "status": PaymentStatus.CAPTURED,
                "captured_at": now.isoformat(),
                "captured_payment_id": payment_id
            }}
        )
        
        return {
            "authorization_id": authorization_id,
            "payment_id": payment_id,
            "status": PaymentStatus.CAPTURED,
            "captured_at": now.isoformat()
        }
    
    async def cancel_authorization(self, authorization_id: str) -> Dict[str, Any]:
        """Cancel/void a pre-authorization hold"""
        auth = await self.db.payment_authorizations.find_one(
            {"id": authorization_id},
            {"_id": 0}
        )
        
        if not auth:
            raise Exception("Authorization not found")
        
        if auth['status'] != PaymentStatus.AUTHORIZED:
            raise Exception(f"Cannot cancel authorization with status: {auth['status']}")
        
        now = datetime.now(timezone.utc)
        
        if not self.mock_mode and not auth.get('mock'):
            # Real Square API cancel
            try:
                result = self.square_client.payments.cancel_payment(
                    payment_id=auth['square_payment_id']
                )
                
                if result.is_error():
                    raise Exception(f"Square API error: {result.errors}")
            except Exception as e:
                raise Exception(f"Failed to cancel authorization: {str(e)}")
        
        # Update status
        await self.db.payment_authorizations.update_one(
            {"id": authorization_id},
            {"$set": {
                "status": PaymentStatus.CANCELED,
                "canceled_at": now.isoformat()
            }}
        )
        
        return {
            "authorization_id": authorization_id,
            "status": PaymentStatus.CANCELED,
            "canceled_at": now.isoformat()
        }
    
    async def create_payment(self, data: PaymentCreate) -> Dict[str, Any]:
        """Create a direct payment (immediate capture)"""
        payment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        if self.mock_mode:
            # Mock payment
            payment_data = {
                "id": payment_id,
                "square_payment_id": f"mock_pay_{payment_id[:8]}",
                "customer_id": data.customer_id,
                "card_id": data.card_id,
                "booking_id": data.booking_id,
                "amount_cents": data.amount_cents,
                "currency": data.currency,
                "status": PaymentStatus.COMPLETED,
                "created_at": now.isoformat(),
                "mock": True
            }
        else:
            try:
                # Get card details
                card = await self.db.saved_cards.find_one(
                    {"card_id": data.card_id},
                    {"_id": 0}
                )
                
                if not card:
                    raise Exception("Card not found")
                
                result = self.square_client.payments.create_payment(
                    body={
                        "source_id": card['square_card_id'],
                        "idempotency_key": str(uuid.uuid4()),
                        "amount_money": {
                            "amount": data.amount_cents,
                            "currency": data.currency
                        },
                        "autocomplete": True,  # Immediate capture
                        "customer_id": card.get('square_customer_id'),
                        "reference_id": data.booking_id,
                        "note": data.note or f"Payment for booking {data.booking_id}",
                        "location_id": self.location_id
                    }
                )
                
                if result.is_error():
                    raise Exception(f"Square API error: {result.errors}")
                
                payment = result.body.get('payment', {})
                
                payment_data = {
                    "id": payment_id,
                    "square_payment_id": payment.get('id'),
                    "customer_id": data.customer_id,
                    "card_id": data.card_id,
                    "booking_id": data.booking_id,
                    "amount_cents": data.amount_cents,
                    "currency": data.currency,
                    "status": PaymentStatus.COMPLETED,
                    "created_at": now.isoformat(),
                    "receipt_url": payment.get('receipt_url'),
                    "mock": False
                }
            except Exception as e:
                raise Exception(f"Payment failed: {str(e)}")
        
        # Store payment
        await self.db.payments.insert_one(payment_data)
        
        return payment_data
    
    async def refund_payment(self, data: RefundCreate) -> Dict[str, Any]:
        """Refund a completed payment (full or partial)"""
        refund_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Get original payment
        payment = await self.db.payments.find_one(
            {"id": data.payment_id},
            {"_id": 0}
        )
        
        if not payment:
            raise Exception("Payment not found")
        
        if payment['status'] not in [PaymentStatus.COMPLETED, PaymentStatus.CAPTURED]:
            raise Exception(f"Cannot refund payment with status: {payment['status']}")
        
        if self.mock_mode or payment.get('mock'):
            # Mock refund
            refund_data = {
                "id": refund_id,
                "square_refund_id": f"mock_refund_{refund_id[:8]}",
                "payment_id": data.payment_id,
                "amount_cents": data.amount_cents,
                "reason": data.reason,
                "status": "COMPLETED",
                "created_at": now.isoformat(),
                "mock": True
            }
        else:
            try:
                result = self.square_client.refunds.refund_payment(
                    body={
                        "idempotency_key": str(uuid.uuid4()),
                        "payment_id": payment['square_payment_id'],
                        "amount_money": {
                            "amount": data.amount_cents,
                            "currency": payment.get('currency', 'USD')
                        },
                        "reason": data.reason or "Customer request"
                    }
                )
                
                if result.is_error():
                    raise Exception(f"Square API error: {result.errors}")
                
                refund = result.body.get('refund', {})
                
                refund_data = {
                    "id": refund_id,
                    "square_refund_id": refund.get('id'),
                    "payment_id": data.payment_id,
                    "amount_cents": data.amount_cents,
                    "reason": data.reason,
                    "status": refund.get('status', 'PENDING'),
                    "created_at": now.isoformat(),
                    "mock": False
                }
            except Exception as e:
                raise Exception(f"Refund failed: {str(e)}")
        
        # Store refund
        await self.db.refunds.insert_one(refund_data)
        
        # Update payment status if full refund
        if data.amount_cents >= payment['amount_cents']:
            await self.db.payments.update_one(
                {"id": data.payment_id},
                {"$set": {"status": PaymentStatus.REFUNDED}}
            )
        
        return refund_data
    
    async def get_booking_payments(self, booking_id: str) -> Dict[str, Any]:
        """Get all payment activity for a booking"""
        authorizations = await self.db.payment_authorizations.find(
            {"booking_id": booking_id},
            {"_id": 0}
        ).to_list(50)
        
        payments = await self.db.payments.find(
            {"booking_id": booking_id},
            {"_id": 0}
        ).to_list(50)
        
        return {
            "booking_id": booking_id,
            "authorizations": authorizations,
            "payments": payments,
            "total_authorized": sum(a['amount_cents'] for a in authorizations if a['status'] == PaymentStatus.AUTHORIZED),
            "total_captured": sum(a['amount_cents'] for a in authorizations if a['status'] == PaymentStatus.CAPTURED),
            "total_paid": sum(p['amount_cents'] for p in payments if p['status'] == PaymentStatus.COMPLETED)
        }
