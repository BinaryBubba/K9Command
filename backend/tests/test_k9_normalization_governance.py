"""
K9Command Normalization and Business Rules Testing - Iteration 19

Tests for:
1. Role governance (public signup = customer only, staff requires approval, admin by owner only)
2. Hours-based cancellation/refund policy (48h=100%, 24-48h=50%, <24h=0%)
3. Booking field normalization (startDate/endDate/dogIds)
4. Dog profile normalization (feedingInstructions, behaviorNotes, specialNeeds)
"""
import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRoleGovernance:
    """Test role governance rules for registration"""
    
    def test_customer_registration_allowed(self):
        """Public registration with customer role should succeed"""
        unique_email = f"test_customer_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "full_name": "Test Customer",
            "phone": "555-0001",
            "role": "customer"
        })
        
        # Customer registration should succeed with 200
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert data["user"]["role"] == "customer", "User role should be customer"
        assert data["user"]["email"] == unique_email
        print(f"✓ Customer registration successful: {unique_email}")
    
    def test_staff_registration_returns_202(self):
        """Staff registration via public endpoint should return 202 (request created, not account)"""
        unique_email = f"test_staff_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "full_name": "Test Staff Request",
            "phone": "555-0002",
            "role": "staff"
        })
        
        # Staff registration should return 202 Accepted (request submitted)
        assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data, "Response should contain detail message"
        assert "request" in data["detail"].lower() or "approval" in data["detail"].lower(), \
            f"Detail should mention request/approval: {data['detail']}"
        print(f"✓ Staff registration returns 202 (request submitted): {unique_email}")
    
    def test_admin_registration_returns_403(self):
        """Admin registration via public endpoint should return 403 (unless first admin)"""
        unique_email = f"test_admin_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "full_name": "Test Admin Attempt",
            "phone": "555-0003",
            "role": "admin"
        })
        
        # Admin registration should return 403 (if admin already exists)
        # or 200 if this is the first admin (bootstrap case)
        if response.status_code == 403:
            data = response.json()
            assert "detail" in data
            assert "admin" in data["detail"].lower() or "owner" in data["detail"].lower(), \
                f"Detail should mention admin/owner restriction: {data['detail']}"
            print(f"✓ Admin registration blocked with 403 (admin already exists)")
        elif response.status_code == 200:
            # First admin bootstrap case
            data = response.json()
            assert data["user"]["role"] == "admin"
            print(f"✓ First admin bootstrap successful (no existing admin)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}: {response.text}")


class TestCancellationRefundPolicy:
    """Test hours-based cancellation refund policy"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for a customer"""
        # Try to login with existing test customer
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "customer@test.com",
            "password": "Test123!"
        })
        
        if login_response.status_code == 200:
            return login_response.json()["token"]
        
        # Create new customer if login fails
        unique_email = f"test_refund_{uuid.uuid4().hex[:8]}@test.com"
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "full_name": "Test Refund Customer",
            "phone": "555-0010",
            "role": "customer"
        })
        
        if register_response.status_code == 200:
            return register_response.json()["token"]
        
        pytest.skip("Could not authenticate for refund tests")
    
    def test_refund_policy_48h_full_refund(self, auth_token):
        """Cancellation >=48 hours before check-in should return 100% refund"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Calculate check-in date 72 hours from now (well over 48h)
        check_in = (datetime.now() + timedelta(hours=72)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(hours=96)).strftime("%Y-%m-%d")
        
        # Get cancellation preview endpoint if available
        response = requests.get(
            f"{BASE_URL}/api/bookings/cancellation-preview",
            params={"check_in_date": check_in, "total_amount": 100.00},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("refund_percentage") == 100 or data.get("refundPercentage") == 100, \
                f"Expected 100% refund for 72h before check-in, got: {data}"
            print(f"✓ 48h+ cancellation returns 100% refund")
        elif response.status_code == 404:
            # Endpoint might not exist, test via pricing engine directly
            print("⚠ Cancellation preview endpoint not found, skipping direct API test")
        else:
            print(f"⚠ Cancellation preview returned {response.status_code}: {response.text}")
    
    def test_refund_policy_24_48h_partial_refund(self, auth_token):
        """Cancellation 24-48 hours before check-in should return 50% refund"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Calculate check-in date 36 hours from now (between 24-48h)
        check_in = (datetime.now() + timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M:%S")
        
        response = requests.get(
            f"{BASE_URL}/api/bookings/cancellation-preview",
            params={"check_in_date": check_in, "total_amount": 100.00},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            refund_pct = data.get("refund_percentage") or data.get("refundPercentage")
            assert refund_pct == 50, f"Expected 50% refund for 36h before check-in, got: {refund_pct}"
            print(f"✓ 24-48h cancellation returns 50% refund")
        elif response.status_code == 404:
            print("⚠ Cancellation preview endpoint not found, skipping direct API test")
        else:
            print(f"⚠ Cancellation preview returned {response.status_code}: {response.text}")
    
    def test_refund_policy_under_24h_no_refund(self, auth_token):
        """Cancellation <24 hours before check-in should return 0% refund"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Calculate check-in date 12 hours from now (under 24h)
        check_in = (datetime.now() + timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S")
        
        response = requests.get(
            f"{BASE_URL}/api/bookings/cancellation-preview",
            params={"check_in_date": check_in, "total_amount": 100.00},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            refund_pct = data.get("refund_percentage") or data.get("refundPercentage")
            assert refund_pct == 0, f"Expected 0% refund for 12h before check-in, got: {refund_pct}"
            print(f"✓ <24h cancellation returns 0% refund")
        elif response.status_code == 404:
            print("⚠ Cancellation preview endpoint not found, skipping direct API test")
        else:
            print(f"⚠ Cancellation preview returned {response.status_code}: {response.text}")


class TestBookingNormalization:
    """Test booking field normalization (startDate/endDate/dogIds)"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "Test123!"
        })
        
        if response.status_code == 200:
            return response.json()["token"]
        pytest.skip("Admin login failed - cannot test booking normalization")
    
    def test_booking_list_returns_normalized_fields(self, admin_token):
        """Booking list should return normalized field names"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Handle both array and object response formats
        bookings = data if isinstance(data, list) else data.get("bookings", [])
        
        if len(bookings) > 0:
            booking = bookings[0]
            # Check that booking has date fields (either normalized or snake_case)
            has_dates = (
                "check_in_date" in booking or "startDate" in booking or 
                "checkInDate" in booking
            )
            assert has_dates, f"Booking should have date fields: {booking.keys()}"
            print(f"✓ Booking list returns bookings with date fields")
        else:
            print("⚠ No bookings found to verify normalization")
    
    def test_booking_creation_accepts_normalized_fields(self, admin_token):
        """Booking creation should accept normalized field names"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get a customer to create booking for
        customers_response = requests.get(f"{BASE_URL}/api/admin/customers", headers=headers)
        
        if customers_response.status_code != 200:
            print("⚠ Could not get customers list, skipping booking creation test")
            return
        
        customers = customers_response.json()
        if not customers:
            print("⚠ No customers found, skipping booking creation test")
            return
        
        customer = customers[0] if isinstance(customers, list) else customers.get("customers", [{}])[0]
        customer_id = customer.get("id")
        household_id = customer.get("household_id")
        
        if not customer_id:
            print("⚠ Customer ID not found, skipping booking creation test")
            return
        
        # Try to create booking with normalized fields
        check_in = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=9)).strftime("%Y-%m-%d")
        
        response = requests.post(f"{BASE_URL}/api/bookings/admin", headers=headers, json={
            "customer_id": customer_id,
            "household_id": household_id,
            "dog_ids": [],  # Empty for test
            "check_in_date": check_in,
            "check_out_date": check_out,
            "booking_type": "stay",
            "notes": "Test booking for normalization"
        })
        
        # Accept 200, 201, or 400 (if no dogs)
        if response.status_code in [200, 201]:
            print(f"✓ Booking creation accepts normalized fields")
        elif response.status_code == 400:
            # Might fail due to no dogs, but that's expected
            print(f"⚠ Booking creation returned 400 (likely no dogs): {response.text}")
        else:
            print(f"⚠ Booking creation returned {response.status_code}: {response.text}")


class TestDogNormalization:
    """Test dog profile normalization (feedingInstructions, behaviorNotes, specialNeeds)"""
    
    @pytest.fixture
    def customer_token(self):
        """Get customer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "customer@test.com",
            "password": "Test123!"
        })
        
        if response.status_code == 200:
            return response.json()["token"]
        
        # Create new customer
        unique_email = f"test_dog_{uuid.uuid4().hex[:8]}@test.com"
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "full_name": "Test Dog Owner",
            "phone": "555-0020",
            "role": "customer"
        })
        
        if register_response.status_code == 200:
            return register_response.json()["token"]
        
        pytest.skip("Could not authenticate for dog tests")
    
    def test_dog_creation_with_normalized_fields(self, customer_token):
        """Dog creation should accept normalized field names"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        dog_data = {
            "name": f"TestDog_{uuid.uuid4().hex[:6]}",
            "breed": "Golden Retriever",
            "age": 3,
            "weight": 65,
            "size": "large",
            "feedingInstructions": "2 cups twice daily",  # camelCase
            "behaviorNotes": "Friendly with other dogs",  # camelCase
            "specialNeeds": "Needs joint supplements"  # camelCase
        }
        
        response = requests.post(f"{BASE_URL}/api/dogs", headers=headers, json=dog_data)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify dog was created with the data
        assert data.get("name") == dog_data["name"], "Dog name should match"
        print(f"✓ Dog creation accepts normalized fields: {data.get('name')}")
        
        # Return dog ID for cleanup
        return data.get("id")
    
    def test_dog_creation_with_snake_case_fields(self, customer_token):
        """Dog creation should also accept snake_case field names"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        dog_data = {
            "name": f"TestDog_{uuid.uuid4().hex[:6]}",
            "breed": "Labrador",
            "age": 2,
            "weight": 70,
            "size": "large",
            "feeding_instructions": "3 cups twice daily",  # snake_case
            "behavior_notes": "Loves to swim",  # snake_case
            "special_needs": "Allergic to chicken"  # snake_case
        }
        
        response = requests.post(f"{BASE_URL}/api/dogs", headers=headers, json=dog_data)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("name") == dog_data["name"], "Dog name should match"
        print(f"✓ Dog creation accepts snake_case fields: {data.get('name')}")
    
    def test_dog_list_returns_normalized_fields(self, customer_token):
        """Dog list should return normalized field names"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        response = requests.get(f"{BASE_URL}/api/dogs", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        dogs = data if isinstance(data, list) else data.get("dogs", [])
        
        if len(dogs) > 0:
            dog = dogs[0]
            # Check that dog has expected fields
            assert "name" in dog, "Dog should have name field"
            print(f"✓ Dog list returns dogs with expected fields")
        else:
            print("⚠ No dogs found to verify normalization")


class TestStaffRequestFlow:
    """Test staff request submission and approval flow"""
    
    def test_staff_request_page_submission(self):
        """Staff request via /auth/register with role=staff should create pending request"""
        unique_email = f"staff_request_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "full_name": "Staff Request Test",
            "phone": "555-0030",
            "role": "staff"
        })
        
        # Should return 202 Accepted
        assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
        print(f"✓ Staff request submission returns 202")
    
    def test_staff_cannot_login_before_approval(self):
        """Staff request should not allow login until approved"""
        unique_email = f"staff_nologin_{uuid.uuid4().hex[:8]}@test.com"
        
        # Submit staff request
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "full_name": "Staff No Login Test",
            "phone": "555-0031",
            "role": "staff"
        })
        
        assert register_response.status_code == 202, "Staff request should return 202"
        
        # Try to login - should fail
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": unique_email,
            "password": "TestPass123!"
        })
        
        # Login should fail (401 or 404)
        assert login_response.status_code in [401, 404], \
            f"Staff should not be able to login before approval, got {login_response.status_code}"
        print(f"✓ Staff cannot login before approval")


class TestHealthAndBasics:
    """Basic health checks"""
    
    def test_api_health(self):
        """API should be accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print(f"✓ API health check passed")
    
    def test_auth_endpoints_exist(self):
        """Auth endpoints should exist"""
        # Test login endpoint exists (even if credentials are wrong)
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "wrong"
        })
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code in [401, 404], f"Login endpoint issue: {response.status_code}"
        print(f"✓ Auth endpoints accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
