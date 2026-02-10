"""
K9Command - Connecteam Parity Phase 1 Backend API Tests
Tests for GPS Time Clock, Breaks, Overtime, Forms Engine, HR/Time Off, Training, Communications

Test Coverage:
- GPS Time Clock: Clock in/out with GPS coordinates
- Geofencing: Create/list geofence zones
- Break Tracking: Start/end breaks
- Break Policies: Create break policies
- Overtime Rules: Create/list overtime rules
- Punch Rounding: Create rounding rules
- Pay Periods: Create pay periods
- Forms Engine: Create templates, submit forms with signature/GPS
- Task Templates: Create task templates
- Time Off: Policies, requests, balances
- Announcements: Create, acknowledge
- Training Courses: Create, start, complete sections
- Quizzes: Create quizzes
- Knowledge Base: Create/search articles
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

# Test GPS coordinates (San Francisco)
TEST_LAT = 37.7749
TEST_LON = -122.4194
TEST_LAT_OUTSIDE = 37.8000  # Outside 100m geofence

# Test location ID
LOCATION_ID = "be41bc5e-ca79-4c80-bfae-21381586de2a"

# Test data storage
test_data = {}


class TestSetup:
    """Setup tests - authenticate users"""
    
    def test_login_admin(self):
        """Login admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "full_name": "Test Admin",
            "phone": "555-0001",
            "role": "admin"
        })
        if response.status_code == 400:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
        
        assert response.status_code in [200, 201], f"Admin auth failed: {response.text}"
        data = response.json()
        test_data['admin_token'] = data['token']
        test_data['admin_id'] = data['user']['id']
        print(f"Admin authenticated: {test_data['admin_id']}")
    
    def test_login_staff(self):
        """Login staff user"""
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


# ==================== GEOFENCING TESTS ====================

class TestGeofencing:
    """Test geofence zone CRUD operations"""
    
    def test_create_geofence(self):
        """Create a geofence zone (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/timeclock/geofences", json={
            "name": "TEST_Main Facility",
            "location_id": LOCATION_ID,
            "latitude": TEST_LAT,
            "longitude": TEST_LON,
            "radius": 100.0,
            "is_active": True,
            "require_within": True,
            "description": "Main facility geofence for testing"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create geofence failed: {response.text}"
        data = response.json()
        assert data['name'] == "TEST_Main Facility"
        assert data['latitude'] == TEST_LAT
        assert data['longitude'] == TEST_LON
        assert data['radius'] == 100.0
        test_data['geofence_id'] = data['id']
        print(f"Created geofence: {test_data['geofence_id']}")
    
    def test_list_geofences(self):
        """List geofence zones"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/timeclock/geofences", headers=headers)
        
        assert response.status_code == 200, f"List geofences failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} geofences")
    
    def test_geofence_staff_denied(self):
        """Staff cannot create geofences"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(f"{BASE_URL}/api/timeclock/geofences", json={
            "name": "Unauthorized Geofence",
            "location_id": LOCATION_ID,
            "latitude": TEST_LAT,
            "longitude": TEST_LON,
            "radius": 50.0
        }, headers=headers)
        
        assert response.status_code == 403, f"Staff should be denied: {response.text}"
        print("Staff correctly denied geofence creation")


# ==================== GPS TIME CLOCK TESTS ====================

class TestGPSTimeClock:
    """Test GPS-enabled clock in/out"""
    
    def test_clock_in_with_gps(self):
        """Clock in with GPS coordinates"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(f"{BASE_URL}/api/timeclock/clock-in", json={
            "location_id": LOCATION_ID,
            "latitude": TEST_LAT,
            "longitude": TEST_LON,
            "accuracy": 10.0,
            "source": "mobile",
            "notes": "Test clock in"
        }, headers=headers)
        
        assert response.status_code == 200, f"Clock in failed: {response.text}"
        data = response.json()
        assert data['staff_id'] == test_data['staff_id']
        assert data['location_id'] == LOCATION_ID
        assert data['clock_in'] is not None
        assert data['clock_out'] is None
        test_data['time_entry_id'] = data['id']
        print(f"Clocked in: {test_data['time_entry_id']}")
    
    def test_clock_in_already_clocked_in(self):
        """Cannot clock in when already clocked in"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(f"{BASE_URL}/api/timeclock/clock-in", json={
            "location_id": LOCATION_ID,
            "latitude": TEST_LAT,
            "longitude": TEST_LON
        }, headers=headers)
        
        assert response.status_code == 400, f"Should fail when already clocked in: {response.text}"
        assert "already clocked in" in response.text.lower()
        print("Correctly prevented double clock-in")
    
    def test_get_current_entry(self):
        """Get current active time entry"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/timeclock/entries/current", headers=headers)
        
        assert response.status_code == 200, f"Get current entry failed: {response.text}"
        data = response.json()
        if data:
            assert data['id'] == test_data['time_entry_id']
            print(f"Current entry: {data['id']}")
        else:
            print("No current entry (may have been clocked out)")


# ==================== BREAK TRACKING TESTS ====================

class TestBreakTracking:
    """Test break start/end functionality"""
    
    def test_start_break(self):
        """Start a break"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(f"{BASE_URL}/api/timeclock/breaks/start", json={
            "time_entry_id": test_data['time_entry_id'],
            "break_type": "lunch",
            "latitude": TEST_LAT,
            "longitude": TEST_LON,
            "notes": "Lunch break"
        }, headers=headers)
        
        assert response.status_code == 200, f"Start break failed: {response.text}"
        data = response.json()
        assert data['time_entry_id'] == test_data['time_entry_id']
        assert data['break_type'] == "lunch"
        assert data['start_time'] is not None
        assert data['end_time'] is None
        test_data['break_id'] = data['id']
        print(f"Started break: {test_data['break_id']}")
    
    def test_start_break_already_on_break(self):
        """Cannot start break when already on break"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(f"{BASE_URL}/api/timeclock/breaks/start", json={
            "time_entry_id": test_data['time_entry_id'],
            "break_type": "rest"
        }, headers=headers)
        
        assert response.status_code == 400, f"Should fail when already on break: {response.text}"
        print("Correctly prevented double break start")
    
    def test_end_break(self):
        """End current break"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(
            f"{BASE_URL}/api/timeclock/breaks/end",
            params={
                "time_entry_id": test_data['time_entry_id'],
                "latitude": TEST_LAT,
                "longitude": TEST_LON
            },
            headers=headers
        )
        
        assert response.status_code == 200, f"End break failed: {response.text}"
        data = response.json()
        assert data['end_time'] is not None
        assert data['duration_minutes'] is not None
        print(f"Ended break, duration: {data['duration_minutes']} minutes")
    
    def test_list_breaks(self):
        """List breaks for time entry"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(
            f"{BASE_URL}/api/timeclock/breaks",
            params={"time_entry_id": test_data['time_entry_id']},
            headers=headers
        )
        
        assert response.status_code == 200, f"List breaks failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        print(f"Found {len(data)} breaks")


# ==================== CLOCK OUT TEST ====================

class TestClockOut:
    """Test clock out functionality"""
    
    def test_clock_out_with_gps(self):
        """Clock out with GPS coordinates"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(
            f"{BASE_URL}/api/timeclock/clock-out",
            params={
                "latitude": TEST_LAT,
                "longitude": TEST_LON,
                "source": "mobile"
            },
            headers=headers
        )
        
        assert response.status_code == 200, f"Clock out failed: {response.text}"
        data = response.json()
        assert data['clock_out'] is not None
        assert data['regular_hours'] >= 0
        print(f"Clocked out, regular hours: {data['regular_hours']}")
    
    def test_clock_out_no_active_entry(self):
        """Cannot clock out without active entry"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(
            f"{BASE_URL}/api/timeclock/clock-out",
            params={"latitude": TEST_LAT, "longitude": TEST_LON},
            headers=headers
        )
        
        assert response.status_code == 400, f"Should fail without active entry: {response.text}"
        print("Correctly prevented clock out without active entry")


# ==================== BREAK POLICIES TESTS ====================

class TestBreakPolicies:
    """Test break policy management"""
    
    def test_create_break_policy(self):
        """Create a break policy (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/timeclock/break-policies", json={
            "name": "TEST_Standard Break Policy",
            "location_id": LOCATION_ID,
            "min_shift_for_break": 4.0,
            "break_duration_minutes": 30,
            "is_paid": False,
            "auto_deduct": False,
            "second_break_after_hours": 8.0,
            "second_break_duration_minutes": 15,
            "is_active": True,
            "description": "Standard break policy for testing"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create break policy failed: {response.text}"
        data = response.json()
        assert data['name'] == "TEST_Standard Break Policy"
        assert data['min_shift_for_break'] == 4.0
        assert data['break_duration_minutes'] == 30
        test_data['break_policy_id'] = data['id']
        print(f"Created break policy: {test_data['break_policy_id']}")
    
    def test_list_break_policies(self):
        """List break policies"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/timeclock/break-policies", headers=headers)
        
        assert response.status_code == 200, f"List break policies failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} break policies")


# ==================== OVERTIME RULES TESTS ====================

class TestOvertimeRules:
    """Test overtime rule management"""
    
    def test_create_overtime_rule(self):
        """Create an overtime rule (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/timeclock/overtime-rules", json={
            "name": "TEST_Standard Overtime",
            "location_id": LOCATION_ID,
            "weekly_regular_hours": 40.0,
            "weekly_overtime_multiplier": 1.5,
            "weekly_double_time_hours": 60.0,
            "double_time_multiplier": 2.0,
            "daily_regular_hours": 8.0,
            "daily_overtime_multiplier": 1.5,
            "max_weekly_hours": 60.0,
            "is_active": True,
            "priority": 1,
            "description": "Standard overtime rules for testing"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create overtime rule failed: {response.text}"
        data = response.json()
        assert data['name'] == "TEST_Standard Overtime"
        assert data['weekly_regular_hours'] == 40.0
        assert data['weekly_overtime_multiplier'] == 1.5
        test_data['overtime_rule_id'] = data['id']
        print(f"Created overtime rule: {test_data['overtime_rule_id']}")
    
    def test_list_overtime_rules(self):
        """List overtime rules"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/timeclock/overtime-rules", headers=headers)
        
        assert response.status_code == 200, f"List overtime rules failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} overtime rules")


# ==================== PUNCH ROUNDING TESTS ====================

class TestPunchRounding:
    """Test punch rounding rule management"""
    
    def test_create_rounding_rule(self):
        """Create a punch rounding rule (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/timeclock/rounding-rules", json={
            "name": "TEST_15 Minute Rounding",
            "location_id": LOCATION_ID,
            "interval_minutes": 15,
            "clock_in_direction": "nearest",
            "clock_out_direction": "nearest",
            "grace_period_minutes": 5,
            "is_active": True,
            "description": "15 minute rounding for testing"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create rounding rule failed: {response.text}"
        data = response.json()
        assert data['name'] == "TEST_15 Minute Rounding"
        assert data['interval_minutes'] == 15
        test_data['rounding_rule_id'] = data['id']
        print(f"Created rounding rule: {test_data['rounding_rule_id']}")
    
    def test_list_rounding_rules(self):
        """List rounding rules"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/timeclock/rounding-rules", headers=headers)
        
        assert response.status_code == 200, f"List rounding rules failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} rounding rules")


# ==================== PAY PERIODS TESTS ====================

class TestPayPeriods:
    """Test pay period management"""
    
    def test_create_pay_period(self):
        """Create a pay period (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        start_date = datetime.now().replace(day=1)
        end_date = start_date + timedelta(days=14)
        
        response = requests.post(f"{BASE_URL}/api/timeclock/pay-periods", json={
            "name": "TEST_Pay Period Jan 2026",
            "location_id": LOCATION_ID,
            "period_type": "biweekly",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "notes": "Test pay period"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create pay period failed: {response.text}"
        data = response.json()
        assert data['name'] == "TEST_Pay Period Jan 2026"
        assert data['period_type'] == "biweekly"
        assert data['status'] == "open"
        test_data['pay_period_id'] = data['id']
        print(f"Created pay period: {test_data['pay_period_id']}")
    
    def test_list_pay_periods(self):
        """List pay periods"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/timeclock/pay-periods", headers=headers)
        
        assert response.status_code == 200, f"List pay periods failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} pay periods")


# ==================== FORMS ENGINE TESTS ====================

class TestFormsEngine:
    """Test forms template and submission functionality"""
    
    def test_create_form_template(self):
        """Create a form template (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/forms/templates", json={
            "name": "TEST_Daily Inspection Form",
            "description": "Daily facility inspection checklist",
            "location_id": LOCATION_ID,
            "fields": [
                {
                    "field_type": "text",
                    "label": "Inspector Name",
                    "required": True
                },
                {
                    "field_type": "checkbox",
                    "label": "All areas clean",
                    "required": True
                },
                {
                    "field_type": "textarea",
                    "label": "Notes",
                    "required": False
                },
                {
                    "field_type": "number",
                    "label": "Temperature Reading",
                    "required": True,
                    "min_value": 60,
                    "max_value": 80
                }
            ],
            "assignable_to": "staff",
            "require_signature": True,
            "require_gps": True,
            "allow_save_draft": True,
            "allow_edit_after_submit": False,
            "is_active": True,
            "category": "inspection",
            "tags": ["daily", "inspection", "facility"]
        }, headers=headers)
        
        assert response.status_code == 200, f"Create form template failed: {response.text}"
        data = response.json()
        assert data['name'] == "TEST_Daily Inspection Form"
        assert data['require_signature'] == True
        assert data['require_gps'] == True
        assert len(data['fields']) == 4
        test_data['form_template_id'] = data['id']
        print(f"Created form template: {test_data['form_template_id']}")
    
    def test_list_form_templates(self):
        """List form templates"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/forms/templates", headers=headers)
        
        assert response.status_code == 200, f"List form templates failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} form templates")
    
    def test_get_form_template(self):
        """Get single form template"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(
            f"{BASE_URL}/api/forms/templates/{test_data['form_template_id']}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Get form template failed: {response.text}"
        data = response.json()
        assert data['id'] == test_data['form_template_id']
        print(f"Retrieved form template: {data['name']}")
    
    def test_submit_form_with_signature_and_gps(self):
        """Submit form with signature and GPS"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        
        # First get the template to get field IDs
        template_response = requests.get(
            f"{BASE_URL}/api/forms/templates/{test_data['form_template_id']}",
            headers=headers
        )
        template = template_response.json()
        fields = template['fields']
        
        # Build values dict using field IDs
        values = {}
        for field in fields:
            if field['label'] == "Inspector Name":
                values[field['id']] = "Test Staff"
            elif field['label'] == "All areas clean":
                values[field['id']] = True
            elif field['label'] == "Notes":
                values[field['id']] = "All areas inspected and clean"
            elif field['label'] == "Temperature Reading":
                values[field['id']] = 72
        
        response = requests.post(f"{BASE_URL}/api/forms/submissions", json={
            "template_id": test_data['form_template_id'],
            "values": values,
            "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "gps_latitude": TEST_LAT,
            "gps_longitude": TEST_LON,
            "gps_accuracy": 10.0,
            "status": "submitted"
        }, headers=headers)
        
        assert response.status_code == 200, f"Submit form failed: {response.text}"
        data = response.json()
        assert data['template_id'] == test_data['form_template_id']
        assert data['status'] == "submitted"
        assert data['signature_data'] is not None
        assert data['gps_latitude'] == TEST_LAT
        test_data['form_submission_id'] = data['id']
        print(f"Submitted form: {test_data['form_submission_id']}")
    
    def test_submit_form_missing_required_field(self):
        """Form submission fails with missing required field"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(f"{BASE_URL}/api/forms/submissions", json={
            "template_id": test_data['form_template_id'],
            "values": {},  # Missing required fields
            "status": "submitted"
        }, headers=headers)
        
        assert response.status_code == 400, f"Should fail with missing required fields: {response.text}"
        print("Correctly rejected form with missing required fields")
    
    def test_list_form_submissions(self):
        """List form submissions"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/forms/submissions", headers=headers)
        
        assert response.status_code == 200, f"List submissions failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} form submissions")


# ==================== TASK TEMPLATES TESTS ====================

class TestTaskTemplates:
    """Test task template management"""
    
    def test_create_task_template(self):
        """Create a task template (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/forms/task-templates", json={
            "name": "TEST_Morning Checklist",
            "description": "Daily morning opening checklist",
            "location_id": LOCATION_ID,
            "checklist_items": [
                {"text": "Check water bowls", "required": True},
                {"text": "Inspect play areas", "required": True},
                {"text": "Review arrivals list", "required": True},
                {"text": "Check medication schedule", "required": False}
            ],
            "assign_to_role": "staff",
            "default_due_hours": 2,
            "priority": "high",
            "reminder_hours_before": [1],
            "is_active": True,
            "category": "daily",
            "tags": ["morning", "checklist", "opening"]
        }, headers=headers)
        
        assert response.status_code == 200, f"Create task template failed: {response.text}"
        data = response.json()
        assert data['name'] == "TEST_Morning Checklist"
        assert len(data['checklist_items']) == 4
        assert data['priority'] == "high"
        test_data['task_template_id'] = data['id']
        print(f"Created task template: {test_data['task_template_id']}")
    
    def test_list_task_templates(self):
        """List task templates"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/forms/task-templates", headers=headers)
        
        assert response.status_code == 200, f"List task templates failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} task templates")


# ==================== TIME OFF POLICIES TESTS ====================

class TestTimeOffPolicies:
    """Test time off policy management"""
    
    def test_create_time_off_policy(self):
        """Create a time off policy (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/hr/time-off-policies", json={
            "name": "TEST_PTO Policy",
            "time_off_type": "vacation",
            "accrual_rate": 1.25,
            "accrual_frequency": "per_pay_period",
            "max_balance": 120.0,
            "max_carryover": 40.0,
            "waiting_period_days": 90,
            "min_increment_hours": 1.0,
            "requires_approval": True,
            "advance_notice_days": 14,
            "is_active": True,
            "description": "Standard PTO policy for testing"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create time off policy failed: {response.text}"
        data = response.json()
        assert data['name'] == "TEST_PTO Policy"
        assert data['time_off_type'] == "vacation"
        assert data['accrual_rate'] == 1.25
        test_data['time_off_policy_id'] = data['id']
        print(f"Created time off policy: {test_data['time_off_policy_id']}")
    
    def test_list_time_off_policies(self):
        """List time off policies"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/hr/time-off-policies", headers=headers)
        
        assert response.status_code == 200, f"List time off policies failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} time off policies")


# ==================== TIME OFF BALANCES TESTS ====================

class TestTimeOffBalances:
    """Test time off balance management"""
    
    def test_adjust_balance(self):
        """Adjust staff time off balance (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(
            f"{BASE_URL}/api/hr/balances/{test_data['staff_id']}/adjust",
            params={
                "policy_id": test_data['time_off_policy_id'],
                "adjustment": 40.0,
                "reason": "Initial balance allocation"
            },
            headers=headers
        )
        
        assert response.status_code == 200, f"Adjust balance failed: {response.text}"
        data = response.json()
        assert data['current_balance'] == 40.0
        test_data['balance_id'] = data['id']
        print(f"Adjusted balance to: {data['current_balance']} hours")
    
    def test_get_balances(self):
        """Get time off balances"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/hr/balances", headers=headers)
        
        assert response.status_code == 200, f"Get balances failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} balance records")


# ==================== TIME OFF REQUESTS TESTS ====================

class TestTimeOffRequests:
    """Test time off request management"""
    
    def test_create_time_off_request(self):
        """Create a time off request"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        start_date = datetime.now() + timedelta(days=30)
        end_date = start_date + timedelta(days=2)
        
        response = requests.post(f"{BASE_URL}/api/hr/time-off-requests", json={
            "policy_id": test_data['time_off_policy_id'],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "hours_requested": 16.0,
            "reason": "Family vacation",
            "notes": "Will be available by phone for emergencies"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create time off request failed: {response.text}"
        data = response.json()
        assert data['staff_id'] == test_data['staff_id']
        assert data['hours_requested'] == 16.0
        assert data['status'] == "pending"
        test_data['time_off_request_id'] = data['id']
        print(f"Created time off request: {test_data['time_off_request_id']}")
    
    def test_list_time_off_requests(self):
        """List time off requests"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/hr/time-off-requests", headers=headers)
        
        assert response.status_code == 200, f"List time off requests failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} time off requests")
    
    def test_approve_time_off_request(self):
        """Approve a time off request (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(
            f"{BASE_URL}/api/hr/time-off-requests/{test_data['time_off_request_id']}/approve",
            headers=headers
        )
        
        assert response.status_code == 200, f"Approve request failed: {response.text}"
        data = response.json()
        assert data['status'] == "approved"
        print(f"Approved time off request")


# ==================== ANNOUNCEMENTS TESTS ====================

class TestAnnouncements:
    """Test announcement management"""
    
    def test_create_announcement(self):
        """Create an announcement (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/comms/announcements", json={
            "title": "TEST_Important Update",
            "content": "This is a test announcement for all staff members.",
            "priority": "high",
            "target_roles": [],
            "requires_acknowledgement": True,
            "acknowledgement_deadline": (datetime.now() + timedelta(days=7)).isoformat(),
            "is_pinned": True,
            "status": "published"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create announcement failed: {response.text}"
        data = response.json()
        assert data['title'] == "TEST_Important Update"
        assert data['priority'] == "high"
        assert data['requires_acknowledgement'] == True
        test_data['announcement_id'] = data['id']
        print(f"Created announcement: {test_data['announcement_id']}")
    
    def test_list_announcements(self):
        """List announcements"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/comms/announcements", headers=headers)
        
        assert response.status_code == 200, f"List announcements failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} announcements")
    
    def test_acknowledge_announcement(self):
        """Acknowledge an announcement"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(
            f"{BASE_URL}/api/comms/announcements/{test_data['announcement_id']}/acknowledge",
            headers=headers
        )
        
        assert response.status_code == 200, f"Acknowledge announcement failed: {response.text}"
        data = response.json()
        assert test_data['staff_id'] in data.get('acknowledged_by', [])
        print(f"Acknowledged announcement")


# ==================== TRAINING COURSES TESTS ====================

class TestTrainingCourses:
    """Test training course management"""
    
    def test_create_course(self):
        """Create a training course (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/comms/courses", json={
            "title": "TEST_Safety Training",
            "description": "Comprehensive safety training for all staff",
            "category": "safety",
            "sections": [
                {
                    "id": "sec1",
                    "title": "Introduction to Safety",
                    "content": "Safety is our top priority...",
                    "order": 1
                },
                {
                    "id": "sec2",
                    "title": "Emergency Procedures",
                    "content": "In case of emergency...",
                    "order": 2
                }
            ],
            "duration_minutes": 60,
            "required_for_new_staff": True,
            "due_days_after_start": 7,
            "passing_score": 80,
            "status": "published",
            "tags": ["safety", "required", "onboarding"]
        }, headers=headers)
        
        assert response.status_code == 200, f"Create course failed: {response.text}"
        data = response.json()
        assert data['title'] == "TEST_Safety Training"
        assert len(data['sections']) == 2
        assert data['required_for_new_staff'] == True
        test_data['course_id'] = data['id']
        print(f"Created course: {test_data['course_id']}")
    
    def test_list_courses(self):
        """List training courses"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/comms/courses", headers=headers)
        
        assert response.status_code == 200, f"List courses failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} courses")
    
    def test_start_course(self):
        """Start a training course"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(
            f"{BASE_URL}/api/comms/courses/{test_data['course_id']}/start",
            headers=headers
        )
        
        assert response.status_code == 200, f"Start course failed: {response.text}"
        data = response.json()
        assert data['course_id'] == test_data['course_id']
        assert data['status'] == "in_progress"
        test_data['course_progress_id'] = data['id']
        print(f"Started course: {test_data['course_progress_id']}")
    
    def test_complete_section(self):
        """Complete a course section"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(
            f"{BASE_URL}/api/comms/courses/{test_data['course_id']}/complete-section",
            params={"section_id": "sec1"},
            headers=headers
        )
        
        assert response.status_code == 200, f"Complete section failed: {response.text}"
        data = response.json()
        assert "sec1" in data.get('completed_sections', [])
        print(f"Completed section sec1")


# ==================== QUIZZES TESTS ====================

class TestQuizzes:
    """Test quiz management"""
    
    def test_create_quiz(self):
        """Create a quiz (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/comms/quizzes", json={
            "title": "TEST_Safety Quiz",
            "description": "Test your safety knowledge",
            "course_id": test_data['course_id'],
            "questions": [
                {
                    "id": "q1",
                    "question": "What is the first step in an emergency?",
                    "question_type": "multiple_choice",
                    "options": [
                        {"id": "a", "text": "Panic"},
                        {"id": "b", "text": "Stay calm and assess"},
                        {"id": "c", "text": "Run away"}
                    ],
                    "correct_answer": "b",
                    "points": 10
                },
                {
                    "id": "q2",
                    "question": "Safety is everyone's responsibility",
                    "question_type": "true_false",
                    "correct_answer": "true",
                    "points": 10
                }
            ],
            "passing_score": 80,
            "time_limit_minutes": 30,
            "allow_retakes": True,
            "max_retakes": 3,
            "is_active": True
        }, headers=headers)
        
        assert response.status_code == 200, f"Create quiz failed: {response.text}"
        data = response.json()
        assert data['title'] == "TEST_Safety Quiz"
        assert len(data['questions']) == 2
        assert data['passing_score'] == 80
        test_data['quiz_id'] = data['id']
        print(f"Created quiz: {test_data['quiz_id']}")
    
    def test_list_quizzes(self):
        """List quizzes"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.get(f"{BASE_URL}/api/comms/quizzes", headers=headers)
        
        assert response.status_code == 200, f"List quizzes failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} quizzes")


# ==================== KNOWLEDGE BASE TESTS ====================

class TestKnowledgeBase:
    """Test knowledge base management"""
    
    def test_create_article(self):
        """Create a knowledge base article (admin only)"""
        headers = {"Authorization": f"Bearer {test_data['admin_token']}"}
        response = requests.post(f"{BASE_URL}/api/comms/knowledge", json={
            "title": "TEST_Emergency Procedures",
            "content": "# Emergency Procedures\n\n## Fire\n1. Sound alarm\n2. Evacuate\n3. Call 911\n\n## Medical\n1. Assess situation\n2. Call for help\n3. Administer first aid",
            "category": "safety",
            "tags": ["emergency", "safety", "procedures"],
            "status": "published",
            "visible_to_roles": []
        }, headers=headers)
        
        assert response.status_code == 200, f"Create article failed: {response.text}"
        data = response.json()
        assert data['title'] == "TEST_Emergency Procedures"
        assert data['status'] == "published"
        test_data['article_id'] = data['id']
        print(f"Created article: {test_data['article_id']}")
    
    def test_list_articles(self):
        """List knowledge base articles"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/comms/knowledge", headers=headers)
        
        assert response.status_code == 200, f"List articles failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} articles")
    
    def test_search_articles(self):
        """Search knowledge base articles"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(
            f"{BASE_URL}/api/comms/knowledge",
            params={"search": "emergency"},
            headers=headers
        )
        
        assert response.status_code == 200, f"Search articles failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} articles matching 'emergency'")


# ==================== TIME ENTRIES LIST TEST ====================

class TestTimeEntriesList:
    """Test time entries listing"""
    
    def test_list_time_entries(self):
        """List time entries"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.get(f"{BASE_URL}/api/timeclock/entries", headers=headers)
        
        assert response.status_code == 200, f"List time entries failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} time entries")


# ==================== AUTHORIZATION TESTS ====================

class TestAuthorization:
    """Test authorization and access control"""
    
    def test_unauthenticated_access_denied(self):
        """Unauthenticated requests are denied"""
        response = requests.get(f"{BASE_URL}/api/timeclock/geofences")
        assert response.status_code == 403, f"Should deny unauthenticated: {response.text}"
        print("Correctly denied unauthenticated access")
    
    def test_staff_cannot_create_overtime_rules(self):
        """Staff cannot create overtime rules"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(f"{BASE_URL}/api/timeclock/overtime-rules", json={
            "name": "Unauthorized Rule",
            "weekly_regular_hours": 40.0
        }, headers=headers)
        
        assert response.status_code == 403, f"Staff should be denied: {response.text}"
        print("Correctly denied staff from creating overtime rules")
    
    def test_staff_cannot_create_time_off_policy(self):
        """Staff cannot create time off policies"""
        headers = {"Authorization": f"Bearer {test_data['staff_token']}"}
        response = requests.post(f"{BASE_URL}/api/hr/time-off-policies", json={
            "name": "Unauthorized Policy",
            "time_off_type": "vacation"
        }, headers=headers)
        
        assert response.status_code == 403, f"Staff should be denied: {response.text}"
        print("Correctly denied staff from creating time off policies")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
