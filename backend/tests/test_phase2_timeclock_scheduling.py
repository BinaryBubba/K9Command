"""
Phase 2 - Time Clock & Scheduling Backend Tests
Tests for GPS clock in/out, breaks, scheduling, shifts, and kiosk mode
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://teamflow-118.preview.emergentagent.com')

# Test credentials
STAFF_EMAIL = "staff_test_new@k9.com"
STAFF_PASSWORD = "Test123!"
ADMIN_EMAIL = "admin_test_new@k9.com"
ADMIN_PASSWORD = "Test123!"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        """Get staff auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Staff login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    def test_staff_login(self, staff_token):
        """Test staff can login"""
        assert staff_token is not None
        print(f"✓ Staff login successful")
    
    def test_admin_login(self, admin_token):
        """Test admin can login"""
        assert admin_token is not None
        print(f"✓ Admin login successful")


class TestTimeClockEntries:
    """Time Clock Entry tests"""
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Staff login failed")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_get_current_entry(self, staff_token):
        """Test getting current time entry"""
        response = requests.get(
            f"{BASE_URL}/api/timeclock/entries/current",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 200
        # Can be null if not clocked in
        print(f"✓ Get current entry: {response.json()}")
    
    def test_list_time_entries(self, staff_token):
        """Test listing time entries"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(
            f"{BASE_URL}/api/timeclock/entries?start_date={today}T00:00:00Z&end_date={today}T23:59:59Z",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List time entries: {len(data)} entries found")
    
    def test_clock_in_with_gps(self, staff_token):
        """Test clock in with GPS coordinates"""
        # First check if already clocked in
        current = requests.get(
            f"{BASE_URL}/api/timeclock/entries/current",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        if current.status_code == 200 and current.json():
            # Already clocked in, clock out first
            requests.post(
                f"{BASE_URL}/api/timeclock/clock-out?source=mobile",
                headers={"Authorization": f"Bearer {staff_token}"}
            )
        
        # Now clock in
        response = requests.post(
            f"{BASE_URL}/api/timeclock/clock-in",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={
                "location_id": "main",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "accuracy": 10.0,
                "source": "mobile"
            }
        )
        
        if response.status_code == 400 and "Already clocked in" in response.text:
            print("✓ Clock in prevented (already clocked in)")
            return
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "clock_in" in data
        assert data["staff_id"] is not None
        print(f"✓ Clock in successful: {data['id']}")
    
    def test_clock_out_with_gps(self, staff_token):
        """Test clock out with GPS coordinates"""
        # First ensure we're clocked in
        current = requests.get(
            f"{BASE_URL}/api/timeclock/entries/current",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        if current.status_code == 200 and not current.json():
            # Not clocked in, clock in first
            requests.post(
                f"{BASE_URL}/api/timeclock/clock-in",
                headers={"Authorization": f"Bearer {staff_token}"},
                json={
                    "location_id": "main",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "source": "mobile"
                }
            )
        
        # Now clock out
        response = requests.post(
            f"{BASE_URL}/api/timeclock/clock-out?latitude=37.7749&longitude=-122.4194&source=mobile",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        if response.status_code == 400 and "No active clock-in" in response.text:
            print("✓ Clock out prevented (not clocked in)")
            return
        
        assert response.status_code == 200
        data = response.json()
        assert "clock_out" in data
        assert data["regular_hours"] is not None
        print(f"✓ Clock out successful: {data.get('regular_hours', 0):.2f} hours")


class TestBreaks:
    """Break tracking tests"""
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Staff login failed")
    
    def test_start_break(self, staff_token):
        """Test starting a break"""
        # First ensure we're clocked in
        current = requests.get(
            f"{BASE_URL}/api/timeclock/entries/current",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        if current.status_code == 200 and not current.json():
            # Clock in first
            requests.post(
                f"{BASE_URL}/api/timeclock/clock-in",
                headers={"Authorization": f"Bearer {staff_token}"},
                json={
                    "location_id": "main",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "source": "mobile"
                }
            )
            current = requests.get(
                f"{BASE_URL}/api/timeclock/entries/current",
                headers={"Authorization": f"Bearer {staff_token}"}
            )
        
        entry = current.json()
        if not entry:
            pytest.skip("No active time entry for break test")
        
        response = requests.post(
            f"{BASE_URL}/api/timeclock/breaks/start",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={
                "time_entry_id": entry["id"],
                "break_type": "rest",
                "latitude": 37.7749,
                "longitude": -122.4194
            }
        )
        
        if response.status_code == 400 and "Break already in progress" in response.text:
            print("✓ Break start prevented (already on break)")
            return
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "start_time" in data
        print(f"✓ Break started: {data['id']}")
    
    def test_end_break(self, staff_token):
        """Test ending a break"""
        current = requests.get(
            f"{BASE_URL}/api/timeclock/entries/current",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        if current.status_code != 200 or not current.json():
            pytest.skip("No active time entry for break test")
        
        entry = current.json()
        
        response = requests.post(
            f"{BASE_URL}/api/timeclock/breaks/end?time_entry_id={entry['id']}&latitude=37.7749&longitude=-122.4194",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        if response.status_code == 404 and "No active break" in response.text:
            print("✓ Break end prevented (no active break)")
            return
        
        assert response.status_code == 200
        data = response.json()
        assert "end_time" in data
        assert "duration_minutes" in data
        print(f"✓ Break ended: {data.get('duration_minutes', 0)} minutes")
    
    def test_list_breaks(self, staff_token):
        """Test listing breaks for a time entry"""
        current = requests.get(
            f"{BASE_URL}/api/timeclock/entries/current",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        if current.status_code != 200 or not current.json():
            pytest.skip("No active time entry for break list test")
        
        entry = current.json()
        
        response = requests.get(
            f"{BASE_URL}/api/timeclock/breaks?time_entry_id={entry['id']}",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List breaks: {len(data)} breaks found")


class TestScheduling:
    """Scheduling and shifts tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Staff login failed")
    
    def test_list_shifts(self, staff_token):
        """Test listing shifts"""
        today = datetime.now()
        start = (today - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
        end = (today + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59Z")
        
        response = requests.get(
            f"{BASE_URL}/api/scheduling/shifts?start_date={start}&end_date={end}",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List shifts: {len(data)} shifts found")
    
    def test_create_shift_admin(self, admin_token):
        """Test creating a shift (admin only)"""
        # First get a staff user ID
        staff_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        staff_data = staff_login.json()
        staff_id = staff_data.get("user", {}).get("id")
        
        if not staff_id:
            pytest.skip("Could not get staff ID")
        
        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = tomorrow.replace(hour=17, minute=0, second=0, microsecond=0)
        
        response = requests.post(
            f"{BASE_URL}/api/scheduling/shifts",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "staff_id": staff_id,
                "location_id": "main",
                "start_time": start_time.isoformat() + "Z",
                "end_time": end_time.isoformat() + "Z",
                "status": "draft",
                "color": "#3B82F6"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["staff_id"] == staff_id
        print(f"✓ Shift created: {data['id']}")
        return data["id"]
    
    def test_create_shift_staff_denied(self, staff_token):
        """Test that staff cannot create shifts"""
        tomorrow = datetime.now() + timedelta(days=1)
        
        response = requests.post(
            f"{BASE_URL}/api/scheduling/shifts",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={
                "staff_id": "some-id",
                "location_id": "main",
                "start_time": tomorrow.isoformat() + "Z",
                "end_time": (tomorrow + timedelta(hours=8)).isoformat() + "Z"
            }
        )
        
        assert response.status_code == 403
        print("✓ Staff denied shift creation (403)")
    
    def test_list_swap_requests(self, staff_token):
        """Test listing swap requests"""
        response = requests.get(
            f"{BASE_URL}/api/scheduling/swap-requests",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List swap requests: {len(data)} requests found")


class TestShiftTemplates:
    """Shift template tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_list_templates(self, admin_token):
        """Test listing shift templates"""
        response = requests.get(
            f"{BASE_URL}/api/scheduling/templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List templates: {len(data)} templates found")
    
    def test_create_template(self, admin_token):
        """Test creating a shift template"""
        response = requests.post(
            f"{BASE_URL}/api/scheduling/templates",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "TEST_Morning Shift",
                "location_id": "main",
                "start_time": "09:00",
                "end_time": "17:00",
                "days_of_week": [0, 1, 2, 3, 4],
                "color": "#10B981"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "TEST_Morning Shift"
        print(f"✓ Template created: {data['id']}")


class TestPayPeriods:
    """Pay period tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_list_pay_periods(self, admin_token):
        """Test listing pay periods"""
        response = requests.get(
            f"{BASE_URL}/api/timeclock/pay-periods",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List pay periods: {len(data)} periods found")
    
    def test_create_pay_period(self, admin_token):
        """Test creating a pay period"""
        today = datetime.now()
        start = today.replace(day=1)
        end = (start + timedelta(days=14))
        
        response = requests.post(
            f"{BASE_URL}/api/timeclock/pay-periods",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"TEST_Period_{today.strftime('%Y%m%d')}",
                "period_type": "biweekly",
                "start_date": start.isoformat() + "Z",
                "end_date": end.isoformat() + "Z"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Pay period created: {data['id']}")
        return data["id"]
    
    def test_get_pay_period_summary(self, admin_token):
        """Test getting pay period summary"""
        # First get a pay period
        periods = requests.get(
            f"{BASE_URL}/api/timeclock/pay-periods",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if periods.status_code != 200 or not periods.json():
            pytest.skip("No pay periods available")
        
        period_id = periods.json()[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/timeclock/pay-periods/{period_id}/summary",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Pay period summary: {len(data)} staff summaries")


class TestKioskMode:
    """Kiosk mode tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_list_kiosk_devices(self, admin_token):
        """Test listing kiosk devices"""
        response = requests.get(
            f"{BASE_URL}/api/scheduling/kiosk/devices",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List kiosk devices: {len(data)} devices found")
    
    def test_register_kiosk_device(self, admin_token):
        """Test registering a kiosk device"""
        response = requests.post(
            f"{BASE_URL}/api/scheduling/kiosk/devices",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "TEST_Front Desk Kiosk",
                "location_id": "main"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "device_code" in data
        print(f"✓ Kiosk device registered: {data['id']}")
        return data["device_code"]
    
    def test_kiosk_status_invalid_code(self):
        """Test kiosk status with invalid device code"""
        response = requests.get(
            f"{BASE_URL}/api/scheduling/kiosk/invalid-code-12345/status"
        )
        
        assert response.status_code == 404
        print("✓ Invalid kiosk code returns 404")
    
    def test_kiosk_clock_invalid_device(self):
        """Test kiosk clock with invalid device"""
        response = requests.post(
            f"{BASE_URL}/api/scheduling/kiosk/clock",
            json={
                "device_code": "invalid-code",
                "staff_pin": "1234",
                "action": "clock_in"
            }
        )
        
        assert response.status_code == 401
        print("✓ Invalid kiosk device returns 401")


class TestReports:
    """Reports tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_planned_vs_actual_report(self, admin_token):
        """Test planned vs actual hours report"""
        today = datetime.now()
        start = (today - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
        end = today.strftime("%Y-%m-%dT23:59:59Z")
        
        response = requests.get(
            f"{BASE_URL}/api/scheduling/reports/planned-vs-actual?start_date={start}&end_date={end}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Planned vs actual report: {len(data)} staff records")
    
    def test_discrepancy_report(self, admin_token):
        """Test discrepancy report"""
        today = datetime.now()
        start = (today - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
        end = today.strftime("%Y-%m-%dT23:59:59Z")
        
        response = requests.get(
            f"{BASE_URL}/api/scheduling/reports/discrepancies?start_date={start}&end_date={end}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_entries_with_discrepancies" in data
        print(f"✓ Discrepancy report: {data['total_entries_with_discrepancies']} entries with issues")


class TestAccessControl:
    """Access control tests"""
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Staff login failed")
    
    def test_staff_cannot_access_pay_periods(self, staff_token):
        """Test staff cannot access pay periods"""
        response = requests.get(
            f"{BASE_URL}/api/timeclock/pay-periods",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        assert response.status_code == 403
        print("✓ Staff denied pay periods access (403)")
    
    def test_staff_cannot_access_kiosk_devices(self, staff_token):
        """Test staff cannot access kiosk devices list"""
        response = requests.get(
            f"{BASE_URL}/api/scheduling/kiosk/devices",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        assert response.status_code == 403
        print("✓ Staff denied kiosk devices access (403)")
    
    def test_staff_cannot_access_reports(self, staff_token):
        """Test staff cannot access admin reports"""
        today = datetime.now()
        start = (today - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
        end = today.strftime("%Y-%m-%dT23:59:59Z")
        
        response = requests.get(
            f"{BASE_URL}/api/scheduling/reports/planned-vs-actual?start_date={start}&end_date={end}",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        assert response.status_code == 403
        print("✓ Staff denied reports access (403)")
    
    def test_unauthenticated_denied(self):
        """Test unauthenticated requests are denied"""
        response = requests.get(f"{BASE_URL}/api/timeclock/entries")
        
        assert response.status_code == 403
        print("✓ Unauthenticated request denied (403)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
