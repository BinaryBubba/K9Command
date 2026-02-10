"""
K9 API Refactoring Tests
Tests all endpoints after refactoring from /api/moego to /api/k9
Verifies the 9 domain-specific routers work correctly
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://paws-point.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Test123!"
CUSTOMER_EMAIL = "customer@test.com"
CUSTOMER_PASSWORD = "Test123!"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def customer_token():
    """Get customer authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
    )
    assert response.status_code == 200, f"Customer login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture
def customer_headers(customer_token):
    """Headers with customer auth"""
    return {"Authorization": f"Bearer {customer_token}", "Content-Type": "application/json"}


class TestKennelsRouter:
    """Tests for /api/k9/kennels endpoints"""
    
    def test_list_kennels(self, admin_headers):
        """GET /api/k9/kennels - List all kennels"""
        response = requests.get(f"{BASE_URL}/api/k9/kennels", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} kennels")
    
    def test_get_kennel_by_id(self, admin_headers):
        """GET /api/k9/kennels/{id} - Get specific kennel"""
        # First get list to find an ID
        list_response = requests.get(f"{BASE_URL}/api/k9/kennels", headers=admin_headers)
        kennels = list_response.json()
        
        if kennels:
            kennel_id = kennels[0]["id"]
            response = requests.get(f"{BASE_URL}/api/k9/kennels/{kennel_id}", headers=admin_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == kennel_id
            print(f"✓ Retrieved kennel: {data.get('name')}")
        else:
            pytest.skip("No kennels available to test")
    
    def test_list_time_slots(self, admin_headers):
        """GET /api/k9/slots - List time slots"""
        response = requests.get(f"{BASE_URL}/api/k9/slots", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} time slots")


class TestBookingsRouter:
    """Tests for /api/k9/bookings endpoints"""
    
    def test_smart_booking_endpoint_exists(self, admin_headers):
        """POST /api/k9/bookings/smart - Verify endpoint exists"""
        # Test with minimal data to verify endpoint responds
        response = requests.post(
            f"{BASE_URL}/api/k9/bookings/smart",
            headers=admin_headers,
            json={"dog_ids": [], "check_in_date": "", "check_out_date": ""}
        )
        # Should return 400 for invalid data, not 404
        assert response.status_code in [400, 422], f"Unexpected status: {response.status_code}"
        print("✓ Smart booking endpoint accessible")
    
    def test_list_coupons(self, admin_headers):
        """GET /api/k9/coupons - List coupons (admin)"""
        response = requests.get(f"{BASE_URL}/api/k9/coupons", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} coupons")
    
    def test_list_eligibility_rules(self, admin_headers):
        """GET /api/k9/eligibility-rules - List eligibility rules"""
        response = requests.get(f"{BASE_URL}/api/k9/eligibility-rules", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} eligibility rules")
    
    def test_list_waitlist(self, admin_headers):
        """GET /api/k9/waitlist - List waitlist entries"""
        response = requests.get(f"{BASE_URL}/api/k9/waitlist", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} waitlist entries")
    
    def test_pending_approval_bookings(self, admin_headers):
        """GET /api/k9/bookings/pending-approval - Get pending bookings"""
        response = requests.get(f"{BASE_URL}/api/k9/bookings/pending-approval", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "bookings" in data
        print(f"✓ Found {data.get('count', 0)} pending approval bookings")


class TestOperationsRouter:
    """Tests for /api/k9/operations endpoints"""
    
    def test_daily_summary(self, admin_headers):
        """GET /api/k9/operations/summary - Get daily operations summary"""
        response = requests.get(f"{BASE_URL}/api/k9/operations/summary", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "check_ins_today" in data
        assert "check_outs_today" in data
        assert "dogs_on_site" in data
        print(f"✓ Daily summary: {data['check_ins_today']} check-ins, {data['dogs_on_site']} dogs on site")
    
    def test_dogs_on_site(self, admin_headers):
        """GET /api/k9/operations/dogs-on-site - Get dogs currently on site"""
        response = requests.get(f"{BASE_URL}/api/k9/operations/dogs-on-site", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "dogs" in data
        assert "count" in data
        print(f"✓ Dogs on site: {data['count']}")
    
    def test_check_ins_today(self, admin_headers):
        """GET /api/k9/operations/check-ins - Get today's check-ins"""
        response = requests.get(f"{BASE_URL}/api/k9/operations/check-ins", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "check_ins" in data
        print(f"✓ Check-ins today: {data.get('count', 0)}")
    
    def test_check_outs_today(self, admin_headers):
        """GET /api/k9/operations/check-outs - Get today's check-outs"""
        response = requests.get(f"{BASE_URL}/api/k9/operations/check-outs", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "check_outs" in data
        print(f"✓ Check-outs today: {data.get('count', 0)}")
    
    def test_baths_due(self, admin_headers):
        """GET /api/k9/operations/baths-due - Get baths due today"""
        response = requests.get(f"{BASE_URL}/api/k9/operations/baths-due", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "baths_due" in data
        print(f"✓ Baths due: {data.get('count', 0)}")


class TestNotificationsRouter:
    """Tests for /api/k9/notifications endpoints"""
    
    def test_get_notifications(self, admin_headers):
        """GET /api/k9/notifications - Get user notifications"""
        response = requests.get(f"{BASE_URL}/api/k9/notifications", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} notifications")
    
    def test_unread_count(self, admin_headers):
        """GET /api/k9/notifications/unread-count - Get unread count"""
        response = requests.get(f"{BASE_URL}/api/k9/notifications/unread-count", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "unread_count" in data
        print(f"✓ Unread notifications: {data['unread_count']}")
    
    def test_vapid_key(self, admin_headers):
        """GET /api/k9/push/vapid-key - Get VAPID public key"""
        response = requests.get(f"{BASE_URL}/api/k9/push/vapid-key", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "vapid_public_key" in data
        print("✓ VAPID key endpoint accessible")
    
    def test_push_subscriptions(self, admin_headers):
        """GET /api/k9/push/subscriptions - Get push subscriptions"""
        response = requests.get(f"{BASE_URL}/api/k9/push/subscriptions", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data
        print(f"✓ Found {len(data['subscriptions'])} push subscriptions")


class TestPaymentsRouter:
    """Tests for /api/k9/payments endpoints"""
    
    def test_payment_config(self, admin_headers):
        """GET /api/k9/payments/config - Get payment configuration"""
        response = requests.get(f"{BASE_URL}/api/k9/payments/config", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have Square config info
        print("✓ Payment config endpoint accessible")
    
    def test_get_saved_cards(self, admin_headers):
        """GET /api/k9/payments/cards - Get saved payment cards"""
        response = requests.get(f"{BASE_URL}/api/k9/payments/cards", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "cards" in data
        print(f"✓ Found {len(data['cards'])} saved cards")


class TestPortalRouter:
    """Tests for /api/k9/portal endpoints (customer-facing)"""
    
    def test_upcoming_bookings(self, customer_headers):
        """GET /api/k9/portal/upcoming - Get upcoming bookings"""
        response = requests.get(f"{BASE_URL}/api/k9/portal/upcoming", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        assert "upcoming" in data
        assert "count" in data
        print(f"✓ Upcoming bookings: {data['count']}")
    
    def test_service_history(self, customer_headers):
        """GET /api/k9/portal/service-history - Get service history"""
        response = requests.get(f"{BASE_URL}/api/k9/portal/service-history", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        print(f"✓ Service history: {data.get('count', 0)} entries")
    
    def test_invoices(self, customer_headers):
        """GET /api/k9/portal/invoices - Get invoices"""
        response = requests.get(f"{BASE_URL}/api/k9/portal/invoices", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
        print(f"✓ Invoices: {data.get('count', 0)} entries")


class TestInventoryRouter:
    """Tests for /api/k9/inventory endpoints"""
    
    def test_list_products(self, admin_headers):
        """GET /api/k9/inventory/products - List products"""
        response = requests.get(f"{BASE_URL}/api/k9/inventory/products", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        print(f"✓ Found {data.get('count', len(data['products']))} products")
    
    def test_low_stock_products(self, admin_headers):
        """GET /api/k9/inventory/low-stock - Get low stock products"""
        response = requests.get(f"{BASE_URL}/api/k9/inventory/low-stock", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        print(f"✓ Low stock products: {data.get('count', len(data['products']))}")
    
    def test_pos_daily_sales(self, admin_headers):
        """GET /api/k9/pos/daily-sales - Get daily sales"""
        response = requests.get(f"{BASE_URL}/api/k9/pos/daily-sales", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Daily sales endpoint accessible")


class TestCRMRouter:
    """Tests for /api/k9/crm endpoints"""
    
    def test_list_leads(self, admin_headers):
        """GET /api/k9/crm/leads - List leads"""
        response = requests.get(f"{BASE_URL}/api/k9/crm/leads", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        print(f"✓ Found {data.get('count', len(data['leads']))} leads")
    
    def test_retention_metrics(self, admin_headers):
        """GET /api/k9/crm/retention-metrics - Get retention metrics"""
        response = requests.get(f"{BASE_URL}/api/k9/crm/retention-metrics", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_customers" in data
        print(f"✓ Retention metrics: {data['total_customers']} total customers")


class TestRemindersRouter:
    """Tests for /api/k9/reminders endpoints"""
    
    def test_get_preferences(self, admin_headers):
        """GET /api/k9/reminders/preferences - Get reminder preferences"""
        response = requests.get(f"{BASE_URL}/api/k9/reminders/preferences", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "check_in_24h" in data
        assert "check_out_24h" in data
        print(f"✓ Reminder preferences retrieved")
    
    def test_update_preferences(self, admin_headers):
        """PUT /api/k9/reminders/preferences - Update preferences"""
        response = requests.put(
            f"{BASE_URL}/api/k9/reminders/preferences",
            headers=admin_headers,
            json={"check_in_24h": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert "preferences" in data or "message" in data
        print("✓ Reminder preferences updated")
    
    def test_scheduled_reminders(self, admin_headers):
        """GET /api/k9/reminders/scheduled - Get scheduled reminders"""
        response = requests.get(f"{BASE_URL}/api/k9/reminders/scheduled", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "reminders" in data
        print(f"✓ Scheduled reminders: {data.get('count', 0)}")
    
    def test_pending_reminders_admin(self, admin_headers):
        """GET /api/k9/reminders/pending - Get pending reminders (admin)"""
        response = requests.get(f"{BASE_URL}/api/k9/reminders/pending", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "reminders" in data
        print(f"✓ Pending reminders: {data.get('count', 0)}")


class TestOldMoegoEndpointsRemoved:
    """Verify old /api/moego endpoints no longer exist"""
    
    def test_old_moego_kennels_404(self, admin_headers):
        """Verify /api/moego/kennels returns 404"""
        response = requests.get(f"{BASE_URL}/api/moego/kennels", headers=admin_headers)
        assert response.status_code == 404, f"Old endpoint still exists: {response.status_code}"
        print("✓ Old /api/moego/kennels endpoint removed")
    
    def test_old_moego_operations_404(self, admin_headers):
        """Verify /api/moego/operations/summary returns 404"""
        response = requests.get(f"{BASE_URL}/api/moego/operations/summary", headers=admin_headers)
        assert response.status_code == 404, f"Old endpoint still exists: {response.status_code}"
        print("✓ Old /api/moego/operations/summary endpoint removed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
