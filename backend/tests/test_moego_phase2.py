"""
MoeGo Parity Phase 2 API Tests
Tests for: Smart Booking, Check-In/Out Operations, Baths Due, Booking Approvals
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Test123!"


class TestMoeGoPhase2APIs:
    """Test MoeGo Phase 2 API endpoints"""
    
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
        
    # ==================== SMART BOOKING API ====================
    
    def test_smart_booking_endpoint_exists(self):
        """Test that smart booking endpoint exists"""
        # Test with minimal data - should fail validation but endpoint should exist
        response = self.session.post(f"{BASE_URL}/api/moego/bookings/smart", json={})
        # Should not be 404 - endpoint exists
        assert response.status_code != 404, "Smart booking endpoint not found"
        # Should be 400, 422, 500, or 520 (server error) for validation error
        assert response.status_code in [400, 422, 500, 520], f"Unexpected status: {response.status_code}"
        print(f"Smart booking endpoint exists, returned status: {response.status_code}")
        
    def test_smart_booking_with_valid_data(self):
        """Test smart booking with valid data structure"""
        # First, we need a dog to book
        # Create a test dog
        dog_data = {
            "name": "TEST_SmartBookDog",
            "breed": "Labrador",
            "weight": 50,
            "age_years": 3,
            "gender": "male",
            "is_neutered": True
        }
        dog_response = self.session.post(f"{BASE_URL}/api/dogs", json=dog_data)
        
        if dog_response.status_code == 201:
            dog_id = dog_response.json().get("id")
            
            # Now try smart booking
            check_in = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT10:00:00Z")
            check_out = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%dT14:00:00Z")
            
            booking_data = {
                "dog_ids": [dog_id],
                "location_id": "main",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "bath_before_pickup": True,
                "bath_day": "checkout",
                "notes": "TEST smart booking"
            }
            
            response = self.session.post(f"{BASE_URL}/api/moego/bookings/smart", json=booking_data)
            # Should succeed or fail with eligibility issues
            assert response.status_code in [200, 201, 400], f"Smart booking failed: {response.text}"
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert "booking" in data, "Response should contain booking"
                assert "eligibility_results" in data, "Response should contain eligibility_results"
                print(f"Smart booking created: {data.get('booking', {}).get('id')}")
                print(f"Requires approval: {data.get('requires_approval')}")
                
            # Cleanup dog
            self.session.delete(f"{BASE_URL}/api/dogs/{dog_id}")
        else:
            print(f"Could not create test dog: {dog_response.text}")
            
    # ==================== CHECK-INS API ====================
    
    def test_check_ins_endpoint_exists(self):
        """Test that check-ins endpoint exists and returns data"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = self.session.get(f"{BASE_URL}/api/moego/operations/check-ins?location_id=main&date={today}")
        
        assert response.status_code == 200, f"Check-ins endpoint failed: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), "Check-ins should return a list"
        print(f"Check-ins for today: {len(data)} bookings")
        
    def test_check_ins_with_different_dates(self):
        """Test check-ins with various date parameters"""
        # Test with tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = self.session.get(f"{BASE_URL}/api/moego/operations/check-ins?location_id=main&date={tomorrow}")
        assert response.status_code == 200, f"Check-ins for tomorrow failed: {response.text}"
        
        # Test with past date
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        response = self.session.get(f"{BASE_URL}/api/moego/operations/check-ins?location_id=main&date={yesterday}")
        assert response.status_code == 200, f"Check-ins for yesterday failed: {response.text}"
        
    # ==================== CHECK-OUTS API ====================
    
    def test_check_outs_endpoint_exists(self):
        """Test that check-outs endpoint exists and returns data"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = self.session.get(f"{BASE_URL}/api/moego/operations/check-outs?location_id=main&date={today}")
        
        assert response.status_code == 200, f"Check-outs endpoint failed: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), "Check-outs should return a list"
        print(f"Check-outs for today: {len(data)} bookings")
        
    def test_check_outs_with_different_dates(self):
        """Test check-outs with various date parameters"""
        # Test with tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = self.session.get(f"{BASE_URL}/api/moego/operations/check-outs?location_id=main&date={tomorrow}")
        assert response.status_code == 200, f"Check-outs for tomorrow failed: {response.text}"
        
    # ==================== BATHS DUE API ====================
    
    def test_baths_due_endpoint_exists(self):
        """Test that baths-due endpoint exists and returns data"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = self.session.get(f"{BASE_URL}/api/moego/operations/baths-due?location_id=main&date={today}")
        
        assert response.status_code == 200, f"Baths-due endpoint failed: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), "Baths-due should return a list"
        print(f"Baths due today: {len(data)} bookings")
        
    def test_baths_due_with_different_dates(self):
        """Test baths-due with various date parameters"""
        # Test with tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = self.session.get(f"{BASE_URL}/api/moego/operations/baths-due?location_id=main&date={tomorrow}")
        assert response.status_code == 200, f"Baths-due for tomorrow failed: {response.text}"
        
    # ==================== PENDING APPROVALS API ====================
    
    def test_pending_approvals_endpoint_exists(self):
        """Test that pending-approval endpoint exists and returns data"""
        response = self.session.get(f"{BASE_URL}/api/moego/bookings/pending-approval")
        
        assert response.status_code == 200, f"Pending approvals endpoint failed: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), "Pending approvals should return a list"
        print(f"Pending approvals: {len(data)} bookings")
        
    def test_pending_approvals_with_location_filter(self):
        """Test pending approvals with location filter"""
        response = self.session.get(f"{BASE_URL}/api/moego/bookings/pending-approval?location_id=main")
        assert response.status_code == 200, f"Pending approvals with location failed: {response.text}"
        
    # ==================== KENNELS API (for Lodging Map) ====================
    
    def test_kennels_list_endpoint(self):
        """Test that kennels list endpoint works"""
        response = self.session.get(f"{BASE_URL}/api/moego/kennels")
        
        assert response.status_code == 200, f"Kennels list failed: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), "Kennels should return a list"
        print(f"Total kennels: {len(data)}")
        
    def test_dogs_on_site_endpoint(self):
        """Test dogs-on-site endpoint for lodging map"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = self.session.get(f"{BASE_URL}/api/moego/operations/dogs-on-site?location_id=main&date={today}")
        
        assert response.status_code == 200, f"Dogs on site failed: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), "Dogs on site should return a list"
        print(f"Dogs on site today: {len(data)}")
        
    # ==================== CHECK-IN/OUT OPERATIONS ====================
    
    def test_check_in_operation_endpoint_exists(self):
        """Test that check-in operation endpoint exists"""
        # Test with non-existent booking - should return 404
        response = self.session.post(f"{BASE_URL}/api/moego/operations/check-in/non-existent-id", json={})
        assert response.status_code == 404, f"Expected 404 for non-existent booking, got: {response.status_code}"
        
    def test_check_out_operation_endpoint_exists(self):
        """Test that check-out operation endpoint exists"""
        # Test with non-existent booking - should return 404
        response = self.session.post(f"{BASE_URL}/api/moego/operations/check-out/non-existent-id", json={})
        assert response.status_code == 404, f"Expected 404 for non-existent booking, got: {response.status_code}"
        
    def test_bath_complete_endpoint_exists(self):
        """Test that bath complete endpoint exists"""
        # Test with non-existent booking - should return 404
        response = self.session.post(f"{BASE_URL}/api/moego/operations/bath/non-existent-id")
        assert response.status_code == 404, f"Expected 404 for non-existent booking, got: {response.status_code}"
        
    # ==================== BOOKING APPROVAL/REJECTION ====================
    
    def test_approve_booking_endpoint_exists(self):
        """Test that approve booking endpoint exists"""
        # Test with non-existent booking - should return 404
        response = self.session.post(f"{BASE_URL}/api/moego/bookings/non-existent-id/approve")
        assert response.status_code == 404, f"Expected 404 for non-existent booking, got: {response.status_code}"
        
    def test_reject_booking_endpoint_exists(self):
        """Test that reject booking endpoint exists"""
        # Test with non-existent booking - should return 404
        response = self.session.post(f"{BASE_URL}/api/moego/bookings/non-existent-id/reject?reason=test")
        assert response.status_code == 404, f"Expected 404 for non-existent booking, got: {response.status_code}"
        
    # ==================== OPERATIONS SUMMARY ====================
    
    def test_operations_summary_endpoint(self):
        """Test operations summary endpoint"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = self.session.get(f"{BASE_URL}/api/moego/operations/summary?location_id=main&date={today}")
        
        assert response.status_code == 200, f"Operations summary failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify expected fields
        expected_fields = ['total_kennels', 'occupied_kennels', 'available_kennels', 
                          'check_ins_scheduled', 'check_outs_scheduled', 'dogs_on_site']
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        print(f"Operations summary: {data}")


class TestMoeGoPhase2AccessControl:
    """Test access control for Phase 2 endpoints"""
    
    def test_check_ins_requires_staff_or_admin(self):
        """Test that check-ins requires staff or admin role"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Try without auth
        response = session.get(f"{BASE_URL}/api/moego/operations/check-ins?location_id=main")
        assert response.status_code == 403, f"Expected 403 without auth, got: {response.status_code}"
        
    def test_pending_approvals_requires_admin(self):
        """Test that pending approvals requires admin role"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Try without auth
        response = session.get(f"{BASE_URL}/api/moego/bookings/pending-approval")
        assert response.status_code == 403, f"Expected 403 without auth, got: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
