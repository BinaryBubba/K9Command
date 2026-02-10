"""
K9Command - Phase 2-4 Backend API Tests
Tests for Ops Dashboard, Staff Operations, Enhanced Booking, Notifications, and Automation

Test Coverage:
- Phase 2: Ops Dashboard, Approval Queue, Staff Assignments, Play Groups, Feeding Schedules
- Phase 3: Enhanced Booking v2, Booking Modification, Single Booking GET, Invoices, Payment History
- Phase 4: Notifications, Notification Templates, Automation Rules, Event Logs, Send Notification
"""
import pytest
import requests
import os
import time
from datetime import datetime, timedelta

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin_test@k9.com"
ADMIN_PASSWORD = "Test123!"
STAFF_EMAIL = "staff_test@k9.com"
STAFF_PASSWORD = "Test123!"
CUSTOMER_EMAIL = "customer_test@k9.com"
CUSTOMER_PASSWORD = "Test123!"

# Test data storage
test_data = {}


class TestSetup:
    """Setup tests - register/login users and create test data"""
    
    def test_register_admin(self):
        """Register admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "full_name": "Test Admin",
            "phone": "555-0001",
            "role": "admin"
        })
        # May already exist
        if response.status_code == 400:
            # Login instead
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
        
        assert response.status_code in [200, 201], f"Admin auth failed: {response.text}"
        data = response.json()
        test_data['admin_token'] = data['token']
        test_data['admin_id'] = data['user']['id']
        print(f"Admin authenticated: {test_data['admin_id']}")
    
    def test_register_staff(self):
        """Register staff user"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD,
            "full_name": "Test Staff",
            "phone": "555-0002",
            "role": "staff"
        })
        if response.status_code == 400:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": STAFF_EMAIL,
                "password": STAFF_PASSWORD
            })
        
        assert response.status_code in [200, 201], f"Staff auth failed: {response.text}"
        data = response.json()
        test_data['staff_token'] = data['token']
        test_data['staff_id'] = data['user']['id']
        print(f"Staff authenticated: {test_data['staff_id']}")
    
    def test_register_customer(self):
        """Register customer user"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": CUSTOMER_EMAIL,
            "password": CUSTOMER_PASSWORD,
            "full_name": "Test Customer",
            "phone": "555-0003",
            "role": "customer"
        })
        if response.status_code == 400:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": CUSTOMER_EMAIL,
                "password": CUSTOMER_PASSWORD
            })
        
        assert response.status_code in [200, 201], f"Customer auth failed: {response.text}"
        data = response.json()
        test_data['customer_token'] = data['token']
        test_data['customer_id'] = data['user']['id']
        test_data['household_id'] = data['user'].get('household_id')
        print(f"Customer authenticated: {test_data['customer_id']}")
    
    def test_create_location(self):
        """Create test location"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/locations", json={
            "name": "Test Kennel Phase2-4",
            "address": "123 Test St",
            "capacity": 20,
            "contact_email": "test@kennel.com",
            "contact_phone": "555-1234"
        }, headers=headers)
        
        if response.status_code == 200:
            test_data['location_id'] = response.json()['id']
        else:
            # Get existing location
            response = requests.get(f"{BASE_URL}/api/locations")
            locations = response.json()
            if locations:
                test_data['location_id'] = locations[0]['id']
            else:
                pytest.skip("No location available")
        print(f"Location ID: {test_data['location_id']}")
    
    def test_create_dog(self):
        """Create test dog for customer"""
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        response = requests.post(f"{BASE_URL}/api/dogs", json={
            "name": "TestDog Phase2-4",
            "breed": "Golden Retriever",
            "age": 3,
            "weight": 65.0
        }, headers=headers)
        
        if response.status_code == 200:
            test_data['dog_id'] = response.json()['id']
        else:
            # Get existing dog
            response = requests.get(f"{BASE_URL}/api/dogs", headers=headers)
            dogs = response.json()
            if dogs:
                test_data['dog_id'] = dogs[0]['id']
            else:
                pytest.skip("No dog available")
        print(f"Dog ID: {test_data['dog_id']}")


class TestPhase2OpsDashboard:
    """Phase 2 - Ops Dashboard Tests"""
    
    def test_ops_dashboard_staff_access(self):
        """GET /api/ops/dashboard - Staff can access"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/ops/dashboard", headers=headers)
        
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert 'date' in data
        assert 'dogs_on_site' in data
        assert 'arrivals' in data
        assert 'departures' in data
        assert 'capacity' in data
        
        # Verify capacity structure
        capacity = data['capacity']
        assert 'total_capacity' in capacity
        assert 'rooms_capacity' in capacity
        assert 'crates_capacity' in capacity
        assert 'total_occupied' in capacity
        assert 'arrivals_today' in capacity
        assert 'departures_today' in capacity
        print(f"Dashboard data: {data['date']}, capacity: {capacity['total_capacity']}")
    
    def test_ops_dashboard_with_date(self):
        """GET /api/ops/dashboard with date parameter"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        response = requests.get(f"{BASE_URL}/api/ops/dashboard?date={tomorrow}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['date'] == tomorrow
        print(f"Dashboard for {tomorrow}: arrivals={data['capacity']['arrivals_today']}")
    
    def test_ops_dashboard_customer_denied(self):
        """GET /api/ops/dashboard - Customer should be denied"""
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        response = requests.get(f"{BASE_URL}/api/ops/dashboard", headers=headers)
        
        assert response.status_code == 403
        print("Customer correctly denied access to ops dashboard")


class TestPhase2ApprovalQueue:
    """Phase 2 - Approval Queue Tests"""
    
    def test_approval_queue_get(self):
        """GET /api/ops/approval-queue"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/ops/approval-queue", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Approval queue items: {len(data)}")
    
    def test_booking_approve(self):
        """POST /api/ops/bookings/{id}/approve - Create and approve booking"""
        # First create a booking that requires approval
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        
        check_in = (datetime.now() + timedelta(days=10)).isoformat()
        check_out = (datetime.now() + timedelta(days=12)).isoformat()
        
        # Create booking via admin endpoint
        booking_response = requests.post(f"{BASE_URL}/api/bookings/admin", json={
            "customer_id": test_data['customer_id'],
            "dog_ids": [test_data['dog_id']],
            "location_id": test_data['location_id'],
            "accommodation_type": "room",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "notes": "Test booking for approval"
        }, headers=headers)
        
        if booking_response.status_code == 200:
            booking_id = booking_response.json()['id']
            test_data['test_booking_id'] = booking_id
            
            # Approve the booking
            approve_response = requests.post(
                f"{BASE_URL}/api/ops/bookings/{booking_id}/approve?notes=Approved%20for%20testing",
                headers=headers
            )
            
            assert approve_response.status_code == 200
            data = approve_response.json()
            assert data['status'] == 'confirmed'
            print(f"Booking {booking_id} approved successfully")
        else:
            print(f"Booking creation returned: {booking_response.status_code}")
            # Test with non-existent booking
            response = requests.post(
                f"{BASE_URL}/api/ops/bookings/nonexistent/approve",
                headers=headers
            )
            assert response.status_code == 404
            print("Approve endpoint correctly returns 404 for non-existent booking")


class TestPhase2StaffAssignments:
    """Phase 2 - Staff Assignments CRUD Tests"""
    
    def test_staff_assignments_get(self):
        """GET /api/ops/staff-assignments"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/ops/staff-assignments", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Staff assignments: {len(data)}")
    
    def test_staff_assignment_create(self):
        """POST /api/ops/staff-assignments"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        
        # Need a booking_id
        booking_id = test_data.get('test_booking_id', 'test-booking-123')
        
        response = requests.post(f"{BASE_URL}/api/ops/staff-assignments", json={
            "staff_id": test_data['staff_id'],
            "dog_id": test_data['dog_id'],
            "booking_id": booking_id,
            "assignment_date": datetime.now().isoformat(),
            "assignment_type": "primary",
            "notes": "Test assignment"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create assignment failed: {response.text}"
        data = response.json()
        assert 'id' in data
        assert data['staff_name'] == "Test Staff"
        test_data['assignment_id'] = data['id']
        print(f"Created assignment: {data['id']}")
    
    def test_staff_assignment_delete(self):
        """DELETE /api/ops/staff-assignments/{id}"""
        if 'assignment_id' not in test_data:
            pytest.skip("No assignment to delete")
        
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.delete(
            f"{BASE_URL}/api/ops/staff-assignments/{test_data['assignment_id']}",
            headers=headers
        )
        
        assert response.status_code == 200
        print(f"Deleted assignment: {test_data['assignment_id']}")


class TestPhase2PlayGroups:
    """Phase 2 - Play Groups CRUD Tests"""
    
    def test_play_groups_get(self):
        """GET /api/ops/play-groups"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/ops/play-groups", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Play groups: {len(data)}")
    
    def test_play_group_create(self):
        """POST /api/ops/play-groups"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        
        response = requests.post(f"{BASE_URL}/api/ops/play-groups", json={
            "name": "Morning Play Group",
            "dog_ids": [test_data['dog_id']],
            "location_id": test_data['location_id'],
            "scheduled_date": datetime.now().isoformat(),
            "scheduled_time": "09:00",
            "duration_minutes": 60,
            "max_dogs": 6,
            "compatibility_level": "good_with_all",
            "supervisor_id": test_data['staff_id'],
            "notes": "Test play group"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create play group failed: {response.text}"
        data = response.json()
        assert 'id' in data
        assert data['name'] == "Morning Play Group"
        test_data['play_group_id'] = data['id']
        print(f"Created play group: {data['id']}")
    
    def test_play_group_update(self):
        """PATCH /api/ops/play-groups/{id}"""
        if 'play_group_id' not in test_data:
            pytest.skip("No play group to update")
        
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.patch(
            f"{BASE_URL}/api/ops/play-groups/{test_data['play_group_id']}",
            json={"status": "completed"},
            headers=headers
        )
        
        assert response.status_code == 200
        print(f"Updated play group status to completed")
    
    def test_play_group_add_dog(self):
        """POST /api/ops/play-groups/{id}/add-dog"""
        if 'play_group_id' not in test_data:
            pytest.skip("No play group")
        
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        # This will fail if dog already in group, which is expected
        response = requests.post(
            f"{BASE_URL}/api/ops/play-groups/{test_data['play_group_id']}/add-dog?dog_id={test_data['dog_id']}",
            headers=headers
        )
        
        # Either success or dog already in group
        assert response.status_code in [200, 400]
        print(f"Add dog to play group: {response.status_code}")


class TestPhase2FeedingSchedules:
    """Phase 2 - Feeding Schedules CRUD Tests"""
    
    def test_feeding_schedules_get(self):
        """GET /api/ops/feeding-schedules"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/ops/feeding-schedules", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Feeding schedules: {len(data)}")
    
    def test_feeding_schedule_create(self):
        """POST /api/ops/feeding-schedules"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        
        booking_id = test_data.get('test_booking_id', 'test-booking-123')
        
        response = requests.post(f"{BASE_URL}/api/ops/feeding-schedules", json={
            "dog_id": test_data['dog_id'],
            "booking_id": booking_id,
            "frequency": "twice_daily",
            "feeding_times": ["08:00", "17:00"],
            "food_type": "dry",
            "portion_size": "2 cups",
            "special_instructions": "Mix with warm water",
            "treats_allowed": True,
            "notes": "Test feeding schedule"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create feeding schedule failed: {response.text}"
        data = response.json()
        assert 'id' in data
        test_data['feeding_schedule_id'] = data['id']
        print(f"Created feeding schedule: {data['id']}")
    
    def test_feeding_schedule_update(self):
        """PATCH /api/ops/feeding-schedules/{id}"""
        if 'feeding_schedule_id' not in test_data:
            pytest.skip("No feeding schedule to update")
        
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.patch(
            f"{BASE_URL}/api/ops/feeding-schedules/{test_data['feeding_schedule_id']}",
            json={"portion_size": "2.5 cups"},
            headers=headers
        )
        
        assert response.status_code == 200
        print("Updated feeding schedule portion size")
    
    def test_feeding_schedule_log_feeding(self):
        """POST /api/ops/feeding-schedules/{id}/log-feeding"""
        if 'feeding_schedule_id' not in test_data:
            pytest.skip("No feeding schedule")
        
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(
            f"{BASE_URL}/api/ops/feeding-schedules/{test_data['feeding_schedule_id']}/log-feeding",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'fed_at' in data
        print(f"Logged feeding at: {data['fed_at']}")


class TestPhase3EnhancedBooking:
    """Phase 3 - Enhanced Booking v2 Tests"""
    
    def test_booking_v2_create(self):
        """POST /api/bookings/v2 - Enhanced booking with pricing engine"""
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        
        check_in = (datetime.now() + timedelta(days=20)).isoformat()
        check_out = (datetime.now() + timedelta(days=23)).isoformat()
        
        response = requests.post(f"{BASE_URL}/api/bookings/v2", json={
            "dog_ids": [test_data['dog_id']],
            "location_id": test_data['location_id'],
            "accommodation_type": "room",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "notes": "Test booking v2",
            "needs_separate_playtime": False,
            "add_on_ids": [],
            "add_on_quantities": {}
        }, headers=headers)
        
        assert response.status_code == 200, f"Booking v2 failed: {response.text}"
        data = response.json()
        assert 'id' in data
        assert 'total_price' in data
        assert data['total_price'] > 0
        test_data['booking_v2_id'] = data['id']
        print(f"Created booking v2: {data['id']}, price: ${data['total_price']}")
    
    def test_booking_modify(self):
        """PATCH /api/bookings/{id}/modify"""
        if 'booking_v2_id' not in test_data:
            pytest.skip("No booking to modify")
        
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        
        response = requests.patch(
            f"{BASE_URL}/api/bookings/{test_data['booking_v2_id']}/modify",
            json={
                "notes": "Modified booking notes",
                "modification_reason": "Customer requested change"
            },
            headers=headers
        )
        
        assert response.status_code == 200, f"Modify booking failed: {response.text}"
        data = response.json()
        assert 'message' in data
        print(f"Modified booking: {data}")
    
    def test_get_single_booking(self):
        """GET /api/bookings/{id}"""
        if 'booking_v2_id' not in test_data:
            pytest.skip("No booking to get")
        
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        response = requests.get(
            f"{BASE_URL}/api/bookings/{test_data['booking_v2_id']}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Get booking failed: {response.text}"
        data = response.json()
        assert data['id'] == test_data['booking_v2_id']
        assert 'total_price' in data
        assert 'status' in data
        print(f"Got booking: {data['id']}, status: {data['status']}")


class TestPhase3Invoices:
    """Phase 3 - Invoices Tests"""
    
    def test_invoices_get_customer(self):
        """GET /api/invoices - Customer view"""
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        response = requests.get(f"{BASE_URL}/api/invoices", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Customer invoices: {len(data)}")
        
        if data:
            test_data['invoice_id'] = data[0]['id']
    
    def test_invoices_get_admin(self):
        """GET /api/invoices - Admin view (all)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/invoices", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"All invoices (admin): {len(data)}")
    
    def test_invoice_get_by_id(self):
        """GET /api/invoices/{id}"""
        if 'invoice_id' not in test_data:
            pytest.skip("No invoice to get")
        
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        response = requests.get(
            f"{BASE_URL}/api/invoices/{test_data['invoice_id']}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == test_data['invoice_id']
        assert 'total_amount' in data
        assert 'invoice_number' in data
        print(f"Got invoice: {data['invoice_number']}, total: ${data['total_amount']}")


class TestPhase3PaymentHistory:
    """Phase 3 - Payment History Tests"""
    
    def test_payment_history_customer(self):
        """GET /api/payments/history - Customer view"""
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        response = requests.get(f"{BASE_URL}/api/payments/history", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Customer payment history: {len(data)} payments")
    
    def test_payment_history_admin(self):
        """GET /api/payments/history - Admin view"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/payments/history", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"All payment history (admin): {len(data)} payments")


class TestPhase4Notifications:
    """Phase 4 - Notifications Tests"""
    
    def test_notifications_get(self):
        """GET /api/notifications"""
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"User notifications: {len(data)}")
        
        if data:
            test_data['notification_id'] = data[0]['id']
    
    def test_notifications_unread_count(self):
        """GET /api/notifications/unread-count"""
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        response = requests.get(f"{BASE_URL}/api/notifications/unread-count", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert 'unread_count' in data
        assert isinstance(data['unread_count'], int)
        print(f"Unread notifications: {data['unread_count']}")
    
    def test_notification_mark_read(self):
        """POST /api/notifications/{id}/read"""
        if 'notification_id' not in test_data:
            pytest.skip("No notification to mark read")
        
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        response = requests.post(
            f"{BASE_URL}/api/notifications/{test_data['notification_id']}/read",
            headers=headers
        )
        
        assert response.status_code == 200
        print(f"Marked notification as read")
    
    def test_notifications_mark_all_read(self):
        """POST /api/notifications/mark-all-read"""
        headers = {"Authorization": f"Bearer {test_data['customer_token']}"}
        response = requests.post(f"{BASE_URL}/api/notifications/mark-all-read", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert 'message' in data
        print(f"Mark all read: {data['message']}")


class TestPhase4NotificationTemplates:
    """Phase 4 - Notification Templates (Admin) Tests"""
    
    def test_notification_templates_get(self):
        """GET /api/admin/notification-templates"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/admin/notification-templates", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Notification templates: {len(data)}")
    
    def test_notification_template_create(self):
        """POST /api/admin/notification-templates"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        
        response = requests.post(f"{BASE_URL}/api/admin/notification-templates", json={
            "name": "Test Template",
            "notification_type": "custom",
            "channel": "in_app",
            "subject": "Test Subject {{dog_name}}",
            "body": "Hello {{customer_name}}, this is a test notification for {{dog_name}}.",
            "active": True,
            "delay_minutes": 0
        }, headers=headers)
        
        assert response.status_code == 200, f"Create template failed: {response.text}"
        data = response.json()
        assert 'id' in data
        test_data['template_id'] = data['id']
        print(f"Created notification template: {data['id']}")
    
    def test_notification_template_update(self):
        """PATCH /api/admin/notification-templates/{id}"""
        if 'template_id' not in test_data:
            pytest.skip("No template to update")
        
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.patch(
            f"{BASE_URL}/api/admin/notification-templates/{test_data['template_id']}",
            json={"subject": "Updated Test Subject"},
            headers=headers
        )
        
        assert response.status_code == 200
        print("Updated notification template")
    
    def test_notification_templates_staff_denied(self):
        """Staff should not access notification templates"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/admin/notification-templates", headers=headers)
        
        assert response.status_code == 403
        print("Staff correctly denied access to notification templates")


class TestPhase4AutomationRules:
    """Phase 4 - Automation Rules (Admin) Tests"""
    
    def test_automation_rules_get(self):
        """GET /api/admin/automation-rules"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/admin/automation-rules", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Automation rules: {len(data)}")
    
    def test_automation_rule_create(self):
        """POST /api/admin/automation-rules"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        
        response = requests.post(f"{BASE_URL}/api/admin/automation-rules", json={
            "name": "Test Automation Rule",
            "description": "Test rule for testing",
            "trigger_event": "booking.created",
            "conditions": {"status": "pending"},
            "actions": [
                {
                    "type": "send_notification",
                    "notification_type": "custom",
                    "channel": "in_app",
                    "subject": "New Booking",
                    "body": "A new booking has been created."
                }
            ],
            "active": True,
            "priority": 10
        }, headers=headers)
        
        assert response.status_code == 200, f"Create rule failed: {response.text}"
        data = response.json()
        assert 'id' in data
        test_data['automation_rule_id'] = data['id']
        print(f"Created automation rule: {data['id']}")
    
    def test_automation_rule_update(self):
        """PATCH /api/admin/automation-rules/{id}"""
        if 'automation_rule_id' not in test_data:
            pytest.skip("No rule to update")
        
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.patch(
            f"{BASE_URL}/api/admin/automation-rules/{test_data['automation_rule_id']}",
            json={"active": False},
            headers=headers
        )
        
        assert response.status_code == 200
        print("Updated automation rule (deactivated)")
    
    def test_automation_rule_delete(self):
        """DELETE /api/admin/automation-rules/{id}"""
        if 'automation_rule_id' not in test_data:
            pytest.skip("No rule to delete")
        
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.delete(
            f"{BASE_URL}/api/admin/automation-rules/{test_data['automation_rule_id']}",
            headers=headers
        )
        
        assert response.status_code == 200
        print(f"Deleted automation rule: {test_data['automation_rule_id']}")


class TestPhase4EventLogs:
    """Phase 4 - Event Logs (Admin) Tests"""
    
    def test_event_logs_get(self):
        """GET /api/admin/event-logs"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/admin/event-logs", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Event logs: {len(data)}")
    
    def test_event_logs_with_filter(self):
        """GET /api/admin/event-logs with event_type filter"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(
            f"{BASE_URL}/api/admin/event-logs?event_type=booking.created&limit=10",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Filtered event logs (booking.created): {len(data)}")
    
    def test_event_logs_staff_denied(self):
        """Staff should not access event logs"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/admin/event-logs", headers=headers)
        
        assert response.status_code == 403
        print("Staff correctly denied access to event logs")


class TestPhase4SendNotification:
    """Phase 4 - Send Notification (Admin) Tests"""
    
    def test_send_notification(self):
        """POST /api/admin/send-notification"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        
        response = requests.post(f"{BASE_URL}/api/admin/send-notification", json={
            "user_id": test_data['customer_id'],
            "subject": "Test Manual Notification",
            "body": "This is a test notification sent manually by admin.",
            "channel": "in_app"
        }, headers=headers)
        
        assert response.status_code == 200, f"Send notification failed: {response.text}"
        data = response.json()
        assert 'notification_id' in data
        print(f"Sent notification: {data['notification_id']}")
    
    def test_send_notification_invalid_user(self):
        """POST /api/admin/send-notification - Invalid user"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        
        response = requests.post(f"{BASE_URL}/api/admin/send-notification", json={
            "user_id": "nonexistent-user-id",
            "subject": "Test",
            "body": "Test",
            "channel": "in_app"
        }, headers=headers)
        
        assert response.status_code == 404
        print("Correctly returned 404 for invalid user")
    
    def test_send_notification_staff_denied(self):
        """Staff should not send manual notifications"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        
        response = requests.post(f"{BASE_URL}/api/admin/send-notification", json={
            "user_id": test_data['customer_id'],
            "subject": "Test",
            "body": "Test",
            "channel": "in_app"
        }, headers=headers)
        
        assert response.status_code == 403
        print("Staff correctly denied access to send notifications")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
