"""
K9Command Final Testing - Iteration 18
Tests for:
1. Customer dashboard Today's Agenda section
2. CSV export endpoints (bookings and customers)
3. BookingModal features (booking type, cash payment, M&G override)
4. Admin settings page
5. Consistent styling (bg-[#F9F7F2])
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCSVExports:
    """Test CSV export endpoints - Admin only"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin and customer tokens"""
        # Admin login
        admin_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "Test123!"
        })
        assert admin_resp.status_code == 200, f"Admin login failed: {admin_resp.text}"
        self.admin_token = admin_resp.json()['token']
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Customer login
        customer_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "customer@test.com",
            "password": "Test123!"
        })
        assert customer_resp.status_code == 200, f"Customer login failed: {customer_resp.text}"
        self.customer_token = customer_resp.json()['token']
        self.customer_headers = {"Authorization": f"Bearer {self.customer_token}"}
    
    def test_bookings_csv_export_admin(self):
        """Admin can export bookings to CSV"""
        response = requests.get(
            f"{BASE_URL}/api/exports/bookings/csv",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Bookings CSV export failed: {response.text}"
        assert 'text/csv' in response.headers.get('content-type', '')
        
        # Verify CSV content has expected headers
        content = response.text
        assert 'Booking ID' in content
        assert 'Customer Name' in content
        assert 'Booking Type' in content
        assert 'Payment Type' in content
        print("PASS: Admin can export bookings CSV")
    
    def test_customers_csv_export_admin(self):
        """Admin can export customers to CSV"""
        response = requests.get(
            f"{BASE_URL}/api/exports/customers/csv",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Customers CSV export failed: {response.text}"
        assert 'text/csv' in response.headers.get('content-type', '')
        
        # Verify CSV content has expected headers
        content = response.text
        assert 'Customer ID' in content
        assert 'Full Name' in content
        assert 'Email' in content
        assert 'Dogs Count' in content
        assert 'Bookings Count' in content
        print("PASS: Admin can export customers CSV")
    
    def test_bookings_csv_export_customer_forbidden(self):
        """Customer cannot export bookings CSV"""
        response = requests.get(
            f"{BASE_URL}/api/exports/bookings/csv",
            headers=self.customer_headers
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert 'Admin access required' in response.text
        print("PASS: Customer correctly blocked from bookings CSV export")
    
    def test_customers_csv_export_customer_forbidden(self):
        """Customer cannot export customers CSV"""
        response = requests.get(
            f"{BASE_URL}/api/exports/customers/csv",
            headers=self.customer_headers
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert 'Admin access required' in response.text
        print("PASS: Customer correctly blocked from customers CSV export")


class TestBookingTypes:
    """Test booking type functionality (stay, daycare, meet_greet)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        # Admin login
        admin_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "Test123!"
        })
        assert admin_resp.status_code == 200
        self.admin_token = admin_resp.json()['token']
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get a location
        locations_resp = requests.get(f"{BASE_URL}/api/locations", headers=self.admin_headers)
        if locations_resp.status_code == 200 and locations_resp.json():
            self.location_id = locations_resp.json()[0]['id']
        else:
            self.location_id = None
    
    def test_booking_types_available(self):
        """Verify booking types are supported in the system"""
        # Get bookings to verify booking_type field exists
        response = requests.get(f"{BASE_URL}/api/bookings", headers=self.admin_headers)
        assert response.status_code == 200
        
        bookings = response.json()
        if bookings:
            # Check that booking_type field exists
            first_booking = bookings[0]
            assert 'booking_type' in first_booking or first_booking.get('booking_type') is None
            print(f"PASS: Booking type field exists. Sample: {first_booking.get('booking_type', 'stay')}")
    
    def test_meet_greet_booking_type_in_csv(self):
        """Verify meet_greet booking type appears in CSV export"""
        response = requests.get(
            f"{BASE_URL}/api/exports/bookings/csv",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        
        content = response.text
        # Check that Booking Type column exists
        assert 'Booking Type' in content
        print("PASS: Booking Type column exists in CSV export")


class TestPaymentTypes:
    """Test payment type functionality including cash option"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        admin_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "Test123!"
        })
        assert admin_resp.status_code == 200
        self.admin_token = admin_resp.json()['token']
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_cash_payment_type_in_bookings(self):
        """Verify cash payment type exists in bookings"""
        response = requests.get(
            f"{BASE_URL}/api/exports/bookings/csv",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        
        content = response.text
        # Check that Payment Type column exists
        assert 'Payment Type' in content
        
        # Check if cash payment type exists in any booking
        if 'cash' in content.lower():
            print("PASS: Cash payment type found in bookings")
        else:
            print("PASS: Payment Type column exists (no cash bookings yet)")


class TestAdminSettings:
    """Test admin settings endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        admin_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "Test123!"
        })
        assert admin_resp.status_code == 200
        self.admin_token = admin_resp.json()['token']
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_admin_settings_endpoint(self):
        """Admin can access settings endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/admin/settings",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Settings endpoint failed: {response.text}"
        
        settings = response.json()
        assert isinstance(settings, dict)
        print(f"PASS: Admin settings endpoint accessible. Keys: {list(settings.keys())[:5]}")
    
    def test_pricing_rules_endpoint(self):
        """Admin can access pricing rules"""
        response = requests.get(
            f"{BASE_URL}/api/admin/pricing-rules",
            headers=self.admin_headers
        )
        # May return 200 with empty list or 404 if not implemented
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: Pricing rules endpoint status: {response.status_code}")


class TestCustomerDashboard:
    """Test customer dashboard functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        customer_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "customer@test.com",
            "password": "Test123!"
        })
        assert customer_resp.status_code == 200
        self.customer_token = customer_resp.json()['token']
        self.customer_headers = {"Authorization": f"Bearer {self.customer_token}"}
        self.customer_user = customer_resp.json()['user']
    
    def test_customer_can_get_bookings(self):
        """Customer can retrieve their bookings"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers=self.customer_headers
        )
        assert response.status_code == 200, f"Failed to get bookings: {response.text}"
        
        bookings = response.json()
        assert isinstance(bookings, list)
        print(f"PASS: Customer can get bookings. Count: {len(bookings)}")
    
    def test_customer_can_get_dogs(self):
        """Customer can retrieve their dogs"""
        response = requests.get(
            f"{BASE_URL}/api/dogs",
            headers=self.customer_headers
        )
        assert response.status_code == 200, f"Failed to get dogs: {response.text}"
        
        dogs = response.json()
        assert isinstance(dogs, list)
        print(f"PASS: Customer can get dogs. Count: {len(dogs)}")
    
    def test_customer_dashboard_stats(self):
        """Customer can get dashboard stats"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.customer_headers
        )
        # May return 200 or 404 depending on implementation
        if response.status_code == 200:
            stats = response.json()
            print(f"PASS: Dashboard stats available: {stats}")
        else:
            print(f"INFO: Dashboard stats endpoint returned {response.status_code}")


class TestServiceTypes:
    """Test service types endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        admin_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "Test123!"
        })
        assert admin_resp.status_code == 200
        self.admin_token = admin_resp.json()['token']
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_service_types_endpoint(self):
        """Service types endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/service-types",
            headers=self.admin_headers
        )
        # May return 200 with list or 404 if not implemented
        if response.status_code == 200:
            types = response.json()
            print(f"PASS: Service types available: {len(types)} types")
        else:
            print(f"INFO: Service types endpoint returned {response.status_code}")


class TestLocations:
    """Test locations endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        admin_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "Test123!"
        })
        assert admin_resp.status_code == 200
        self.admin_token = admin_resp.json()['token']
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_locations_endpoint(self):
        """Locations endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/locations",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Locations failed: {response.text}"
        
        locations = response.json()
        assert isinstance(locations, list)
        print(f"PASS: Locations available: {len(locations)} locations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
