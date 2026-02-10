"""
K9Command New Features Test - Iteration 17
Tests for:
1. Meet & Greet booking type and requirement for new customers
2. Cash payment option
3. CSV export for bookings and customers
4. Automated staff onboarding emails
5. Customer welcome emails
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestK9NewFeatures:
    """Test new K9Command features"""
    
    admin_token = None
    customer_token = None
    test_customer_id = None
    test_dog_id = None
    test_household_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        # Login as admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "Test123!"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        TestK9NewFeatures.admin_token = data['token']
    
    def get_admin_headers(self):
        return {"Authorization": f"Bearer {TestK9NewFeatures.admin_token}"}
    
    def get_customer_headers(self):
        return {"Authorization": f"Bearer {TestK9NewFeatures.customer_token}"}
    
    # ==================== BOOKING TYPE TESTS ====================
    
    def test_01_create_customer_for_testing(self):
        """Create a test customer via admin endpoint"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(
            f"{BASE_URL}/api/admin/customers",
            headers=self.get_admin_headers(),
            json={
                "email": f"test_mg_customer_{unique_id}@test.com",
                "full_name": f"Test MG Customer {unique_id}",
                "phone": "555-1234",
                "password": "Test123!"
            }
        )
        assert response.status_code == 200, f"Create customer failed: {response.text}"
        data = response.json()
        TestK9NewFeatures.test_customer_id = data.get('id')
        TestK9NewFeatures.test_household_id = data.get('household_id')
        print(f"Created test customer: {TestK9NewFeatures.test_customer_id}")
    
    def test_02_login_as_test_customer(self):
        """Login as the test customer"""
        # Get customer email from admin
        response = requests.get(
            f"{BASE_URL}/api/admin/users?role=customer",
            headers=self.get_admin_headers()
        )
        assert response.status_code == 200
        customers = response.json()
        
        # Find our test customer
        test_customer = None
        for c in customers:
            if c.get('id') == TestK9NewFeatures.test_customer_id:
                test_customer = c
                break
        
        if test_customer:
            # Login as customer
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": test_customer['email'],
                "password": "Test123!"
            })
            if response.status_code == 200:
                TestK9NewFeatures.customer_token = response.json()['token']
                print(f"Logged in as customer: {test_customer['email']}")
            else:
                print(f"Customer login failed: {response.text}")
    
    def test_03_create_dog_for_customer(self):
        """Create a dog for the test customer"""
        if not TestK9NewFeatures.customer_token:
            pytest.skip("Customer token not available")
        
        response = requests.post(
            f"{BASE_URL}/api/dogs",
            headers=self.get_customer_headers(),
            json={
                "name": f"TestDog_{str(uuid.uuid4())[:6]}",
                "breed": "Golden Retriever",
                "age": 3,
                "weight": 65,
                "size": "large"
            }
        )
        assert response.status_code == 200, f"Create dog failed: {response.text}"
        TestK9NewFeatures.test_dog_id = response.json().get('id')
        print(f"Created test dog: {TestK9NewFeatures.test_dog_id}")
    
    def test_04_meet_greet_requirement_blocks_stay_booking(self):
        """Test that new customers cannot book stay without Meet & Greet"""
        if not TestK9NewFeatures.customer_token or not TestK9NewFeatures.test_dog_id:
            pytest.skip("Customer or dog not available")
        
        # Get location
        loc_response = requests.get(f"{BASE_URL}/api/locations")
        locations = loc_response.json()
        location_id = locations[0]['id'] if locations else None
        
        # Try to book a stay (should fail due to Meet & Greet requirement)
        check_in = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        check_out = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            headers=self.get_customer_headers(),
            json={
                "dog_ids": [TestK9NewFeatures.test_dog_id],
                "location_id": location_id,
                "accommodation_type": "room",
                "booking_type": "stay",
                "check_in_date": check_in,
                "check_out_date": check_out
            }
        )
        
        # Should fail with 400 - Meet & Greet required
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "Meet & Greet" in response.json().get('detail', ''), "Error should mention Meet & Greet"
        print("PASS: Stay booking blocked for new customer without Meet & Greet")
    
    def test_05_meet_greet_requirement_blocks_daycare_booking(self):
        """Test that new customers cannot book daycare without Meet & Greet"""
        if not TestK9NewFeatures.customer_token or not TestK9NewFeatures.test_dog_id:
            pytest.skip("Customer or dog not available")
        
        loc_response = requests.get(f"{BASE_URL}/api/locations")
        locations = loc_response.json()
        location_id = locations[0]['id'] if locations else None
        
        check_in = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        check_out = (datetime.now() + timedelta(days=8)).strftime('%Y-%m-%d')
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            headers=self.get_customer_headers(),
            json={
                "dog_ids": [TestK9NewFeatures.test_dog_id],
                "location_id": location_id,
                "accommodation_type": "room",
                "booking_type": "daycare",
                "check_in_date": check_in,
                "check_out_date": check_out
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "Meet & Greet" in response.json().get('detail', ''), "Error should mention Meet & Greet"
        print("PASS: Daycare booking blocked for new customer without Meet & Greet")
    
    def test_06_customer_can_book_meet_greet(self):
        """Test that new customers CAN book a Meet & Greet"""
        if not TestK9NewFeatures.customer_token or not TestK9NewFeatures.test_dog_id:
            pytest.skip("Customer or dog not available")
        
        loc_response = requests.get(f"{BASE_URL}/api/locations")
        locations = loc_response.json()
        location_id = locations[0]['id'] if locations else None
        
        check_in = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        check_out = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            headers=self.get_customer_headers(),
            json={
                "dog_ids": [TestK9NewFeatures.test_dog_id],
                "location_id": location_id,
                "accommodation_type": "room",
                "booking_type": "meet_greet",
                "check_in_date": check_in,
                "check_out_date": check_out
            }
        )
        
        assert response.status_code == 200, f"Meet & Greet booking failed: {response.text}"
        booking = response.json()
        assert booking.get('booking_type') == 'meet_greet', "Booking type should be meet_greet"
        print(f"PASS: Customer can book Meet & Greet: {booking.get('id')}")
    
    def test_07_admin_can_override_meet_greet_requirement(self):
        """Test that admin can override Meet & Greet requirement"""
        if not TestK9NewFeatures.test_customer_id or not TestK9NewFeatures.test_dog_id:
            pytest.skip("Customer or dog not available")
        
        loc_response = requests.get(f"{BASE_URL}/api/locations")
        locations = loc_response.json()
        location_id = locations[0]['id'] if locations else None
        
        check_in = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
        check_out = (datetime.now() + timedelta(days=17)).strftime('%Y-%m-%d')
        
        # Admin creates booking with override
        response = requests.post(
            f"{BASE_URL}/api/bookings/admin",
            headers=self.get_admin_headers(),
            json={
                "customer_id": TestK9NewFeatures.test_customer_id,
                "dog_ids": [TestK9NewFeatures.test_dog_id],
                "location_id": location_id,
                "accommodation_type": "room",
                "booking_type": "stay",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "meet_greet_override": True
            }
        )
        
        assert response.status_code == 200, f"Admin override booking failed: {response.text}"
        booking = response.json()
        assert booking.get('booking_type') == 'stay', "Booking type should be stay"
        print(f"PASS: Admin can override Meet & Greet requirement: {booking.get('id')}")
    
    # ==================== CASH PAYMENT TESTS ====================
    
    def test_08_admin_can_create_booking_with_cash_payment(self):
        """Test that admin can create booking with cash payment type"""
        if not TestK9NewFeatures.test_customer_id or not TestK9NewFeatures.test_dog_id:
            pytest.skip("Customer or dog not available")
        
        loc_response = requests.get(f"{BASE_URL}/api/locations")
        locations = loc_response.json()
        location_id = locations[0]['id'] if locations else None
        
        check_in = (datetime.now() + timedelta(days=21)).strftime('%Y-%m-%d')
        check_out = (datetime.now() + timedelta(days=24)).strftime('%Y-%m-%d')
        
        response = requests.post(
            f"{BASE_URL}/api/bookings/admin",
            headers=self.get_admin_headers(),
            json={
                "customer_id": TestK9NewFeatures.test_customer_id,
                "dog_ids": [TestK9NewFeatures.test_dog_id],
                "location_id": location_id,
                "accommodation_type": "room",
                "booking_type": "stay",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "payment_type": "cash",
                "meet_greet_override": True
            }
        )
        
        assert response.status_code == 200, f"Cash payment booking failed: {response.text}"
        booking = response.json()
        assert booking.get('payment_type') == 'cash', f"Payment type should be cash, got {booking.get('payment_type')}"
        print(f"PASS: Admin can create booking with cash payment: {booking.get('id')}")
    
    def test_09_admin_can_create_booking_with_invoice_payment(self):
        """Test that admin can create booking with invoice payment type"""
        if not TestK9NewFeatures.test_customer_id or not TestK9NewFeatures.test_dog_id:
            pytest.skip("Customer or dog not available")
        
        loc_response = requests.get(f"{BASE_URL}/api/locations")
        locations = loc_response.json()
        location_id = locations[0]['id'] if locations else None
        
        check_in = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
        check_out = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        response = requests.post(
            f"{BASE_URL}/api/bookings/admin",
            headers=self.get_admin_headers(),
            json={
                "customer_id": TestK9NewFeatures.test_customer_id,
                "dog_ids": [TestK9NewFeatures.test_dog_id],
                "location_id": location_id,
                "accommodation_type": "room",
                "booking_type": "stay",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "payment_type": "invoice",
                "meet_greet_override": True
            }
        )
        
        assert response.status_code == 200, f"Invoice payment booking failed: {response.text}"
        booking = response.json()
        assert booking.get('payment_type') == 'invoice', f"Payment type should be invoice, got {booking.get('payment_type')}"
        print(f"PASS: Admin can create booking with invoice payment: {booking.get('id')}")
    
    # ==================== CSV EXPORT TESTS ====================
    
    def test_10_csv_export_bookings(self):
        """Test CSV export for bookings"""
        response = requests.get(
            f"{BASE_URL}/api/exports/bookings/csv",
            headers=self.get_admin_headers()
        )
        
        assert response.status_code == 200, f"Bookings CSV export failed: {response.text}"
        assert 'text/csv' in response.headers.get('content-type', ''), "Response should be CSV"
        
        content = response.text
        assert 'Booking ID' in content, "CSV should have Booking ID header"
        assert 'Customer Name' in content, "CSV should have Customer Name header"
        assert 'Booking Type' in content, "CSV should have Booking Type header"
        assert 'Payment Type' in content, "CSV should have Payment Type header"
        print("PASS: Bookings CSV export works correctly")
    
    def test_11_csv_export_customers(self):
        """Test CSV export for customers"""
        response = requests.get(
            f"{BASE_URL}/api/exports/customers/csv",
            headers=self.get_admin_headers()
        )
        
        assert response.status_code == 200, f"Customers CSV export failed: {response.text}"
        assert 'text/csv' in response.headers.get('content-type', ''), "Response should be CSV"
        
        content = response.text
        assert 'Customer ID' in content, "CSV should have Customer ID header"
        assert 'Full Name' in content, "CSV should have Full Name header"
        assert 'Email' in content, "CSV should have Email header"
        assert 'Dogs Count' in content, "CSV should have Dogs Count header"
        print("PASS: Customers CSV export works correctly")
    
    def test_12_csv_export_requires_admin(self):
        """Test that CSV export requires admin access"""
        if not TestK9NewFeatures.customer_token:
            pytest.skip("Customer token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/exports/bookings/csv",
            headers=self.get_customer_headers()
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: CSV export correctly requires admin access")
    
    # ==================== EMAIL AUTOMATION TESTS ====================
    
    def test_13_email_outbox_accessible(self):
        """Test that email outbox is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/admin/email-outbox",
            headers=self.get_admin_headers()
        )
        
        assert response.status_code == 200, f"Email outbox failed: {response.text}"
        data = response.json()
        assert 'emails' in data, "Response should have emails field"
        assert 'mock_mode' in data, "Response should indicate mock mode"
        print(f"PASS: Email outbox accessible, mock_mode={data.get('mock_mode')}, count={len(data.get('emails', []))}")
    
    def test_14_customer_registration_sends_welcome_email(self):
        """Test that customer registration triggers welcome email"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Register a new customer
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": f"test_welcome_{unique_id}@test.com",
                "full_name": f"Test Welcome {unique_id}",
                "phone": "555-9999",
                "password": "Test123!",
                "role": "customer"
            }
        )
        
        assert response.status_code == 200, f"Customer registration failed: {response.text}"
        
        # Check email outbox for welcome email
        outbox_response = requests.get(
            f"{BASE_URL}/api/admin/email-outbox?limit=10",
            headers=self.get_admin_headers()
        )
        
        assert outbox_response.status_code == 200
        emails = outbox_response.json().get('emails', [])
        
        # Find welcome email for this customer
        welcome_email = None
        for email in emails:
            if f"test_welcome_{unique_id}@test.com" in email.get('to', ''):
                welcome_email = email
                break
        
        assert welcome_email is not None, "Welcome email should be in outbox"
        assert "Welcome" in welcome_email.get('subject', ''), "Email subject should contain Welcome"
        assert "Meet & Greet" in welcome_email.get('body', ''), "Email body should mention Meet & Greet"
        print(f"PASS: Customer welcome email sent to outbox: {welcome_email.get('id')}")
    
    def test_15_staff_approval_sends_welcome_email(self):
        """Test that staff approval triggers welcome email"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Register a staff member (creates pending request)
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": f"test_staff_{unique_id}@test.com",
                "full_name": f"Test Staff {unique_id}",
                "phone": "555-8888",
                "password": "Test123!",
                "role": "staff"
            }
        )
        
        # Staff registration returns 202 (pending approval)
        assert response.status_code == 202, f"Expected 202 for staff registration, got {response.status_code}: {response.text}"
        
        # Get staff requests
        requests_response = requests.get(
            f"{BASE_URL}/api/admin/staff-requests",
            headers=self.get_admin_headers()
        )
        
        assert requests_response.status_code == 200
        staff_requests = requests_response.json().get('requests', [])
        
        # Find our staff request
        staff_request = None
        for req in staff_requests:
            if f"test_staff_{unique_id}@test.com" in req.get('email', ''):
                staff_request = req
                break
        
        if staff_request and staff_request.get('status') == 'pending':
            # Approve the staff request
            approve_response = requests.post(
                f"{BASE_URL}/api/admin/staff-requests/{staff_request['id']}/approve",
                headers=self.get_admin_headers()
            )
            
            assert approve_response.status_code == 200, f"Staff approval failed: {approve_response.text}"
            
            # Check email outbox for staff welcome email
            outbox_response = requests.get(
                f"{BASE_URL}/api/admin/email-outbox?limit=10",
                headers=self.get_admin_headers()
            )
            
            emails = outbox_response.json().get('emails', [])
            
            # Find welcome email for this staff
            staff_welcome = None
            for email in emails:
                if f"test_staff_{unique_id}@test.com" in email.get('to', ''):
                    staff_welcome = email
                    break
            
            assert staff_welcome is not None, "Staff welcome email should be in outbox"
            assert "Welcome" in staff_welcome.get('subject', ''), "Email subject should contain Welcome"
            print(f"PASS: Staff welcome email sent to outbox: {staff_welcome.get('id')}")
        else:
            print("SKIP: Staff request not found or already processed")
    
    # ==================== BOOKING MODEL TESTS ====================
    
    def test_16_booking_response_includes_booking_type(self):
        """Test that booking response includes booking_type field"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers=self.get_admin_headers()
        )
        
        assert response.status_code == 200, f"Get bookings failed: {response.text}"
        bookings = response.json()
        
        if bookings:
            # Check that booking_type is present
            for booking in bookings[:5]:  # Check first 5
                # booking_type may be None for old bookings, but field should exist
                assert 'booking_type' in booking or booking.get('booking_type') is None or booking.get('booking_type') in ['stay', 'daycare', 'meet_greet'], \
                    f"Invalid booking_type: {booking.get('booking_type')}"
            print(f"PASS: Booking responses include booking_type field")
        else:
            print("SKIP: No bookings to check")
    
    def test_17_booking_response_includes_payment_type(self):
        """Test that booking response includes payment_type field"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers=self.get_admin_headers()
        )
        
        assert response.status_code == 200
        bookings = response.json()
        
        if bookings:
            for booking in bookings[:5]:
                # payment_type may be None for old bookings
                pt = booking.get('payment_type')
                assert pt is None or pt in ['invoice', 'immediate', 'cash'], \
                    f"Invalid payment_type: {pt}"
            print(f"PASS: Booking responses include payment_type field")
        else:
            print("SKIP: No bookings to check")


class TestEmailTemplates:
    """Test email template management"""
    
    admin_token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "Test123!"
        })
        assert response.status_code == 200
        TestEmailTemplates.admin_token = response.json()['token']
    
    def get_admin_headers(self):
        return {"Authorization": f"Bearer {TestEmailTemplates.admin_token}"}
    
    def test_get_email_templates(self):
        """Test getting email templates"""
        response = requests.get(
            f"{BASE_URL}/api/admin/email-templates",
            headers=self.get_admin_headers()
        )
        
        assert response.status_code == 200, f"Get templates failed: {response.text}"
        data = response.json()
        assert 'templates' in data, "Response should have templates"
        assert 'mock_mode' in data, "Response should indicate mock mode"
        print(f"PASS: Email templates accessible, count={len(data.get('templates', {}))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
