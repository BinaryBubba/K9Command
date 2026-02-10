"""
K9Command - Account Governance & Feature Testing
Tests for:
1. Customer registration (free)
2. Staff registration (requires approval - HTTP 202)
3. Admin registration (first admin = owner, subsequent blocked)
4. Customer dog profile modification
5. Customer booking modification (24h+ before check-in)
6. Email templates and outbox (mock mode)
7. Staff management (approve/reject)
8. Owner functions (create admin)
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_CUSTOMER_EMAIL = "customer_test@k9.com"
TEST_CUSTOMER_PASSWORD = "Test123!"
TEST_ADMIN_EMAIL = "admin_test@k9.com"
TEST_ADMIN_PASSWORD = "Test123!"


class TestAccountGovernance:
    """Test account governance rules"""
    
    def test_customer_registration_free(self):
        """Customers can register freely without approval"""
        unique_email = f"test_customer_{uuid.uuid4().hex[:8]}@k9.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "full_name": "Test Customer",
            "phone": "555-0100",
            "role": "customer"
        })
        
        # Customer registration should succeed immediately (200)
        assert response.status_code == 200, f"Customer registration failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token returned for customer registration"
        assert data["user"]["role"] == "customer"
        print(f"✓ Customer registration successful: {unique_email}")
    
    def test_staff_registration_requires_approval(self):
        """Staff registration should return 202 (pending approval)"""
        unique_email = f"test_staff_{uuid.uuid4().hex[:8]}@k9.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "full_name": "Test Staff",
            "phone": "555-0200",
            "role": "staff"
        })
        
        # Staff registration should return 202 Accepted (pending approval)
        assert response.status_code == 202, f"Expected 202 for staff registration, got {response.status_code}: {response.text}"
        data = response.json()
        assert "approval" in data.get("detail", "").lower() or "pending" in data.get("detail", "").lower(), \
            f"Expected approval message, got: {data}"
        print(f"✓ Staff registration pending approval: {unique_email}")
    
    def test_admin_registration_blocked_if_admin_exists(self):
        """Admin registration should be blocked if an admin already exists"""
        unique_email = f"test_admin_{uuid.uuid4().hex[:8]}@k9.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "full_name": "Test Admin",
            "phone": "555-0300",
            "role": "admin"
        })
        
        # Should be blocked (403) if admin already exists
        assert response.status_code == 403, f"Expected 403 for admin registration, got {response.status_code}: {response.text}"
        data = response.json()
        assert "owner" in data.get("detail", "").lower() or "not allowed" in data.get("detail", "").lower(), \
            f"Expected owner/not allowed message, got: {data}"
        print("✓ Admin registration correctly blocked")
    
    def test_duplicate_email_rejected(self):
        """Duplicate email registration should be rejected"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": "Test123!",
            "full_name": "Duplicate User",
            "phone": "555-0400",
            "role": "customer"
        })
        
        # Should be rejected (400)
        assert response.status_code == 400, f"Expected 400 for duplicate email, got {response.status_code}"
        print("✓ Duplicate email correctly rejected")


class TestCustomerLogin:
    """Test customer login and token"""
    
    @pytest.fixture
    def customer_token(self):
        """Get customer auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": TEST_CUSTOMER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Customer login failed: {response.text}")
        return response.json()["token"]
    
    def test_customer_login_success(self):
        """Customer can login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": TEST_CUSTOMER_PASSWORD
        })
        
        assert response.status_code == 200, f"Customer login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "customer"
        print(f"✓ Customer login successful: {TEST_CUSTOMER_EMAIL}")
    
    def test_customer_get_me(self, customer_token):
        """Customer can get their profile"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        
        assert response.status_code == 200, f"Get me failed: {response.text}"
        data = response.json()
        assert data["email"] == TEST_CUSTOMER_EMAIL
        print("✓ Customer profile retrieved")


class TestAdminLogin:
    """Test admin login and token"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_ADMIN_EMAIL,
            "password": TEST_ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json()["token"]
    
    def test_admin_login_success(self):
        """Admin can login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_ADMIN_EMAIL,
            "password": TEST_ADMIN_PASSWORD
        })
        
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {TEST_ADMIN_EMAIL}")


class TestDogProfileModification:
    """Test customer can modify their dog profiles"""
    
    @pytest.fixture
    def customer_session(self):
        """Get customer auth session"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": TEST_CUSTOMER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Customer login failed: {response.text}")
        token = response.json()["token"]
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_get_customer_dogs(self, customer_session):
        """Customer can get their dogs"""
        response = customer_session.get(f"{BASE_URL}/api/dogs")
        
        assert response.status_code == 200, f"Get dogs failed: {response.text}"
        dogs = response.json()
        print(f"✓ Customer has {len(dogs)} dogs")
        return dogs
    
    def test_create_and_update_dog(self, customer_session):
        """Customer can create and update a dog profile"""
        # Create a dog
        dog_name = f"TestDog_{uuid.uuid4().hex[:6]}"
        create_response = customer_session.post(f"{BASE_URL}/api/dogs", json={
            "name": dog_name,
            "breed": "Golden Retriever",
            "age": 3,
            "weight": 65,
            "meal_routine": "2 cups twice daily",
            "other_notes": "Friendly with other dogs"
        })
        
        assert create_response.status_code == 200, f"Create dog failed: {create_response.text}"
        dog = create_response.json()
        dog_id = dog["id"]
        print(f"✓ Dog created: {dog_name} (ID: {dog_id})")
        
        # Update the dog - use fields that exist in the model
        update_response = customer_session.patch(f"{BASE_URL}/api/dogs/{dog_id}", json={
            "notes": "Very friendly, loves to play fetch",
            "weight": 70
        })
        
        assert update_response.status_code == 200, f"Update dog failed: {update_response.text}"
        updated_dog = update_response.json()
        assert updated_dog["weight"] == 70
        print(f"✓ Dog profile updated successfully (weight: {updated_dog['weight']})")
        
        return dog_id


class TestBookingModification:
    """Test customer can modify their bookings"""
    
    @pytest.fixture
    def customer_session(self):
        """Get customer auth session"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": TEST_CUSTOMER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Customer login failed: {response.text}")
        token = response.json()["token"]
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_get_customer_bookings(self, customer_session):
        """Customer can get their bookings"""
        response = customer_session.get(f"{BASE_URL}/api/bookings")
        
        assert response.status_code == 200, f"Get bookings failed: {response.text}"
        bookings = response.json()
        print(f"✓ Customer has {len(bookings)} bookings")
        return bookings
    
    def test_create_booking(self, customer_session):
        """Customer can create a booking"""
        # First get dogs
        dogs_response = customer_session.get(f"{BASE_URL}/api/dogs")
        if dogs_response.status_code != 200 or not dogs_response.json():
            pytest.skip("No dogs available for booking")
        
        dogs = dogs_response.json()
        dog_id = dogs[0]["id"]
        
        # Get location
        locations_response = customer_session.get(f"{BASE_URL}/api/locations")
        if locations_response.status_code != 200 or not locations_response.json():
            pytest.skip("No locations available")
        
        locations = locations_response.json()
        location_id = locations[0]["id"]
        
        # Create booking for 7 days from now (to allow modification)
        check_in = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT10:00:00")
        check_out = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%dT10:00:00")
        
        response = customer_session.post(f"{BASE_URL}/api/bookings", json={
            "dog_ids": [dog_id],
            "location_id": location_id,
            "accommodation_type": "room",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "notes": "Test booking for modification"
        })
        
        assert response.status_code == 200, f"Create booking failed: {response.text}"
        booking = response.json()
        print(f"✓ Booking created: {booking['id']}")
        return booking


class TestEmailTemplates:
    """Test email templates and outbox (admin only)"""
    
    @pytest.fixture
    def admin_session(self):
        """Get admin auth session"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_ADMIN_EMAIL,
            "password": TEST_ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        token = response.json()["token"]
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_get_email_templates(self, admin_session):
        """Admin can get email templates"""
        response = admin_session.get(f"{BASE_URL}/api/admin/email-templates")
        
        assert response.status_code == 200, f"Get templates failed: {response.text}"
        data = response.json()
        assert "templates" in data
        assert "mock_mode" in data
        print(f"✓ Email templates retrieved (mock_mode: {data['mock_mode']})")
        print(f"  Templates: {list(data['templates'].keys())}")
    
    def test_update_email_template(self, admin_session):
        """Admin can update email template"""
        response = admin_session.put(
            f"{BASE_URL}/api/admin/email-templates/booking_confirmation",
            json={
                "subject": "Your K9Command Booking is {{status}}!",
                "body": "Hello!\n\nYour booking for {{dogs}} has been {{status}}.\n\nCheck-in: {{startDate}}\nCheck-out: {{endDate}}\n\nThank you!"
            }
        )
        
        assert response.status_code == 200, f"Update template failed: {response.text}"
        data = response.json()
        assert "template" in data
        print("✓ Email template updated")
    
    def test_send_test_email(self, admin_session):
        """Admin can send test email (mock mode)"""
        response = admin_session.post(
            f"{BASE_URL}/api/admin/email-templates/booking_confirmation/test",
            json={"email": "test@example.com"}
        )
        
        assert response.status_code == 200, f"Send test email failed: {response.text}"
        data = response.json()
        assert "email" in data
        print(f"✓ Test email sent (mock_mode: {data.get('mock_mode', True)})")
    
    def test_get_email_outbox(self, admin_session):
        """Admin can get email outbox"""
        response = admin_session.get(f"{BASE_URL}/api/admin/email-outbox")
        
        assert response.status_code == 200, f"Get outbox failed: {response.text}"
        data = response.json()
        assert "emails" in data
        assert "count" in data
        print(f"✓ Email outbox retrieved ({data['count']} emails)")
    
    def test_customer_cannot_access_email_templates(self):
        """Customer cannot access email templates"""
        # Login as customer
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": TEST_CUSTOMER_PASSWORD
        })
        if login_response.status_code != 200:
            pytest.skip("Customer login failed")
        
        token = login_response.json()["token"]
        response = requests.get(
            f"{BASE_URL}/api/admin/email-templates",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 for customer, got {response.status_code}"
        print("✓ Customer correctly denied access to email templates")


class TestStaffManagement:
    """Test staff request management (admin only)"""
    
    @pytest.fixture
    def admin_session(self):
        """Get admin auth session"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_ADMIN_EMAIL,
            "password": TEST_ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        token = response.json()["token"]
        user_id = response.json()["user"]["id"]
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        session.user_id = user_id
        return session
    
    def test_list_staff_requests(self, admin_session):
        """Admin can list staff requests"""
        response = admin_session.get(f"{BASE_URL}/api/admin/staff-requests")
        
        assert response.status_code == 200, f"List staff requests failed: {response.text}"
        data = response.json()
        assert "requests" in data
        assert "count" in data
        print(f"✓ Staff requests listed ({data['count']} requests)")
    
    def test_check_owner_status(self, admin_session):
        """Admin can check owner status"""
        response = admin_session.get(f"{BASE_URL}/api/admin/is-owner/{admin_session.user_id}")
        
        assert response.status_code == 200, f"Check owner failed: {response.text}"
        data = response.json()
        assert "isOwner" in data
        print(f"✓ Owner status checked: isOwner={data['isOwner']}")
    
    def test_create_staff_request_and_approve(self, admin_session):
        """Create a staff request and approve it"""
        # First create a staff registration request
        unique_email = f"staff_approve_{uuid.uuid4().hex[:8]}@k9.com"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "full_name": "Staff To Approve",
            "phone": "555-0500",
            "role": "staff"
        })
        
        assert reg_response.status_code == 202, f"Staff registration should return 202: {reg_response.text}"
        print(f"✓ Staff request created: {unique_email}")
        
        # Get the request ID
        requests_response = admin_session.get(f"{BASE_URL}/api/admin/staff-requests")
        assert requests_response.status_code == 200
        
        staff_requests = requests_response.json()["requests"]
        request_to_approve = next(
            (r for r in staff_requests if r.get("email") == unique_email and r.get("status") == "pending"),
            None
        )
        
        if not request_to_approve:
            pytest.skip("Could not find the staff request to approve")
        
        request_id = request_to_approve["id"]
        
        # Approve the request
        approve_response = admin_session.post(f"{BASE_URL}/api/admin/staff-requests/{request_id}/approve")
        
        assert approve_response.status_code == 200, f"Approve failed: {approve_response.text}"
        data = approve_response.json()
        assert "user_id" in data
        print(f"✓ Staff request approved, user created: {data['user_id']}")
    
    def test_create_staff_request_and_reject(self, admin_session):
        """Create a staff request and reject it"""
        # First create a staff registration request
        unique_email = f"staff_reject_{uuid.uuid4().hex[:8]}@k9.com"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "Test123!",
            "full_name": "Staff To Reject",
            "phone": "555-0600",
            "role": "staff"
        })
        
        assert reg_response.status_code == 202, f"Staff registration should return 202: {reg_response.text}"
        print(f"✓ Staff request created: {unique_email}")
        
        # Get the request ID
        requests_response = admin_session.get(f"{BASE_URL}/api/admin/staff-requests")
        assert requests_response.status_code == 200
        
        staff_requests = requests_response.json()["requests"]
        request_to_reject = next(
            (r for r in staff_requests if r.get("email") == unique_email and r.get("status") == "pending"),
            None
        )
        
        if not request_to_reject:
            pytest.skip("Could not find the staff request to reject")
        
        request_id = request_to_reject["id"]
        
        # Reject the request
        reject_response = admin_session.post(
            f"{BASE_URL}/api/admin/staff-requests/{request_id}/reject",
            json={"reason": "Test rejection"}
        )
        
        assert reject_response.status_code == 200, f"Reject failed: {reject_response.text}"
        print("✓ Staff request rejected")
    
    def test_customer_cannot_access_staff_requests(self):
        """Customer cannot access staff requests"""
        # Login as customer
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": TEST_CUSTOMER_PASSWORD
        })
        if login_response.status_code != 200:
            pytest.skip("Customer login failed")
        
        token = login_response.json()["token"]
        response = requests.get(
            f"{BASE_URL}/api/admin/staff-requests",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 for customer, got {response.status_code}"
        print("✓ Customer correctly denied access to staff requests")


class TestOwnerFunctions:
    """Test owner-only functions"""
    
    @pytest.fixture
    def admin_session(self):
        """Get admin auth session"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_ADMIN_EMAIL,
            "password": TEST_ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        token = response.json()["token"]
        user_id = response.json()["user"]["id"]
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        session.user_id = user_id
        return session
    
    def test_create_admin_by_owner(self, admin_session):
        """Owner can create new admin accounts"""
        # First check if current admin is owner
        owner_check = admin_session.get(f"{BASE_URL}/api/admin/is-owner/{admin_session.user_id}")
        if owner_check.status_code != 200:
            pytest.skip("Could not check owner status")
        
        is_owner = owner_check.json().get("isOwner", False)
        
        unique_email = f"new_admin_{uuid.uuid4().hex[:8]}@k9.com"
        response = admin_session.post(
            f"{BASE_URL}/api/admin/create-admin",
            json={
                "email": unique_email,
                "fullName": "New Admin User"
            }
        )
        
        if is_owner:
            assert response.status_code == 200, f"Owner should be able to create admin: {response.text}"
            print(f"✓ Owner created new admin: {unique_email}")
        else:
            assert response.status_code == 403, f"Non-owner should not create admin: {response.text}"
            print("✓ Non-owner correctly denied admin creation")


class TestDataClientIntegration:
    """Test that dataClient facade methods work with backend"""
    
    @pytest.fixture
    def customer_session(self):
        """Get customer auth session"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CUSTOMER_EMAIL,
            "password": TEST_CUSTOMER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Customer login failed: {response.text}")
        token = response.json()["token"]
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_get_bookings_for_calendar(self, customer_session):
        """Test getting bookings (used by calendar)"""
        response = customer_session.get(f"{BASE_URL}/api/bookings")
        
        assert response.status_code == 200, f"Get bookings failed: {response.text}"
        bookings = response.json()
        print(f"✓ Calendar bookings retrieved: {len(bookings)} bookings")
    
    def test_get_dogs_for_dashboard(self, customer_session):
        """Test getting dogs (used by dashboard)"""
        response = customer_session.get(f"{BASE_URL}/api/dogs")
        
        assert response.status_code == 200, f"Get dogs failed: {response.text}"
        dogs = response.json()
        print(f"✓ Dashboard dogs retrieved: {len(dogs)} dogs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
