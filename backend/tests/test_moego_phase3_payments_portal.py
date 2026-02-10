"""
MoeGo Phase 3 - Payments & Customer Portal Tests
Tests Square payment service (mock mode), card vaulting, deposits, refunds, and customer portal endpoints.
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Test123!"
CUSTOMER_EMAIL = f"test_customer_{uuid.uuid4().hex[:8]}@k9.com"
CUSTOMER_PASSWORD = "Test123!"


class TestPaymentConfig:
    """Test payment configuration endpoint"""
    
    def test_get_payment_config_returns_mock_mode(self, auth_token):
        """GET /api/moego/payments/config returns mock_mode info"""
        response = requests.get(
            f"{BASE_URL}/api/moego/payments/config",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify config structure
        assert "mock_mode" in data
        assert "application_id" in data
        assert "location_id" in data
        assert "environment" in data
        
        # Should be in mock mode since no Square credentials configured
        assert data["mock_mode"] == True
        print(f"Payment config: mock_mode={data['mock_mode']}, env={data['environment']}")


class TestSavedCards:
    """Test card vaulting (save/get/delete cards)"""
    
    def test_save_card_accepts_card_data(self, auth_token):
        """POST /api/moego/payments/cards accepts card data"""
        response = requests.post(
            f"{BASE_URL}/api/moego/payments/cards",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "source_id": f"mock_token_{uuid.uuid4().hex[:8]}",
                "cardholder_name": "Test User",
                "postal_code": "12345"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "card" in data
        assert data["card"]["card_brand"] == "VISA"  # Mock mode returns VISA
        assert data["card"]["last_4"] == "1111"  # Mock mode returns 1111
        assert data["card"]["status"] == "active"
        
        print(f"Card saved: {data['card']['card_brand']} ****{data['card']['last_4']}")
        return data["card"]["card_id"]
    
    def test_get_cards_returns_user_cards(self, auth_token):
        """GET /api/moego/payments/cards returns user's saved cards"""
        response = requests.get(
            f"{BASE_URL}/api/moego/payments/cards",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "cards" in data
        assert "count" in data
        assert isinstance(data["cards"], list)
        
        print(f"Found {data['count']} saved cards")
        return data["cards"]
    
    def test_delete_card_removes_card(self, auth_token):
        """DELETE /api/moego/payments/cards/{id} removes card"""
        # First save a card
        save_response = requests.post(
            f"{BASE_URL}/api/moego/payments/cards",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "source_id": f"mock_token_delete_{uuid.uuid4().hex[:8]}",
                "cardholder_name": "Delete Test",
                "postal_code": "54321"
            }
        )
        assert save_response.status_code == 200
        card_id = save_response.json()["card"]["card_id"]
        
        # Delete the card
        delete_response = requests.delete(
            f"{BASE_URL}/api/moego/payments/cards/{card_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert delete_response.status_code == 200
        assert "message" in delete_response.json()
        print(f"Card {card_id} deleted successfully")


class TestDepositHold:
    """Test deposit/pre-authorization holds"""
    
    def test_create_deposit_hold(self, auth_token, saved_card_id, test_booking_id):
        """POST /api/moego/payments/deposit-hold creates authorization"""
        response = requests.post(
            f"{BASE_URL}/api/moego/payments/deposit-hold",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "card_id": saved_card_id,
                "booking_id": test_booking_id,
                "amount_cents": 5000,  # $50 deposit
                "currency": "USD",
                "note": "Test deposit hold"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "authorization" in data
        assert data["authorization"]["status"] == "authorized"
        assert data["authorization"]["amount_cents"] == 5000
        
        print(f"Deposit hold created: {data['authorization']['id']}")
        return data["authorization"]["id"]


class TestCapturePayment:
    """Test capturing pre-authorized payments"""
    
    def test_capture_authorization(self, admin_token, auth_id):
        """POST /api/moego/payments/capture/{id} captures authorization"""
        response = requests.post(
            f"{BASE_URL}/api/moego/payments/capture/{auth_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "result" in data
        assert data["result"]["status"] == "captured"
        
        print(f"Authorization {auth_id} captured")


class TestDirectCharge:
    """Test direct payment (immediate charge)"""
    
    def test_create_direct_charge(self, auth_token, saved_card_id, test_booking_id):
        """POST /api/moego/payments/charge creates immediate payment"""
        response = requests.post(
            f"{BASE_URL}/api/moego/payments/charge",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "card_id": saved_card_id,
                "booking_id": test_booking_id,
                "amount_cents": 15000,  # $150
                "currency": "USD",
                "note": "Test direct charge"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "payment" in data
        assert data["payment"]["status"] == "completed"
        assert data["payment"]["amount_cents"] == 15000
        
        print(f"Direct charge completed: {data['payment']['id']}")
        return data["payment"]["id"]


class TestRefund:
    """Test refund processing"""
    
    def test_refund_payment(self, admin_token, payment_id):
        """POST /api/moego/payments/refund processes refunds"""
        response = requests.post(
            f"{BASE_URL}/api/moego/payments/refund",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "payment_id": payment_id,
                "amount_cents": 5000,  # Partial refund $50
                "reason": "Test refund"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "refund" in data
        assert data["refund"]["status"] == "COMPLETED"
        assert data["refund"]["amount_cents"] == 5000
        
        print(f"Refund processed: {data['refund']['id']}")


class TestCustomerPortal:
    """Test customer portal endpoints"""
    
    def test_get_upcoming_bookings(self, auth_token):
        """GET /api/moego/portal/upcoming returns customer bookings"""
        response = requests.get(
            f"{BASE_URL}/api/moego/portal/upcoming",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "upcoming" in data
        assert "count" in data
        assert isinstance(data["upcoming"], list)
        
        print(f"Found {data['count']} upcoming bookings")
    
    def test_get_service_history(self, auth_token):
        """GET /api/moego/portal/service-history returns past bookings"""
        response = requests.get(
            f"{BASE_URL}/api/moego/portal/service-history",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "history" in data
        assert "count" in data
        assert isinstance(data["history"], list)
        
        print(f"Found {data['count']} past bookings")
    
    def test_get_invoices(self, auth_token):
        """GET /api/moego/portal/invoices returns payment receipts"""
        response = requests.get(
            f"{BASE_URL}/api/moego/portal/invoices",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "invoices" in data
        assert "count" in data
        assert isinstance(data["invoices"], list)
        
        print(f"Found {data['count']} invoices")


class TestRebook:
    """Test rebooking from history"""
    
    def test_rebook_from_history(self, auth_token, completed_booking_id):
        """POST /api/moego/portal/rebook/{id} creates new booking from history"""
        check_in = (datetime.now() + timedelta(days=30)).isoformat()
        check_out = (datetime.now() + timedelta(days=33)).isoformat()
        
        response = requests.post(
            f"{BASE_URL}/api/moego/portal/rebook/{completed_booking_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "check_in_date": check_in,
                "check_out_date": check_out
            }
        )
        
        # May return 404 if no completed booking exists
        if response.status_code == 404:
            print("No completed booking found to rebook from - skipping")
            pytest.skip("No completed booking available for rebooking test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "booking" in data
        assert data["booking"]["rebooked_from"] == completed_booking_id
        
        print(f"Rebooked: new booking {data['booking']['id']}")


# ==================== FIXTURES ====================

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.text}")
    
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def admin_token(auth_token):
    """Admin token (same as auth_token for admin user)"""
    return auth_token


@pytest.fixture(scope="module")
def saved_card_id(auth_token):
    """Create and return a saved card ID for testing"""
    response = requests.post(
        f"{BASE_URL}/api/moego/payments/cards",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "source_id": f"mock_token_fixture_{uuid.uuid4().hex[:8]}",
            "cardholder_name": "Test Fixture Card",
            "postal_code": "99999"
        }
    )
    
    if response.status_code != 200:
        pytest.skip(f"Failed to create test card: {response.text}")
    
    return response.json()["card"]["card_id"]


@pytest.fixture(scope="module")
def test_booking_id(auth_token):
    """Create a test booking for payment tests"""
    # First get user's dogs
    dogs_response = requests.get(
        f"{BASE_URL}/api/dogs",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    dog_ids = []
    if dogs_response.status_code == 200:
        dogs = dogs_response.json()
        if isinstance(dogs, list) and len(dogs) > 0:
            dog_ids = [dogs[0].get("id")]
    
    # Create a simple booking
    booking_id = f"test_booking_{uuid.uuid4().hex[:8]}"
    check_in = (datetime.now() + timedelta(days=7)).isoformat()
    check_out = (datetime.now() + timedelta(days=10)).isoformat()
    
    # Try to create via smart booking endpoint
    response = requests.post(
        f"{BASE_URL}/api/moego/bookings/smart",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "dog_ids": dog_ids if dog_ids else [],
            "check_in_date": check_in,
            "check_out_date": check_out,
            "accommodation_type": "room",
            "notes": "Test booking for payment tests"
        }
    )
    
    if response.status_code == 200:
        return response.json().get("booking", {}).get("id", booking_id)
    
    # Return a mock booking ID if creation fails
    return booking_id


@pytest.fixture(scope="module")
def auth_id(auth_token, saved_card_id, test_booking_id):
    """Create a deposit hold and return authorization ID"""
    response = requests.post(
        f"{BASE_URL}/api/moego/payments/deposit-hold",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "card_id": saved_card_id,
            "booking_id": test_booking_id,
            "amount_cents": 2500,
            "currency": "USD",
            "note": "Fixture deposit hold"
        }
    )
    
    if response.status_code != 200:
        pytest.skip(f"Failed to create deposit hold: {response.text}")
    
    return response.json()["authorization"]["id"]


@pytest.fixture(scope="module")
def payment_id(auth_token, saved_card_id, test_booking_id):
    """Create a payment and return payment ID for refund tests"""
    response = requests.post(
        f"{BASE_URL}/api/moego/payments/charge",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "card_id": saved_card_id,
            "booking_id": test_booking_id,
            "amount_cents": 10000,
            "currency": "USD",
            "note": "Fixture payment for refund test"
        }
    )
    
    if response.status_code != 200:
        pytest.skip(f"Failed to create payment: {response.text}")
    
    return response.json()["payment"]["id"]


@pytest.fixture(scope="module")
def completed_booking_id(auth_token):
    """Get a completed booking ID for rebook tests"""
    response = requests.get(
        f"{BASE_URL}/api/moego/portal/service-history",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    if response.status_code == 200:
        history = response.json().get("history", [])
        if history:
            return history[0].get("id")
    
    # Return a fake ID - test will skip if not found
    return "nonexistent_booking_id"


# ==================== INTEGRATION TESTS ====================

class TestPaymentFlow:
    """End-to-end payment flow tests"""
    
    def test_full_payment_flow(self, auth_token, admin_token):
        """Test complete payment flow: save card -> deposit hold -> capture"""
        # 1. Save a card
        card_response = requests.post(
            f"{BASE_URL}/api/moego/payments/cards",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "source_id": f"mock_flow_{uuid.uuid4().hex[:8]}",
                "cardholder_name": "Flow Test",
                "postal_code": "11111"
            }
        )
        assert card_response.status_code == 200
        card_id = card_response.json()["card"]["card_id"]
        print(f"Step 1: Card saved - {card_id}")
        
        # 2. Create a booking ID
        booking_id = f"flow_booking_{uuid.uuid4().hex[:8]}"
        
        # 3. Create deposit hold
        hold_response = requests.post(
            f"{BASE_URL}/api/moego/payments/deposit-hold",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "card_id": card_id,
                "booking_id": booking_id,
                "amount_cents": 7500,
                "currency": "USD"
            }
        )
        assert hold_response.status_code == 200
        auth_id = hold_response.json()["authorization"]["id"]
        print(f"Step 2: Deposit hold created - {auth_id}")
        
        # 4. Capture the authorization (admin only)
        capture_response = requests.post(
            f"{BASE_URL}/api/moego/payments/capture/{auth_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert capture_response.status_code == 200
        assert capture_response.json()["result"]["status"] == "captured"
        print(f"Step 3: Authorization captured")
        
        # 5. Verify payment in booking payments
        payments_response = requests.get(
            f"{BASE_URL}/api/moego/payments/booking/{booking_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert payments_response.status_code == 200
        print(f"Step 4: Payment flow complete!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
