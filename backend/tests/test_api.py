"""
Backend API Tests for K9 Command Kennel Operations Platform
Tests: Auth, Bookings, Tasks, Admin User Management
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
TEST_CUSTOMER = {
    "email": f"test_customer_{datetime.now().strftime('%H%M%S')}@test.com",
    "password": "TestPass123!",
    "full_name": "Test Customer",
    "phone": "555-0100",
    "role": "customer"
}

TEST_ADMIN = {
    "email": f"test_admin_{datetime.now().strftime('%H%M%S')}@test.com",
    "password": "AdminPass123!",
    "full_name": "Test Admin",
    "phone": "555-0200",
    "role": "admin"
}

TEST_STAFF = {
    "email": f"test_staff_{datetime.now().strftime('%H%M%S')}@test.com",
    "password": "StaffPass123!",
    "full_name": "Test Staff",
    "phone": "555-0300",
    "role": "staff"
}


class TestHealthAndAuth:
    """Test authentication endpoints"""
    
    def test_register_customer(self):
        """Register a new customer"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json=TEST_CUSTOMER)
        assert response.status_code == 200, f"Failed to register customer: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_CUSTOMER["email"]
        assert data["user"]["role"] == "customer"
        print(f"✓ Customer registered: {TEST_CUSTOMER['email']}")
        return data["token"]
    
    def test_register_admin(self):
        """Register a new admin"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json=TEST_ADMIN)
        assert response.status_code == 200, f"Failed to register admin: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin registered: {TEST_ADMIN['email']}")
        return data["token"]
    
    def test_register_staff(self):
        """Register a new staff"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json=TEST_STAFF)
        assert response.status_code == 200, f"Failed to register staff: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "staff"
        print(f"✓ Staff registered: {TEST_STAFF['email']}")
        return data["token"]
    
    def test_login_customer(self):
        """Login with customer credentials"""
        # First register
        requests.post(f"{BASE_URL}/api/auth/register", json=TEST_CUSTOMER)
        
        # Then login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CUSTOMER["email"],
            "password": TEST_CUSTOMER["password"]
        })
        assert response.status_code == 200, f"Failed to login: {response.text}"
        data = response.json()
        assert "token" in data
        print("✓ Customer login successful")
        return data["token"]
    
    def test_get_me(self):
        """Test /auth/me endpoint"""
        # Register and get token
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_CUSTOMER,
            "email": f"me_test_{datetime.now().strftime('%H%M%S%f')}@test.com"
        })
        token = reg_response.json()["token"]
        
        # Get current user
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        print("✓ Get current user successful")


class TestLocations:
    """Test location endpoints"""
    
    def test_get_locations(self):
        """Get all locations"""
        response = requests.get(f"{BASE_URL}/api/locations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} locations")
        return data
    
    def test_check_availability(self):
        """Check location availability"""
        # First get locations
        locations = requests.get(f"{BASE_URL}/api/locations").json()
        
        if len(locations) > 0:
            location_id = locations[0]["id"]
            check_in = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            check_out = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
            
            response = requests.get(
                f"{BASE_URL}/api/locations/{location_id}/availability",
                params={"check_in": check_in, "check_out": check_out}
            )
            assert response.status_code == 200
            data = response.json()
            assert "rooms_available" in data
            assert "crates_available" in data
            assert "total_rooms" in data
            assert "total_crates" in data
            print(f"✓ Availability check: {data['rooms_available']} rooms, {data['crates_available']} crates available")
        else:
            pytest.skip("No locations available for testing")


class TestDogs:
    """Test dog management endpoints"""
    
    @pytest.fixture
    def customer_token(self):
        """Get customer token"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_CUSTOMER,
            "email": f"dog_test_{datetime.now().strftime('%H%M%S%f')}@test.com"
        })
        return response.json()["token"]
    
    def test_create_dog(self, customer_token):
        """Create a new dog"""
        dog_data = {
            "name": "Test Buddy",
            "breed": "Golden Retriever",
            "age": 3,
            "weight": 65.0,
            "gender": "male",
            "spayed_neutered": True,
            "friendly_with_dogs": True,
            "friendly_with_people": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/dogs",
            json=dog_data,
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert response.status_code == 200, f"Failed to create dog: {response.text}"
        data = response.json()
        assert data["name"] == "Test Buddy"
        assert data["breed"] == "Golden Retriever"
        print(f"✓ Dog created: {data['name']}")
        return data
    
    def test_get_dogs(self, customer_token):
        """Get all dogs for customer"""
        response = requests.get(
            f"{BASE_URL}/api/dogs",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} dogs")


class TestBookings:
    """Test booking endpoints - P0 Bug Fix verification"""
    
    @pytest.fixture
    def customer_with_dog(self):
        """Create customer with a dog"""
        # Register customer
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_CUSTOMER,
            "email": f"booking_test_{datetime.now().strftime('%H%M%S%f')}@test.com"
        })
        token = reg_response.json()["token"]
        
        # Create dog
        dog_response = requests.post(
            f"{BASE_URL}/api/dogs",
            json={
                "name": "Booking Test Dog",
                "breed": "Labrador",
                "age": 2,
                "weight": 55.0,
                "gender": "female",
                "spayed_neutered": True
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        dog = dog_response.json()
        
        # Get location
        locations = requests.get(f"{BASE_URL}/api/locations").json()
        location_id = locations[0]["id"] if locations else None
        
        return {"token": token, "dog_id": dog["id"], "location_id": location_id}
    
    def test_create_booking(self, customer_with_dog):
        """Create a new booking"""
        if not customer_with_dog["location_id"]:
            pytest.skip("No location available")
        
        check_in = (datetime.now() + timedelta(days=14)).isoformat()
        check_out = (datetime.now() + timedelta(days=17)).isoformat()
        
        booking_data = {
            "dog_ids": [customer_with_dog["dog_id"]],
            "location_id": customer_with_dog["location_id"],
            "accommodation_type": "room",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "notes": "Test booking",
            "needs_separate_playtime": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            json=booking_data,
            headers={"Authorization": f"Bearer {customer_with_dog['token']}"}
        )
        assert response.status_code == 200, f"Failed to create booking: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["total_price"] > 0
        print(f"✓ Booking created: {data['id'][:8]}... Total: ${data['total_price']}")
        return data
    
    def test_booking_with_separate_playtime_pricing(self, customer_with_dog):
        """Verify separate playtime fee is $6/day (not $25)"""
        if not customer_with_dog["location_id"]:
            pytest.skip("No location available")
        
        check_in = (datetime.now() + timedelta(days=21)).isoformat()
        check_out = (datetime.now() + timedelta(days=24)).isoformat()  # 3 nights
        
        # Booking WITHOUT separate playtime
        booking_without = {
            "dog_ids": [customer_with_dog["dog_id"]],
            "location_id": customer_with_dog["location_id"],
            "accommodation_type": "room",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "notes": "Without playtime",
            "needs_separate_playtime": False
        }
        
        response1 = requests.post(
            f"{BASE_URL}/api/bookings",
            json=booking_without,
            headers={"Authorization": f"Bearer {customer_with_dog['token']}"}
        )
        price_without = response1.json()["total_price"]
        
        # Booking WITH separate playtime
        check_in2 = (datetime.now() + timedelta(days=28)).isoformat()
        check_out2 = (datetime.now() + timedelta(days=31)).isoformat()  # 3 nights
        
        booking_with = {
            "dog_ids": [customer_with_dog["dog_id"]],
            "location_id": customer_with_dog["location_id"],
            "accommodation_type": "room",
            "check_in_date": check_in2,
            "check_out_date": check_out2,
            "notes": "With playtime",
            "needs_separate_playtime": True
        }
        
        response2 = requests.post(
            f"{BASE_URL}/api/bookings",
            json=booking_with,
            headers={"Authorization": f"Bearer {customer_with_dog['token']}"}
        )
        price_with = response2.json()["total_price"]
        separate_fee = response2.json().get("separate_playtime_fee", 0)
        
        # Verify the fee is $6/day * 3 nights = $18
        expected_fee = 6 * 3  # $6/day * 3 nights
        price_diff = price_with - price_without
        
        print(f"✓ Price without playtime: ${price_without}")
        print(f"✓ Price with playtime: ${price_with}")
        print(f"✓ Separate playtime fee: ${separate_fee}")
        print(f"✓ Price difference: ${price_diff}")
        
        assert separate_fee == expected_fee, f"Expected $18 fee, got ${separate_fee}"
        print(f"✓ VERIFIED: Separate playtime fee is $6/day (${expected_fee} for 3 nights)")
    
    def test_get_bookings(self, customer_with_dog):
        """Get all bookings"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers={"Authorization": f"Bearer {customer_with_dog['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} bookings")


class TestAdminBookings:
    """Test admin booking management"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN,
            "email": f"admin_booking_{datetime.now().strftime('%H%M%S%f')}@test.com"
        })
        return response.json()["token"]
    
    def test_admin_get_all_bookings(self, admin_token):
        """Admin can get all bookings"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin got {len(data)} bookings")
        return data
    
    def test_admin_update_booking_status(self, admin_token):
        """Admin can update booking status"""
        # First get bookings
        bookings = requests.get(
            f"{BASE_URL}/api/bookings",
            headers={"Authorization": f"Bearer {admin_token}"}
        ).json()
        
        if len(bookings) > 0:
            booking_id = bookings[0]["id"]
            
            # Update status to confirmed
            response = requests.patch(
                f"{BASE_URL}/api/bookings/{booking_id}/status?status=confirmed",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
            print(f"✓ Admin updated booking status to confirmed")
        else:
            pytest.skip("No bookings to update")


class TestTasks:
    """Test task management - Admin CRUD"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN,
            "email": f"task_admin_{datetime.now().strftime('%H%M%S%f')}@test.com"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_token(self):
        """Get staff token"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_STAFF,
            "email": f"task_staff_{datetime.now().strftime('%H%M%S%f')}@test.com"
        })
        return response.json()["token"]
    
    def test_create_task(self, admin_token):
        """Create a new task"""
        # Get location first
        locations = requests.get(f"{BASE_URL}/api/locations").json()
        location_id = locations[0]["id"] if locations else None
        
        task_data = {
            "title": "Test Task - Clean kennels",
            "description": "Daily cleaning task",
            "location_id": location_id,
            "due_date": (datetime.now() + timedelta(days=1)).isoformat()
        }
        
        response = requests.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to create task: {response.text}"
        data = response.json()
        assert data["title"] == "Test Task - Clean kennels"
        assert data["status"] == "pending"
        print(f"✓ Task created: {data['title']}")
        return data
    
    def test_get_tasks(self, admin_token):
        """Get all tasks"""
        response = requests.get(
            f"{BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} tasks")
        return data
    
    def test_complete_task(self, admin_token):
        """Complete a task"""
        # Create a task first
        locations = requests.get(f"{BASE_URL}/api/locations").json()
        location_id = locations[0]["id"] if locations else None
        
        task_response = requests.post(
            f"{BASE_URL}/api/tasks",
            json={
                "title": "Task to complete",
                "description": "Will be completed",
                "location_id": location_id
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        task_id = task_response.json()["id"]
        
        # Complete the task
        response = requests.patch(
            f"{BASE_URL}/api/tasks/{task_id}/complete",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Task completed: {task_id[:8]}...")
    
    def test_delete_task(self, admin_token):
        """Delete a task (admin only)"""
        # Create a task first
        locations = requests.get(f"{BASE_URL}/api/locations").json()
        location_id = locations[0]["id"] if locations else None
        
        task_response = requests.post(
            f"{BASE_URL}/api/tasks",
            json={
                "title": "Task to delete",
                "description": "Will be deleted",
                "location_id": location_id
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        task_id = task_response.json()["id"]
        
        # Delete the task
        response = requests.delete(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Task deleted: {task_id[:8]}...")
    
    def test_staff_cannot_delete_task(self, staff_token):
        """Staff cannot delete tasks"""
        # Try to delete a non-existent task (should fail with 403, not 404)
        response = requests.delete(
            f"{BASE_URL}/api/tasks/fake-task-id",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403, "Staff should not be able to delete tasks"
        print("✓ Staff correctly denied task deletion")


class TestAdminUserManagement:
    """Test admin user management endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN,
            "email": f"user_mgmt_admin_{datetime.now().strftime('%H%M%S%f')}@test.com"
        })
        return response.json()["token"]
    
    def test_get_all_users(self, admin_token):
        """Admin can get all users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin got {len(data)} users")
    
    def test_get_customers_only(self, admin_token):
        """Admin can filter users by role"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users?role=customer",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned users should be customers
        for user in data:
            assert user["role"] == "customer"
        print(f"✓ Admin got {len(data)} customers")
    
    def test_toggle_user_status(self, admin_token):
        """Admin can activate/deactivate users"""
        # Create a customer to toggle
        customer_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_CUSTOMER,
            "email": f"toggle_test_{datetime.now().strftime('%H%M%S%f')}@test.com"
        })
        customer_id = customer_response.json()["user"]["id"]
        
        # Deactivate the customer
        response = requests.patch(
            f"{BASE_URL}/api/admin/users/{customer_id}/status?is_active=false",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Customer deactivated")
        
        # Reactivate the customer
        response = requests.patch(
            f"{BASE_URL}/api/admin/users/{customer_id}/status?is_active=true",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Customer reactivated")
    
    def test_non_admin_cannot_access_user_management(self):
        """Non-admin users cannot access user management"""
        # Register a customer
        customer_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_CUSTOMER,
            "email": f"non_admin_test_{datetime.now().strftime('%H%M%S%f')}@test.com"
        })
        customer_token = customer_response.json()["token"]
        
        # Try to access admin endpoint
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert response.status_code == 403
        print("✓ Non-admin correctly denied access to user management")


class TestDashboardStats:
    """Test dashboard statistics endpoint"""
    
    def test_admin_dashboard_stats(self):
        """Admin gets comprehensive stats"""
        # Register admin
        admin_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN,
            "email": f"stats_admin_{datetime.now().strftime('%H%M%S%f')}@test.com"
        })
        admin_token = admin_response.json()["token"]
        
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_customers" in data
        assert "total_dogs" in data
        assert "total_bookings" in data
        print(f"✓ Admin stats: {data['total_customers']} customers, {data['total_dogs']} dogs, {data['total_bookings']} bookings")
    
    def test_customer_dashboard_stats(self):
        """Customer gets their own stats"""
        # Register customer
        customer_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_CUSTOMER,
            "email": f"stats_customer_{datetime.now().strftime('%H%M%S%f')}@test.com"
        })
        customer_token = customer_response.json()["token"]
        
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "my_dogs" in data
        assert "my_bookings" in data
        print(f"✓ Customer stats: {data['my_dogs']} dogs, {data['my_bookings']} bookings")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
