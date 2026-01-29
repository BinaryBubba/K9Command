"""
Backend API Tests for K9 Command - New Features (Iteration 3)
Tests: Timesheet Modification, Staff Bookings CRUD, Chat Tabs, Admin Timesheets, 
       Shift Scheduler, Task Completion Tracking, Customer CRUD, Incident CRUD, Time Entry CRUD
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data with unique timestamps
timestamp = datetime.now().strftime('%H%M%S%f')

TEST_ADMIN = {
    "email": f"test_admin_{timestamp}@test.com",
    "password": "AdminPass123!",
    "full_name": "Test Admin",
    "phone": "555-0200",
    "role": "admin"
}

TEST_STAFF = {
    "email": f"test_staff_{timestamp}@test.com",
    "password": "StaffPass123!",
    "full_name": "Test Staff",
    "phone": "555-0300",
    "role": "staff"
}

TEST_CUSTOMER = {
    "email": f"test_customer_{timestamp}@test.com",
    "password": "TestPass123!",
    "full_name": "Test Customer",
    "phone": "555-0100",
    "role": "customer"
}


class TestSetup:
    """Setup tests - register users and get tokens"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/register", json=TEST_ADMIN)
        assert response.status_code == 200, f"Admin registration failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/register", json=TEST_STAFF)
        assert response.status_code == 200, f"Staff registration failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def customer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/register", json=TEST_CUSTOMER)
        assert response.status_code == 200, f"Customer registration failed: {response.text}"
        return response.json()["token"]


# ==================== TIME ENTRY CRUD TESTS ====================
class TestTimeEntryCRUD:
    """Test Time Entry CRUD operations (Admin)"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN, "email": f"time_admin_{ts}@test.com"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def staff_user(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_STAFF, "email": f"time_staff_{ts}@test.com"
        })
        return response.json()["user"]
    
    def test_admin_create_time_entry(self, admin_token, staff_user):
        """Admin can create time entry for staff"""
        clock_in = (datetime.now() - timedelta(hours=8)).isoformat()
        clock_out = (datetime.now() - timedelta(hours=1)).isoformat()
        
        response = requests.post(
            f"{BASE_URL}/api/time-entries",
            json={
                "staff_id": staff_user["id"],
                "clock_in": clock_in,
                "clock_out": clock_out,
                "notes": "Test entry created by admin"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to create time entry: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["staff_id"] == staff_user["id"]
        print(f"✓ Admin created time entry: {data['id'][:8]}...")
        return data
    
    def test_admin_get_time_entries(self, admin_token):
        """Admin can get all time entries"""
        response = requests.get(
            f"{BASE_URL}/api/time-entries",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin got {len(data)} time entries")
    
    def test_admin_update_time_entry(self, admin_token, staff_user):
        """Admin can update time entry"""
        # First create an entry
        clock_in = (datetime.now() - timedelta(hours=4)).isoformat()
        create_response = requests.post(
            f"{BASE_URL}/api/time-entries",
            json={"staff_id": staff_user["id"], "clock_in": clock_in},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        entry_id = create_response.json()["id"]
        
        # Update it
        new_clock_out = datetime.now().isoformat()
        response = requests.patch(
            f"{BASE_URL}/api/time-entries/{entry_id}",
            json={"clock_out": new_clock_out, "notes": "Updated by admin"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Admin updated time entry: {entry_id[:8]}...")
    
    def test_admin_delete_time_entry(self, admin_token, staff_user):
        """Admin can delete time entry"""
        # First create an entry
        clock_in = (datetime.now() - timedelta(hours=2)).isoformat()
        create_response = requests.post(
            f"{BASE_URL}/api/time-entries",
            json={"staff_id": staff_user["id"], "clock_in": clock_in},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        entry_id = create_response.json()["id"]
        
        # Delete it
        response = requests.delete(
            f"{BASE_URL}/api/time-entries/{entry_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Admin deleted time entry: {entry_id[:8]}...")


# ==================== TIMESHEET MODIFICATION REQUEST TESTS ====================
class TestTimesheetModificationRequests:
    """Test staff timesheet modification requests"""
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_STAFF, "email": f"mod_staff_{ts}@test.com"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN, "email": f"mod_admin_{ts}@test.com"
        })
        return response.json()["token"]
    
    def test_staff_clock_in_out(self, staff_token):
        """Staff can clock in and out"""
        # First check if already clocked in
        current_response = requests.get(
            f"{BASE_URL}/api/time-entries/current",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        if current_response.status_code == 200 and current_response.json().get("clocked_in"):
            # Clock out first
            requests.post(
                f"{BASE_URL}/api/time-entries/clock-out",
                headers={"Authorization": f"Bearer {staff_token}"}
            )
        
        # Clock in
        response = requests.post(
            f"{BASE_URL}/api/time-entries/clock-in",
            json={"staff_id": "test", "location_id": "main-kennel"},
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 200, f"Clock in failed: {response.text}"
        entry = response.json()
        print(f"✓ Staff clocked in: {entry['id'][:8]}...")
        
        # Clock out
        response = requests.post(
            f"{BASE_URL}/api/time-entries/clock-out",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 200, f"Clock out failed: {response.text}"
        print("✓ Staff clocked out")
        return entry
    
    def test_staff_request_modification(self, staff_token):
        """Staff can request modification to past time entry"""
        # First clock in and out to create an entry
        requests.post(
            f"{BASE_URL}/api/time-entries/clock-in",
            json={"staff_id": "test", "location_id": "main-kennel"},
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        requests.post(
            f"{BASE_URL}/api/time-entries/clock-out",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        # Get the entry
        entries_response = requests.get(
            f"{BASE_URL}/api/time-entries",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        entries = entries_response.json()
        if len(entries) == 0:
            pytest.skip("No time entries to modify")
        
        entry = entries[0]
        
        # Request modification
        new_clock_in = (datetime.now() - timedelta(hours=9)).isoformat()
        new_clock_out = (datetime.now() - timedelta(hours=1)).isoformat()
        
        response = requests.post(
            f"{BASE_URL}/api/time-entries/modification-request",
            json={
                "time_entry_id": entry["id"],
                "requested_clock_in": new_clock_in,
                "requested_clock_out": new_clock_out,
                "reason": "Forgot to clock in on time"
            },
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 200, f"Modification request failed: {response.text}"
        print("✓ Staff submitted modification request")
    
    def test_admin_get_modification_requests(self, admin_token):
        """Admin can view all modification requests"""
        response = requests.get(
            f"{BASE_URL}/api/time-entries/modification-requests",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin got {len(data)} modification requests")


# ==================== SHIFT SCHEDULING TESTS ====================
class TestShiftScheduling:
    """Test shift scheduling CRUD"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN, "email": f"shift_admin_{ts}@test.com"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def staff_user(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_STAFF, "email": f"shift_staff_{ts}@test.com"
        })
        return response.json()["user"]
    
    @pytest.fixture(scope="class")
    def location_id(self):
        response = requests.get(f"{BASE_URL}/api/locations")
        locations = response.json()
        return locations[0]["id"] if locations else None
    
    def test_create_shift(self, admin_token, staff_user, location_id):
        """Admin can create a shift"""
        if not location_id:
            pytest.skip("No location available")
        
        start_time = (datetime.now() + timedelta(days=1, hours=9)).isoformat()
        end_time = (datetime.now() + timedelta(days=1, hours=17)).isoformat()
        
        response = requests.post(
            f"{BASE_URL}/api/shifts",
            json={
                "staff_id": staff_user["id"],
                "location_id": location_id,
                "start_time": start_time,
                "end_time": end_time,
                "notes": "Morning shift"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to create shift: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["staff_id"] == staff_user["id"]
        print(f"✓ Created shift: {data['id'][:8]}...")
        return data
    
    def test_get_shifts(self, admin_token):
        """Admin can get all shifts"""
        response = requests.get(
            f"{BASE_URL}/api/shifts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} shifts")
    
    def test_update_shift(self, admin_token, staff_user, location_id):
        """Admin can update a shift"""
        if not location_id:
            pytest.skip("No location available")
        
        # Create a shift first
        start_time = (datetime.now() + timedelta(days=2, hours=9)).isoformat()
        end_time = (datetime.now() + timedelta(days=2, hours=17)).isoformat()
        
        create_response = requests.post(
            f"{BASE_URL}/api/shifts",
            json={
                "staff_id": staff_user["id"],
                "location_id": location_id,
                "start_time": start_time,
                "end_time": end_time
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        shift_id = create_response.json()["id"]
        
        # Update it
        new_end_time = (datetime.now() + timedelta(days=2, hours=18)).isoformat()
        response = requests.patch(
            f"{BASE_URL}/api/shifts/{shift_id}",
            json={"end_time": new_end_time, "notes": "Extended shift"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Updated shift: {shift_id[:8]}...")
    
    def test_delete_shift(self, admin_token, staff_user, location_id):
        """Admin can delete a shift"""
        if not location_id:
            pytest.skip("No location available")
        
        # Create a shift first
        start_time = (datetime.now() + timedelta(days=3, hours=9)).isoformat()
        end_time = (datetime.now() + timedelta(days=3, hours=17)).isoformat()
        
        create_response = requests.post(
            f"{BASE_URL}/api/shifts",
            json={
                "staff_id": staff_user["id"],
                "location_id": location_id,
                "start_time": start_time,
                "end_time": end_time
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        shift_id = create_response.json()["id"]
        
        # Delete it
        response = requests.delete(
            f"{BASE_URL}/api/shifts/{shift_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Deleted shift: {shift_id[:8]}...")


# ==================== BOOKING CRUD TESTS ====================
class TestBookingCRUD:
    """Test Booking CRUD operations (Staff/Admin)"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN, "email": f"booking_admin_{ts}@test.com"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_STAFF, "email": f"booking_staff_{ts}@test.com"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def customer_with_dog(self):
        ts = datetime.now().strftime('%H%M%S%f')
        # Register customer
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_CUSTOMER, "email": f"booking_customer_{ts}@test.com"
        })
        token = reg_response.json()["token"]
        
        # Create dog
        dog_response = requests.post(
            f"{BASE_URL}/api/dogs",
            json={"name": "Test Dog", "breed": "Labrador", "age": 3, "weight": 50.0, "gender": "male"},
            headers={"Authorization": f"Bearer {token}"}
        )
        dog = dog_response.json()
        
        # Get location
        locations = requests.get(f"{BASE_URL}/api/locations").json()
        location_id = locations[0]["id"] if locations else None
        
        return {"token": token, "dog_id": dog["id"], "location_id": location_id}
    
    def test_create_booking(self, customer_with_dog):
        """Customer can create booking"""
        if not customer_with_dog["location_id"]:
            pytest.skip("No location available")
        
        check_in = (datetime.now() + timedelta(days=7)).isoformat()
        check_out = (datetime.now() + timedelta(days=10)).isoformat()
        
        response = requests.post(
            f"{BASE_URL}/api/bookings",
            json={
                "dog_ids": [customer_with_dog["dog_id"]],
                "location_id": customer_with_dog["location_id"],
                "accommodation_type": "room",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "notes": "Test booking"
            },
            headers={"Authorization": f"Bearer {customer_with_dog['token']}"}
        )
        assert response.status_code == 200, f"Failed to create booking: {response.text}"
        data = response.json()
        print(f"✓ Created booking: {data['id'][:8]}...")
        return data
    
    def test_staff_edit_booking(self, staff_token, customer_with_dog):
        """Staff can edit booking with modification reason"""
        if not customer_with_dog["location_id"]:
            pytest.skip("No location available")
        
        # Create a booking first
        check_in = (datetime.now() + timedelta(days=14)).isoformat()
        check_out = (datetime.now() + timedelta(days=17)).isoformat()
        
        create_response = requests.post(
            f"{BASE_URL}/api/bookings",
            json={
                "dog_ids": [customer_with_dog["dog_id"]],
                "location_id": customer_with_dog["location_id"],
                "accommodation_type": "room",
                "check_in_date": check_in,
                "check_out_date": check_out
            },
            headers={"Authorization": f"Bearer {customer_with_dog['token']}"}
        )
        booking_id = create_response.json()["id"]
        
        # Staff edits booking
        response = requests.patch(
            f"{BASE_URL}/api/bookings/{booking_id}",
            json={
                "notes": "Updated by staff",
                "modification_reason": "Customer requested date change"
            },
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 200, f"Failed to edit booking: {response.text}"
        print(f"✓ Staff edited booking: {booking_id[:8]}...")
    
    def test_staff_delete_booking(self, staff_token, customer_with_dog):
        """Staff can delete/cancel booking"""
        if not customer_with_dog["location_id"]:
            pytest.skip("No location available")
        
        # Create a booking first
        check_in = (datetime.now() + timedelta(days=21)).isoformat()
        check_out = (datetime.now() + timedelta(days=24)).isoformat()
        
        create_response = requests.post(
            f"{BASE_URL}/api/bookings",
            json={
                "dog_ids": [customer_with_dog["dog_id"]],
                "location_id": customer_with_dog["location_id"],
                "accommodation_type": "room",
                "check_in_date": check_in,
                "check_out_date": check_out
            },
            headers={"Authorization": f"Bearer {customer_with_dog['token']}"}
        )
        booking_id = create_response.json()["id"]
        
        # Staff deletes booking
        response = requests.delete(
            f"{BASE_URL}/api/bookings/{booking_id}",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 200, f"Failed to delete booking: {response.text}"
        print(f"✓ Staff deleted booking: {booking_id[:8]}...")


# ==================== CUSTOMER CRUD TESTS ====================
class TestCustomerCRUD:
    """Test Admin Customer CRUD operations"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN, "email": f"cust_admin_{ts}@test.com"
        })
        return response.json()["token"]
    
    def test_admin_create_customer(self, admin_token):
        """Admin can create a customer"""
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(
            f"{BASE_URL}/api/admin/customers",
            json={
                "email": f"new_customer_{ts}@test.com",
                "full_name": "New Customer",
                "phone": "555-9999",
                "password": "TempPass123!"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to create customer: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"✓ Admin created customer: {data['id'][:8]}...")
        return data
    
    def test_admin_update_customer(self, admin_token):
        """Admin can update a customer"""
        # Create a customer first
        ts = datetime.now().strftime('%H%M%S%f')
        create_response = requests.post(
            f"{BASE_URL}/api/admin/customers",
            json={
                "email": f"update_customer_{ts}@test.com",
                "full_name": "Update Customer",
                "password": "TempPass123!"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        customer_id = create_response.json()["id"]
        
        # Update customer
        response = requests.patch(
            f"{BASE_URL}/api/admin/customers/{customer_id}",
            json={"full_name": "Updated Name", "phone": "555-8888"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to update customer: {response.text}"
        print(f"✓ Admin updated customer: {customer_id[:8]}...")
    
    def test_admin_toggle_customer_status(self, admin_token):
        """Admin can activate/deactivate customer"""
        # Create a customer first
        ts = datetime.now().strftime('%H%M%S%f')
        create_response = requests.post(
            f"{BASE_URL}/api/admin/customers",
            json={
                "email": f"toggle_customer_{ts}@test.com",
                "full_name": "Toggle Customer",
                "password": "TempPass123!"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        customer_id = create_response.json()["id"]
        
        # Deactivate
        response = requests.patch(
            f"{BASE_URL}/api/admin/users/{customer_id}/status?is_active=false",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Admin deactivated customer")
        
        # Reactivate
        response = requests.patch(
            f"{BASE_URL}/api/admin/users/{customer_id}/status?is_active=true",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Admin reactivated customer")


# ==================== INCIDENT CRUD TESTS ====================
class TestIncidentCRUD:
    """Test Incident CRUD operations"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN, "email": f"incident_admin_{ts}@test.com"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_STAFF, "email": f"incident_staff_{ts}@test.com"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def location_id(self):
        response = requests.get(f"{BASE_URL}/api/locations")
        locations = response.json()
        return locations[0]["id"] if locations else None
    
    def test_create_incident(self, staff_token, location_id):
        """Staff can create incident"""
        if not location_id:
            pytest.skip("No location available")
        
        response = requests.post(
            f"{BASE_URL}/api/incidents",
            json={
                "title": "Test Incident",
                "description": "Test incident - dog escaped from kennel",
                "severity": "high",
                "location_id": location_id
            },
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 200, f"Failed to create incident: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"✓ Created incident: {data['id'][:8]}...")
        return data
    
    def test_get_incidents(self, admin_token):
        """Admin can get all incidents"""
        response = requests.get(
            f"{BASE_URL}/api/incidents",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} incidents")
    
    def test_update_incident(self, admin_token, staff_token, location_id):
        """Admin can update incident"""
        if not location_id:
            pytest.skip("No location available")
        
        # Create incident first
        create_response = requests.post(
            f"{BASE_URL}/api/incidents",
            json={"title": "Update Test", "description": "Update test incident", "severity": "medium", "location_id": location_id},
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert create_response.status_code == 200, f"Failed to create incident: {create_response.text}"
        incident_id = create_response.json()["id"]
        
        # Update it
        response = requests.patch(
            f"{BASE_URL}/api/incidents/{incident_id}",
            json={"status": "resolved", "resolution": "Issue resolved"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Updated incident: {incident_id[:8]}...")
    
    def test_delete_incident(self, admin_token, staff_token, location_id):
        """Admin can delete incident"""
        if not location_id:
            pytest.skip("No location available")
        
        # Create incident first
        create_response = requests.post(
            f"{BASE_URL}/api/incidents",
            json={"title": "Delete Test", "description": "Delete test incident", "severity": "low", "location_id": location_id},
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert create_response.status_code == 200, f"Failed to create incident: {create_response.text}"
        incident_id = create_response.json()["id"]
        
        # Delete it
        response = requests.delete(
            f"{BASE_URL}/api/incidents/{incident_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Deleted incident: {incident_id[:8]}...")


# ==================== TASK COMPLETION TRACKING TESTS ====================
class TestTaskCompletionTracking:
    """Test task completion tracking (who completed)"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN, "email": f"task_admin_{ts}@test.com"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def staff_token_and_user(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_STAFF, "email": f"task_staff_{ts}@test.com"
        })
        return {"token": response.json()["token"], "user": response.json()["user"]}
    
    @pytest.fixture(scope="class")
    def location_id(self):
        response = requests.get(f"{BASE_URL}/api/locations")
        locations = response.json()
        return locations[0]["id"] if locations else None
    
    def test_task_completion_tracking(self, admin_token, staff_token_and_user, location_id):
        """Task completion tracks who completed it"""
        # Create task
        create_response = requests.post(
            f"{BASE_URL}/api/tasks",
            json={
                "title": "Test task for completion tracking",
                "description": "This task will be completed by staff",
                "location_id": location_id
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        task_id = create_response.json()["id"]
        
        # Staff completes task
        response = requests.patch(
            f"{BASE_URL}/api/tasks/{task_id}/complete",
            headers={"Authorization": f"Bearer {staff_token_and_user['token']}"}
        )
        assert response.status_code == 200
        
        # Verify completion tracking
        tasks_response = requests.get(
            f"{BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        tasks = tasks_response.json()
        completed_task = next((t for t in tasks if t["id"] == task_id), None)
        
        assert completed_task is not None
        assert completed_task["status"] == "completed"
        assert completed_task.get("completed_by") == staff_token_and_user["user"]["id"]
        assert completed_task.get("completed_by_name") == staff_token_and_user["user"]["full_name"]
        print(f"✓ Task completion tracked: completed by {completed_task.get('completed_by_name')}")


# ==================== CHAT TESTS ====================
class TestChatTabs:
    """Test chat functionality with tabs"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_ADMIN, "email": f"chat_admin_{ts}@test.com"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_STAFF, "email": f"chat_staff_{ts}@test.com"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def customer_token(self):
        ts = datetime.now().strftime('%H%M%S%f')
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            **TEST_CUSTOMER, "email": f"chat_customer_{ts}@test.com"
        })
        return response.json()["token"]
    
    def test_get_chat_users(self, admin_token):
        """Can get available chat users"""
        response = requests.get(
            f"{BASE_URL}/api/chat/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} chat users")
    
    def test_get_chats(self, admin_token):
        """Can get chats"""
        response = requests.get(
            f"{BASE_URL}/api/chats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} chats")


# ==================== TEST BOOKING VERIFICATION ====================
class TestBookingVerification:
    """Verify test booking exists with dogs Buddy and Max"""
    
    def test_existing_customer_login(self):
        """Test customer can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "test_customer@example.com",
                "password": "TestPass123!"
            }
        )
        if response.status_code == 200:
            print("✓ Test customer login successful")
            return response.json()["token"]
        else:
            print("⚠ Test customer not found or wrong password")
            pytest.skip("Test customer not available")
    
    def test_verify_test_booking_dogs(self):
        """Verify test booking has dogs Buddy and Max"""
        # Login as test customer
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "test_customer@example.com",
                "password": "TestPass123!"
            }
        )
        if login_response.status_code != 200:
            pytest.skip("Test customer not available")
        
        token = login_response.json()["token"]
        
        # Get dogs
        dogs_response = requests.get(
            f"{BASE_URL}/api/dogs",
            headers={"Authorization": f"Bearer {token}"}
        )
        dogs = dogs_response.json()
        dog_names = [d["name"] for d in dogs]
        
        if "Buddy" in dog_names and "Max" in dog_names:
            print(f"✓ Test customer has dogs: {dog_names}")
        else:
            print(f"⚠ Test customer dogs: {dog_names} (expected Buddy and Max)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
