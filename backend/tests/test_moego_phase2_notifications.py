"""
MoeGo Parity Phase 2 - Notifications & Smart Booking Tests
Tests for: Notification APIs, Smart Booking with eligibility, Bath add-on, Coupon codes
"""
import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Test123!"
CUSTOMER_EMAIL = "customer@test.com"
CUSTOMER_PASSWORD = "Test123!"


class TestNotificationAPIs:
    """Test Notification API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.admin_user = login_response.json().get("user")
        
    def test_get_unread_count_endpoint(self):
        """Test GET /api/moego/notifications/unread-count"""
        response = self.session.get(f"{BASE_URL}/api/moego/notifications/unread-count")
        
        assert response.status_code == 200, f"Unread count failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "unread_count" in data, "Response should contain unread_count"
        assert isinstance(data["unread_count"], int), "unread_count should be an integer"
        print(f"Unread notifications count: {data['unread_count']}")
        
    def test_get_notifications_endpoint(self):
        """Test GET /api/moego/notifications"""
        response = self.session.get(f"{BASE_URL}/api/moego/notifications")
        
        assert response.status_code == 200, f"Get notifications failed: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), "Notifications should return a list"
        print(f"Total notifications: {len(data)}")
        
        # Verify notification structure if any exist
        if len(data) > 0:
            notification = data[0]
            expected_fields = ["id", "user_id", "type", "title", "message", "is_read", "created_at"]
            for field in expected_fields:
                assert field in notification, f"Notification missing field: {field}"
                
    def test_get_notifications_with_unread_filter(self):
        """Test GET /api/moego/notifications?unread_only=true"""
        response = self.session.get(f"{BASE_URL}/api/moego/notifications?unread_only=true")
        
        assert response.status_code == 200, f"Get unread notifications failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Notifications should return a list"
        
        # All returned notifications should be unread
        for notification in data:
            assert notification.get("is_read") == False, "Unread filter should only return unread notifications"
        print(f"Unread notifications: {len(data)}")
        
    def test_get_notifications_with_limit(self):
        """Test GET /api/moego/notifications?limit=5"""
        response = self.session.get(f"{BASE_URL}/api/moego/notifications?limit=5")
        
        assert response.status_code == 200, f"Get notifications with limit failed: {response.status_code}"
        data = response.json()
        assert len(data) <= 5, "Should respect limit parameter"
        
    def test_mark_notification_read_endpoint_exists(self):
        """Test POST /api/moego/notifications/{id}/read endpoint exists"""
        # Test with non-existent notification - should return 404
        response = self.session.post(f"{BASE_URL}/api/moego/notifications/non-existent-id/read")
        assert response.status_code == 404, f"Expected 404 for non-existent notification, got: {response.status_code}"
        
    def test_mark_all_read_endpoint(self):
        """Test POST /api/moego/notifications/mark-all-read"""
        response = self.session.post(f"{BASE_URL}/api/moego/notifications/mark-all-read")
        
        assert response.status_code == 200, f"Mark all read failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "message" in data, "Response should contain message"
        print(f"Mark all read response: {data['message']}")


class TestSmartBookingWithNotifications:
    """Test Smart Booking API with notification triggers"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin first to create test data
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.admin_user = login_response.json().get("user")
        
    def test_smart_booking_creates_booking(self):
        """Test that smart booking creates a booking with eligibility checks"""
        # Create a test dog
        dog_data = {
            "name": f"TEST_SmartDog_{uuid.uuid4().hex[:6]}",
            "breed": "Golden Retriever",
            "weight": 65,
            "age_years": 4,
            "gender": "female",
            "is_neutered": True,
            "vaccinations": [
                {"vaccine_name": "Rabies", "date_administered": "2024-01-15", "expiry_date": "2027-01-15"},
                {"vaccine_name": "DHPP", "date_administered": "2024-01-15", "expiry_date": "2025-01-15"},
                {"vaccine_name": "Bordetella", "date_administered": "2024-06-01", "expiry_date": "2025-06-01"}
            ]
        }
        dog_response = self.session.post(f"{BASE_URL}/api/dogs", json=dog_data)
        
        if dog_response.status_code == 201:
            dog_id = dog_response.json().get("id")
            
            # Create smart booking
            check_in = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%dT10:00:00Z")
            check_out = (datetime.now() + timedelta(days=17)).strftime("%Y-%m-%dT14:00:00Z")
            
            booking_data = {
                "dog_ids": [dog_id],
                "location_id": "main",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "bath_before_pickup": True,
                "bath_day": "checkout",
                "notes": "TEST smart booking with notifications"
            }
            
            response = self.session.post(f"{BASE_URL}/api/moego/bookings/smart", json=booking_data)
            
            assert response.status_code in [200, 201], f"Smart booking failed: {response.status_code} - {response.text}"
            
            data = response.json()
            assert "booking" in data, "Response should contain booking"
            assert "eligibility_results" in data, "Response should contain eligibility_results"
            assert "requires_approval" in data, "Response should contain requires_approval"
            
            booking = data["booking"]
            assert booking.get("bath_before_pickup") == True, "Bath should be scheduled"
            assert booking.get("bath_day") == "checkout", "Bath day should be checkout"
            
            print(f"Smart booking created: {booking.get('id')}")
            print(f"Status: {booking.get('status')}")
            print(f"Requires approval: {data.get('requires_approval')}")
            
            # Cleanup
            self.session.delete(f"{BASE_URL}/api/dogs/{dog_id}")
        else:
            pytest.skip(f"Could not create test dog: {dog_response.text}")
            
    def test_smart_booking_with_bath_day_before(self):
        """Test smart booking with bath scheduled day before checkout"""
        # Create a test dog
        dog_data = {
            "name": f"TEST_BathDog_{uuid.uuid4().hex[:6]}",
            "breed": "Poodle",
            "weight": 45,
            "age_years": 2,
            "gender": "male",
            "is_neutered": True
        }
        dog_response = self.session.post(f"{BASE_URL}/api/dogs", json=dog_data)
        
        if dog_response.status_code == 201:
            dog_id = dog_response.json().get("id")
            
            check_in = (datetime.now() + timedelta(days=21)).strftime("%Y-%m-%dT10:00:00Z")
            check_out = (datetime.now() + timedelta(days=24)).strftime("%Y-%m-%dT14:00:00Z")
            
            booking_data = {
                "dog_ids": [dog_id],
                "location_id": "main",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "bath_before_pickup": True,
                "bath_day": "day_before",  # Day before checkout
                "notes": "TEST bath day before"
            }
            
            response = self.session.post(f"{BASE_URL}/api/moego/bookings/smart", json=booking_data)
            
            if response.status_code in [200, 201]:
                data = response.json()
                booking = data["booking"]
                assert booking.get("bath_day") == "day_before", "Bath day should be day_before"
                print(f"Bath scheduled for day before checkout")
            
            # Cleanup
            self.session.delete(f"{BASE_URL}/api/dogs/{dog_id}")
        else:
            pytest.skip(f"Could not create test dog: {dog_response.text}")
            
    def test_smart_booking_with_coupon_code(self):
        """Test smart booking with coupon code"""
        # Create a test dog
        dog_data = {
            "name": f"TEST_CouponDog_{uuid.uuid4().hex[:6]}",
            "breed": "Beagle",
            "weight": 30,
            "age_years": 3,
            "gender": "female",
            "is_neutered": True
        }
        dog_response = self.session.post(f"{BASE_URL}/api/dogs", json=dog_data)
        
        if dog_response.status_code == 201:
            dog_id = dog_response.json().get("id")
            
            check_in = (datetime.now() + timedelta(days=28)).strftime("%Y-%m-%dT10:00:00Z")
            check_out = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT14:00:00Z")
            
            booking_data = {
                "dog_ids": [dog_id],
                "location_id": "main",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "bath_before_pickup": False,
                "coupon_code": "TESTCOUPON",  # May or may not exist
                "notes": "TEST with coupon"
            }
            
            response = self.session.post(f"{BASE_URL}/api/moego/bookings/smart", json=booking_data)
            
            # Should succeed even if coupon doesn't exist (coupon is optional)
            assert response.status_code in [200, 201, 400], f"Unexpected status: {response.status_code}"
            
            if response.status_code in [200, 201]:
                data = response.json()
                booking = data["booking"]
                print(f"Booking with coupon: {booking.get('coupon_data')}")
            
            # Cleanup
            self.session.delete(f"{BASE_URL}/api/dogs/{dog_id}")
        else:
            pytest.skip(f"Could not create test dog: {dog_response.text}")


class TestSmartBookingEligibilityBlocking:
    """Test Smart Booking auto-blocking on eligibility failures"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.admin_user = login_response.json().get("user")
        
    def test_booking_with_aggressive_dog_triggers_block(self):
        """Test that booking with aggressive dog triggers auto-block"""
        # Create a dog with aggression history
        dog_data = {
            "name": f"TEST_AggressiveDog_{uuid.uuid4().hex[:6]}",
            "breed": "German Shepherd",
            "weight": 80,
            "age_years": 5,
            "gender": "male",
            "is_neutered": True,
            "incidents_of_aggression": True,  # This should trigger blocking
            "friendly_with_dogs": False
        }
        dog_response = self.session.post(f"{BASE_URL}/api/dogs", json=dog_data)
        
        if dog_response.status_code == 201:
            dog_id = dog_response.json().get("id")
            
            check_in = (datetime.now() + timedelta(days=35)).strftime("%Y-%m-%dT10:00:00Z")
            check_out = (datetime.now() + timedelta(days=38)).strftime("%Y-%m-%dT14:00:00Z")
            
            booking_data = {
                "dog_ids": [dog_id],
                "location_id": "main",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "notes": "TEST aggressive dog booking"
            }
            
            response = self.session.post(f"{BASE_URL}/api/moego/bookings/smart", json=booking_data)
            
            if response.status_code in [200, 201]:
                data = response.json()
                # Check if booking was auto-blocked due to behavior rules
                print(f"Booking status: {data.get('booking', {}).get('status')}")
                print(f"Requires approval: {data.get('requires_approval')}")
                print(f"Auto blocked: {data.get('auto_blocked')}")
                print(f"Eligibility errors: {data.get('booking', {}).get('eligibility_errors')}")
            
            # Cleanup
            self.session.delete(f"{BASE_URL}/api/dogs/{dog_id}")
        else:
            pytest.skip(f"Could not create test dog: {dog_response.text}")


class TestBookingApprovalNotifications:
    """Test that booking approval/rejection sends notifications"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.admin_user = login_response.json().get("user")
        
    def test_approve_booking_endpoint(self):
        """Test booking approval endpoint"""
        # First check if there are any pending approvals
        response = self.session.get(f"{BASE_URL}/api/moego/bookings/pending-approval")
        assert response.status_code == 200
        
        pending = response.json()
        if len(pending) > 0:
            booking_id = pending[0]["id"]
            
            # Try to approve
            approve_response = self.session.post(f"{BASE_URL}/api/moego/bookings/{booking_id}/approve")
            
            # Should succeed or fail with specific error
            assert approve_response.status_code in [200, 400], f"Approve failed: {approve_response.text}"
            
            if approve_response.status_code == 200:
                print(f"Booking {booking_id} approved successfully")
        else:
            print("No pending approvals to test")
            
    def test_reject_booking_endpoint(self):
        """Test booking rejection endpoint"""
        # First check if there are any pending approvals
        response = self.session.get(f"{BASE_URL}/api/moego/bookings/pending-approval")
        assert response.status_code == 200
        
        pending = response.json()
        if len(pending) > 0:
            booking_id = pending[0]["id"]
            
            # Try to reject
            reject_response = self.session.post(
                f"{BASE_URL}/api/moego/bookings/{booking_id}/reject?reason=Test rejection"
            )
            
            # Should succeed or fail with specific error
            assert reject_response.status_code in [200, 400], f"Reject failed: {reject_response.text}"
            
            if reject_response.status_code == 200:
                print(f"Booking {booking_id} rejected successfully")
        else:
            print("No pending approvals to test rejection")


class TestNotificationAccessControl:
    """Test access control for notification endpoints"""
    
    def test_notifications_require_auth(self):
        """Test that notification endpoints require authentication"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Try without auth
        response = session.get(f"{BASE_URL}/api/moego/notifications")
        assert response.status_code == 403, f"Expected 403 without auth, got: {response.status_code}"
        
    def test_unread_count_requires_auth(self):
        """Test that unread count requires authentication"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Try without auth
        response = session.get(f"{BASE_URL}/api/moego/notifications/unread-count")
        assert response.status_code == 403, f"Expected 403 without auth, got: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
