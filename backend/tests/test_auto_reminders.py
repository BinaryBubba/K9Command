"""
Test Auto-Reminders System for K9Command
Tests reminder preferences, scheduling, and management endpoints
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Test123!"
CUSTOMER_EMAIL = "customer@test.com"
CUSTOMER_PASSWORD = "Test123!"


class TestAutoReminders:
    """Auto-Reminders API Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.customer_token = None
        self.test_booking_id = None
    
    def get_admin_token(self):
        """Get admin authentication token"""
        if self.admin_token:
            return self.admin_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.admin_token = response.json().get("token")
            return self.admin_token
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def get_customer_token(self):
        """Get customer authentication token"""
        if self.customer_token:
            return self.customer_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CUSTOMER_EMAIL,
            "password": CUSTOMER_PASSWORD
        })
        if response.status_code == 200:
            self.customer_token = response.json().get("token")
            return self.customer_token
        pytest.skip(f"Customer login failed: {response.status_code}")
    
    # ==================== REMINDER PREFERENCES TESTS ====================
    
    def test_get_reminder_preferences_customer(self):
        """Test GET /api/moego/reminders/preferences - Customer can get their preferences"""
        token = self.get_customer_token()
        response = self.session.get(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "user_id" in data, "Response should contain user_id"
        assert "check_in_24h" in data, "Response should contain check_in_24h"
        assert "check_in_2h" in data, "Response should contain check_in_2h"
        assert "check_out_24h" in data, "Response should contain check_out_24h"
        assert "check_out_2h" in data, "Response should contain check_out_2h"
        assert "booking_confirmation" in data, "Response should contain booking_confirmation"
        assert "payment_due" in data, "Response should contain payment_due"
        assert "channels" in data, "Response should contain channels"
        
        # Verify default values
        assert isinstance(data["check_in_24h"], bool)
        assert isinstance(data["check_in_2h"], bool)
        assert isinstance(data["check_out_24h"], bool)
        assert isinstance(data["check_out_2h"], bool)
        assert isinstance(data["booking_confirmation"], bool)
        assert isinstance(data["payment_due"], bool)
        assert isinstance(data["channels"], list)
        
        print(f"✓ Customer reminder preferences retrieved: {data}")
    
    def test_get_reminder_preferences_admin(self):
        """Test GET /api/moego/reminders/preferences - Admin can get their preferences"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "user_id" in data
        print(f"✓ Admin reminder preferences retrieved")
    
    def test_update_reminder_preferences_single_field(self):
        """Test PUT /api/moego/reminders/preferences - Update single preference"""
        token = self.get_customer_token()
        
        # First get current preferences
        get_response = self.session.get(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"}
        )
        original_prefs = get_response.json()
        
        # Toggle check_in_24h
        new_value = not original_prefs.get("check_in_24h", True)
        
        response = self.session.put(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"},
            json={"check_in_24h": new_value}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "message" in data, "Response should contain message"
        assert "preferences" in data, "Response should contain preferences"
        assert data["preferences"]["check_in_24h"] == new_value, "Preference should be updated"
        
        print(f"✓ Single preference updated: check_in_24h = {new_value}")
        
        # Restore original value
        self.session.put(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"},
            json={"check_in_24h": original_prefs.get("check_in_24h", True)}
        )
    
    def test_update_reminder_preferences_multiple_fields(self):
        """Test PUT /api/moego/reminders/preferences - Update multiple preferences"""
        token = self.get_customer_token()
        
        response = self.session.put(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "check_in_24h": True,
                "check_in_2h": True,
                "check_out_24h": True,
                "check_out_2h": False,
                "booking_confirmation": True,
                "payment_due": True
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        prefs = data["preferences"]
        assert prefs["check_in_24h"] == True
        assert prefs["check_in_2h"] == True
        assert prefs["check_out_24h"] == True
        assert prefs["check_out_2h"] == False
        assert prefs["booking_confirmation"] == True
        assert prefs["payment_due"] == True
        
        print(f"✓ Multiple preferences updated successfully")
    
    def test_update_reminder_preferences_unauthorized(self):
        """Test PUT /api/moego/reminders/preferences - Unauthorized access"""
        response = self.session.put(
            f"{BASE_URL}/api/moego/reminders/preferences",
            json={"check_in_24h": False}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Unauthorized access correctly rejected")
    
    # ==================== SCHEDULED REMINDERS TESTS ====================
    
    def test_get_scheduled_reminders_customer(self):
        """Test GET /api/moego/reminders/scheduled - Customer can get their scheduled reminders"""
        token = self.get_customer_token()
        response = self.session.get(
            f"{BASE_URL}/api/moego/reminders/scheduled",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "reminders" in data, "Response should contain reminders"
        assert "count" in data, "Response should contain count"
        assert isinstance(data["reminders"], list)
        assert isinstance(data["count"], int)
        
        print(f"✓ Customer scheduled reminders retrieved: {data['count']} reminders")
    
    def test_get_scheduled_reminders_with_booking_filter(self):
        """Test GET /api/moego/reminders/scheduled?booking_id=xxx - Filter by booking"""
        token = self.get_customer_token()
        
        # Use a non-existent booking ID to test filter works
        response = self.session.get(
            f"{BASE_URL}/api/moego/reminders/scheduled?booking_id=non-existent-booking",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["count"] == 0, "Should return 0 reminders for non-existent booking"
        print(f"✓ Booking filter works correctly")
    
    # ==================== ADMIN-ONLY ENDPOINTS TESTS ====================
    
    def test_process_due_reminders_admin(self):
        """Test POST /api/moego/reminders/process - Admin can process due reminders"""
        token = self.get_admin_token()
        response = self.session.post(
            f"{BASE_URL}/api/moego/reminders/process",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "message" in data, "Response should contain message"
        assert "results" in data, "Response should contain results"
        assert "processed" in data["results"], "Results should contain processed count"
        assert "sent" in data["results"], "Results should contain sent count"
        assert "failed" in data["results"], "Results should contain failed count"
        
        print(f"✓ Admin processed reminders: {data['results']}")
    
    def test_process_due_reminders_customer_forbidden(self):
        """Test POST /api/moego/reminders/process - Customer cannot process reminders"""
        token = self.get_customer_token()
        response = self.session.post(
            f"{BASE_URL}/api/moego/reminders/process",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Customer correctly forbidden from processing reminders")
    
    def test_get_pending_reminders_admin(self):
        """Test GET /api/moego/reminders/pending - Admin can get all pending reminders"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/moego/reminders/pending",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "reminders" in data, "Response should contain reminders"
        assert "count" in data, "Response should contain count"
        assert isinstance(data["reminders"], list)
        
        print(f"✓ Admin retrieved {data['count']} pending reminders")
    
    def test_get_pending_reminders_customer_forbidden(self):
        """Test GET /api/moego/reminders/pending - Customer cannot get all pending reminders"""
        token = self.get_customer_token()
        response = self.session.get(
            f"{BASE_URL}/api/moego/reminders/pending",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Customer correctly forbidden from viewing all pending reminders")
    
    # ==================== SCHEDULE/CANCEL REMINDERS TESTS ====================
    
    def test_schedule_reminders_nonexistent_booking(self):
        """Test POST /api/moego/reminders/schedule/{booking_id} - Non-existent booking"""
        token = self.get_customer_token()
        response = self.session.post(
            f"{BASE_URL}/api/moego/reminders/schedule/non-existent-booking-id",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Non-existent booking correctly returns 404")
    
    def test_cancel_reminders_nonexistent_booking(self):
        """Test DELETE /api/moego/reminders/cancel/{booking_id} - Non-existent booking"""
        token = self.get_customer_token()
        response = self.session.delete(
            f"{BASE_URL}/api/moego/reminders/cancel/non-existent-booking-id",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Non-existent booking correctly returns 404 for cancel")


class TestReminderIntegration:
    """Integration tests for reminders with bookings"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def get_customer_token(self):
        """Get customer authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CUSTOMER_EMAIL,
            "password": CUSTOMER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Customer login failed: {response.status_code}")
    
    def test_reminder_preferences_persistence(self):
        """Test that reminder preferences persist across requests"""
        token = self.get_customer_token()
        
        # Update preferences
        update_response = self.session.put(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "check_in_24h": True,
                "check_out_2h": True
            }
        )
        assert update_response.status_code == 200
        
        # Get preferences again
        get_response = self.session.get(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data["check_in_24h"] == True, "check_in_24h should persist"
        assert data["check_out_2h"] == True, "check_out_2h should persist"
        
        print(f"✓ Reminder preferences persist correctly")
    
    def test_full_reminder_workflow(self):
        """Test complete reminder workflow: get prefs -> update -> verify"""
        token = self.get_customer_token()
        
        # Step 1: Get initial preferences
        get_response = self.session.get(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        initial_prefs = get_response.json()
        print(f"  Initial preferences: check_in_24h={initial_prefs['check_in_24h']}")
        
        # Step 2: Update a preference
        new_value = not initial_prefs["check_in_24h"]
        update_response = self.session.put(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"},
            json={"check_in_24h": new_value}
        )
        assert update_response.status_code == 200
        print(f"  Updated check_in_24h to: {new_value}")
        
        # Step 3: Verify update
        verify_response = self.session.get(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert verify_response.status_code == 200
        updated_prefs = verify_response.json()
        assert updated_prefs["check_in_24h"] == new_value
        print(f"  Verified: check_in_24h={updated_prefs['check_in_24h']}")
        
        # Step 4: Restore original value
        restore_response = self.session.put(
            f"{BASE_URL}/api/moego/reminders/preferences",
            headers={"Authorization": f"Bearer {token}"},
            json={"check_in_24h": initial_prefs["check_in_24h"]}
        )
        assert restore_response.status_code == 200
        print(f"  Restored to original: {initial_prefs['check_in_24h']}")
        
        print(f"✓ Full reminder workflow completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
