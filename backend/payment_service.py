"""
Payment Service Abstraction Layer
Supports Square (primary) and future Crypto (USDC) payments
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import os
import logging
import uuid

logger = logging.getLogger(__name__)


class PaymentProvider(ABC):
    """Abstract base class for payment providers"""
    
    @abstractmethod
    async def create_payment(
        self,
        amount: float,
        currency: str,
        reference_id: str,
        customer_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a payment"""
        pass
    
    @abstractmethod
    async def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        """Capture an authorized payment"""
        pass
    
    @abstractmethod
    async def refund_payment(
        self,
        payment_id: str,
        amount: float = None,
        reason: str = None
    ) -> Dict[str, Any]:
        """Refund a payment (full or partial)"""
        pass
    
    @abstractmethod
    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Get payment details"""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured"""
        pass


class SquarePaymentProvider(PaymentProvider):
    """Square payment provider implementation"""
    
    def __init__(self):
        self.access_token = os.environ.get('SQUARE_ACCESS_TOKEN', '')
        self.environment = os.environ.get('SQUARE_ENVIRONMENT', 'sandbox')
        self.location_id = os.environ.get('SQUARE_LOCATION_ID', '')
        self._client = None
    
    def is_configured(self) -> bool:
        return bool(self.access_token)
    
    def _get_client(self):
        """Lazy load Square client"""
        if not self._client and self.is_configured():
            try:
                from square import Square
                self._client = Square(
                    access_token=self.access_token,
                    environment=self.environment
                )
            except ImportError:
                logger.error("Square SDK not installed")
                return None
        return self._client
    
    async def create_payment(
        self,
        amount: float,
        currency: str,
        reference_id: str,
        source_id: str = None,
        customer_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a Square payment"""
        client = self._get_client()
        if not client:
            raise Exception("Square client not configured")
        
        if not source_id:
            raise Exception("Square requires a source_id (payment token)")
        
        idempotency_key = f"{reference_id}:{str(uuid.uuid4())}"
        
        request_body = {
            "source_id": source_id,
            "amount_money": {
                "amount": int(amount * 100),  # Convert to cents
                "currency": currency
            },
            "idempotency_key": idempotency_key,
            "reference_id": reference_id,
        }
        
        if self.location_id:
            request_body["location_id"] = self.location_id
        
        if customer_id:
            request_body["customer_id"] = customer_id
        
        if metadata:
            request_body["note"] = str(metadata.get('note', ''))[:500]
        
        result = client.payments.create_payment(request_body)
        
        if result.is_success:
            payment = result.body.get('payment', {})
            return {
                "success": True,
                "payment_id": payment.get('id'),
                "status": payment.get('status', 'COMPLETED').lower(),
                "amount": amount,
                "currency": currency,
                "provider": "square",
                "provider_data": payment,
                "receipt_url": payment.get('receipt_url')
            }
        else:
            errors = result.errors or []
            error_msg = errors[0].get('detail', 'Payment failed') if errors else 'Payment failed'
            return {
                "success": False,
                "error": error_msg,
                "provider": "square"
            }
    
    async def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        """Capture an authorized payment (not typically needed for Square)"""
        # Square payments are typically auto-captured
        return {"success": True, "payment_id": payment_id, "status": "captured"}
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: float = None,
        reason: str = None
    ) -> Dict[str, Any]:
        """Create a refund for a Square payment"""
        client = self._get_client()
        if not client:
            raise Exception("Square client not configured")
        
        idempotency_key = f"refund_{payment_id}:{str(uuid.uuid4())}"
        
        request_body = {
            "payment_id": payment_id,
            "idempotency_key": idempotency_key,
        }
        
        if amount:
            # Get original payment to get currency
            original = await self.get_payment(payment_id)
            request_body["amount_money"] = {
                "amount": int(amount * 100),
                "currency": original.get('currency', 'USD')
            }
        
        if reason:
            request_body["reason"] = reason[:192]  # Square limit
        
        result = client.refunds.refund_payment(request_body)
        
        if result.is_success:
            refund = result.body.get('refund', {})
            return {
                "success": True,
                "refund_id": refund.get('id'),
                "status": refund.get('status', 'COMPLETED').lower(),
                "amount": amount or (refund.get('amount_money', {}).get('amount', 0) / 100),
                "provider": "square",
                "provider_data": refund
            }
        else:
            errors = result.errors or []
            error_msg = errors[0].get('detail', 'Refund failed') if errors else 'Refund failed'
            return {
                "success": False,
                "error": error_msg,
                "provider": "square"
            }
    
    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Get payment details from Square"""
        client = self._get_client()
        if not client:
            raise Exception("Square client not configured")
        
        result = client.payments.get_payment(payment_id)
        
        if result.is_success:
            payment = result.body.get('payment', {})
            amount_money = payment.get('amount_money', {})
            return {
                "success": True,
                "payment_id": payment.get('id'),
                "status": payment.get('status', '').lower(),
                "amount": amount_money.get('amount', 0) / 100,
                "currency": amount_money.get('currency', 'USD'),
                "provider": "square",
                "provider_data": payment
            }
        else:
            return {"success": False, "error": "Payment not found"}


class CryptoPaymentProvider(PaymentProvider):
    """
    Crypto payment provider (USDC) - Infrastructure placeholder.
    Full implementation deferred to Phase 4+.
    """
    
    def __init__(self):
        self.wallet_address = os.environ.get('CRYPTO_WALLET_ADDRESS', '')
        self.network = os.environ.get('CRYPTO_NETWORK', 'ethereum')  # ethereum, polygon, solana, etc.
        self.usdc_contract = os.environ.get('USDC_CONTRACT_ADDRESS', '')
    
    def is_configured(self) -> bool:
        # Infrastructure exists but not fully implemented
        return bool(self.wallet_address)
    
    async def create_payment(
        self,
        amount: float,
        currency: str,
        reference_id: str,
        customer_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create a crypto payment request.
        This creates a payment intent that the customer completes via wallet.
        """
        if currency.upper() not in ('USDC', 'USD'):
            return {"success": False, "error": "Only USDC payments supported"}
        
        # Generate unique payment reference
        payment_id = f"crypto_{str(uuid.uuid4())[:8]}_{reference_id}"
        
        # In full implementation:
        # 1. Create payment intent in database
        # 2. Return wallet address and amount for customer to send
        # 3. Set up webhook/polling to detect payment
        
        return {
            "success": True,
            "payment_id": payment_id,
            "status": "pending",
            "amount": amount,
            "currency": "USDC",
            "provider": "crypto",
            "wallet_address": self.wallet_address,
            "network": self.network,
            "instructions": "Send exact amount in USDC to the wallet address. Include the payment ID in the memo.",
            "expires_at": (datetime.now(timezone.utc).isoformat()),
            "note": "CRYPTO PAYMENTS NOT YET FULLY IMPLEMENTED - Infrastructure placeholder"
        }
    
    async def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        """Crypto payments don't need capture - they're confirmed on-chain"""
        return {"success": True, "payment_id": payment_id, "status": "completed"}
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: float = None,
        reason: str = None
    ) -> Dict[str, Any]:
        """
        Refund crypto payment.
        In full implementation, this would trigger an on-chain transfer.
        """
        return {
            "success": False,
            "error": "Crypto refunds require manual processing. Contact admin.",
            "provider": "crypto",
            "note": "CRYPTO REFUNDS NOT YET IMPLEMENTED"
        }
    
    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Get crypto payment status - would check on-chain in full implementation"""
        return {
            "success": False,
            "error": "Payment lookup not yet implemented",
            "provider": "crypto"
        }


class MockPaymentProvider(PaymentProvider):
    """Mock payment provider for testing and demo"""
    
    def is_configured(self) -> bool:
        return True
    
    async def create_payment(
        self,
        amount: float,
        currency: str,
        reference_id: str,
        customer_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        payment_id = f"mock_pay_{str(uuid.uuid4())[:8]}"
        return {
            "success": True,
            "payment_id": payment_id,
            "status": "completed",
            "amount": amount,
            "currency": currency,
            "provider": "mock",
            "mock": True
        }
    
    async def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        return {"success": True, "payment_id": payment_id, "status": "captured", "mock": True}
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: float = None,
        reason: str = None
    ) -> Dict[str, Any]:
        refund_id = f"mock_refund_{str(uuid.uuid4())[:8]}"
        return {
            "success": True,
            "refund_id": refund_id,
            "status": "completed",
            "amount": amount,
            "provider": "mock",
            "mock": True
        }
    
    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        return {
            "success": True,
            "payment_id": payment_id,
            "status": "completed",
            "provider": "mock",
            "mock": True
        }


class PaymentService:
    """
    Unified payment service that abstracts provider selection.
    Use this class for all payment operations.
    """
    
    def __init__(self, db=None):
        self.db = db
        self._providers = {
            "square": SquarePaymentProvider(),
            "crypto": CryptoPaymentProvider(),
            "mock": MockPaymentProvider()
        }
    
    def get_provider(self, provider_name: str) -> PaymentProvider:
        """Get a specific payment provider"""
        provider = self._providers.get(provider_name.lower())
        if not provider:
            raise ValueError(f"Unknown payment provider: {provider_name}")
        return provider
    
    def get_available_providers(self) -> Dict[str, bool]:
        """Get list of configured providers"""
        return {
            name: provider.is_configured()
            for name, provider in self._providers.items()
        }
    
    async def process_payment(
        self,
        provider_name: str,
        amount: float,
        currency: str,
        booking_id: str,
        payment_type: str,  # deposit, balance, full
        source_id: str = None,  # Required for Square
        customer_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a payment through the specified provider.
        Falls back to mock if provider not configured.
        """
        provider = self.get_provider(provider_name)
        
        if not provider.is_configured() and provider_name != 'mock':
            logger.warning(f"{provider_name} not configured, falling back to mock")
            provider = self._providers['mock']
        
        # Add payment type to metadata
        metadata = metadata or {}
        metadata['payment_type'] = payment_type
        metadata['booking_id'] = booking_id
        
        if provider_name == 'square' and source_id:
            result = await provider.create_payment(
                amount=amount,
                currency=currency,
                reference_id=booking_id,
                source_id=source_id,
                customer_id=customer_id,
                metadata=metadata
            )
        else:
            result = await provider.create_payment(
                amount=amount,
                currency=currency,
                reference_id=booking_id,
                customer_id=customer_id,
                metadata=metadata
            )
        
        # Record payment in database if we have db access
        if self.db and result.get('success'):
            from models import Payment, PaymentType, PaymentProvider as PaymentProviderEnum
            
            payment_record = {
                "id": str(uuid.uuid4()),
                "booking_id": booking_id,
                "household_id": metadata.get('household_id', ''),
                "amount": amount,
                "currency": currency,
                "payment_type": payment_type,
                "provider": provider_name,
                "provider_transaction_id": result.get('payment_id'),
                "provider_receipt_url": result.get('receipt_url'),
                "status": result.get('status', 'completed'),
                "metadata": metadata,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            await self.db.payments.insert_one(payment_record)
            result['payment_record_id'] = payment_record['id']
        
        return result
    
    async def process_refund(
        self,
        provider_name: str,
        original_payment_id: str,
        amount: float = None,
        reason: str = None,
        booking_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process a refund"""
        provider = self.get_provider(provider_name)
        
        if not provider.is_configured() and provider_name != 'mock':
            provider = self._providers['mock']
        
        result = await provider.refund_payment(
            payment_id=original_payment_id,
            amount=amount,
            reason=reason
        )
        
        # Record refund in database
        if self.db and result.get('success'):
            refund_record = {
                "id": str(uuid.uuid4()),
                "booking_id": booking_id,
                "household_id": metadata.get('household_id', '') if metadata else '',
                "amount": amount or 0,
                "currency": "USD",
                "payment_type": "refund",
                "provider": provider_name,
                "provider_transaction_id": result.get('refund_id'),
                "status": result.get('status', 'completed'),
                "refund_of": original_payment_id,
                "metadata": {"reason": reason, **(metadata or {})},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            await self.db.payments.insert_one(refund_record)
            result['refund_record_id'] = refund_record['id']
        
        return result
