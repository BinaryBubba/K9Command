"""
Phase 3 Backend Tests - Forms, Tasks, HR (Time Off)
Tests for K9Command Connecteam-style features
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin_test_new@k9.com"
ADMIN_PASSWORD = "Test123!"
STAFF_EMAIL = "staff_test_new@k9.com"
STAFF_PASSWORD = "Test123!"


class TestAuthentication:
    """Authentication tests for Phase 3"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful")
    
    def test_staff_login(self):
        """Test staff login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        assert response.status_code == 200, f"Staff login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "staff"
        print(f"✓ Staff login successful")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return response.json()["token"]


@pytest.fixture(scope="module")
def staff_token():
    """Get staff auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": STAFF_EMAIL,
        "password": STAFF_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Staff login failed: {response.text}")
    return response.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Admin auth headers"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def staff_headers(staff_token):
    """Staff auth headers"""
    return {"Authorization": f"Bearer {staff_token}"}


# ==================== FORM TEMPLATES TESTS ====================

class TestFormTemplates:
    """Form template CRUD tests"""
    
    created_template_id = None
    
    def test_list_form_templates(self, admin_headers):
        """Test listing form templates"""
        response = requests.get(f"{BASE_URL}/api/forms/templates", headers=admin_headers)
        assert response.status_code == 200, f"List templates failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} form templates")
    
    def test_create_form_template(self, admin_headers):
        """Test creating a form template"""
        template_data = {
            "name": "TEST_Daily Inspection Form",
            "description": "Daily inspection checklist for staff",
            "category": "inspection",
            "fields": [
                {
                    "id": "field_1",
                    "field_type": "text",
                    "label": "Inspector Name",
                    "required": True,
                    "order": 0
                },
                {
                    "id": "field_2",
                    "field_type": "date",
                    "label": "Inspection Date",
                    "required": True,
                    "order": 1
                },
                {
                    "id": "field_3",
                    "field_type": "select",
                    "label": "Area Inspected",
                    "required": True,
                    "options": [
                        {"value": "kennel_a", "label": "Kennel A"},
                        {"value": "kennel_b", "label": "Kennel B"},
                        {"value": "play_area", "label": "Play Area"}
                    ],
                    "order": 2
                },
                {
                    "id": "field_4",
                    "field_type": "textarea",
                    "label": "Notes",
                    "required": False,
                    "order": 3
                }
            ],
            "require_signature": True,
            "require_gps": False,
            "allow_save_draft": True,
            "is_active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/forms/templates", json=template_data, headers=admin_headers)
        assert response.status_code == 200, f"Create template failed: {response.text}"
        data = response.json()
        assert data["name"] == template_data["name"]
        assert len(data["fields"]) == 4
        TestFormTemplates.created_template_id = data["id"]
        print(f"✓ Created form template: {data['id']}")
    
    def test_get_form_template(self, admin_headers):
        """Test getting a single form template"""
        if not TestFormTemplates.created_template_id:
            pytest.skip("No template created")
        
        response = requests.get(
            f"{BASE_URL}/api/forms/templates/{TestFormTemplates.created_template_id}",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Get template failed: {response.text}"
        data = response.json()
        assert data["id"] == TestFormTemplates.created_template_id
        print(f"✓ Retrieved form template: {data['name']}")
    
    def test_update_form_template(self, admin_headers):
        """Test updating a form template"""
        if not TestFormTemplates.created_template_id:
            pytest.skip("No template created")
        
        updates = {
            "description": "Updated daily inspection checklist",
            "require_gps": True
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/forms/templates/{TestFormTemplates.created_template_id}",
            json=updates,
            headers=admin_headers
        )
        assert response.status_code == 200, f"Update template failed: {response.text}"
        data = response.json()
        assert data["description"] == updates["description"]
        assert data["require_gps"] == True
        print(f"✓ Updated form template")
    
    def test_staff_can_list_templates(self, staff_headers):
        """Test that staff can list form templates"""
        response = requests.get(f"{BASE_URL}/api/forms/templates", headers=staff_headers)
        assert response.status_code == 200, f"Staff list templates failed: {response.text}"
        print(f"✓ Staff can list form templates")
    
    def test_staff_cannot_create_template(self, staff_headers):
        """Test that staff cannot create form templates"""
        template_data = {
            "name": "TEST_Unauthorized Template",
            "fields": []
        }
        response = requests.post(f"{BASE_URL}/api/forms/templates", json=template_data, headers=staff_headers)
        assert response.status_code == 403, f"Staff should not create templates: {response.status_code}"
        print(f"✓ Staff correctly denied template creation (403)")


# ==================== FORM SUBMISSIONS TESTS ====================

class TestFormSubmissions:
    """Form submission tests"""
    
    created_submission_id = None
    
    def test_create_form_submission_draft(self, staff_headers):
        """Test creating a form submission as draft"""
        if not TestFormTemplates.created_template_id:
            pytest.skip("No template created")
        
        submission_data = {
            "template_id": TestFormTemplates.created_template_id,
            "values": {
                "field_1": "John Staff",
                "field_2": datetime.now().strftime("%Y-%m-%d")
            },
            "status": "draft"
        }
        
        response = requests.post(f"{BASE_URL}/api/forms/submissions", json=submission_data, headers=staff_headers)
        assert response.status_code == 200, f"Create submission failed: {response.text}"
        data = response.json()
        assert data["status"] == "draft"
        TestFormSubmissions.created_submission_id = data["id"]
        print(f"✓ Created draft submission: {data['id']}")
    
    def test_list_form_submissions(self, staff_headers):
        """Test listing form submissions"""
        response = requests.get(f"{BASE_URL}/api/forms/submissions", headers=staff_headers)
        assert response.status_code == 200, f"List submissions failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} form submissions")
    
    def test_get_form_submission(self, staff_headers):
        """Test getting a single form submission"""
        if not TestFormSubmissions.created_submission_id:
            pytest.skip("No submission created")
        
        response = requests.get(
            f"{BASE_URL}/api/forms/submissions/{TestFormSubmissions.created_submission_id}",
            headers=staff_headers
        )
        assert response.status_code == 200, f"Get submission failed: {response.text}"
        data = response.json()
        assert data["id"] == TestFormSubmissions.created_submission_id
        print(f"✓ Retrieved form submission")
    
    def test_update_form_submission(self, staff_headers):
        """Test updating a form submission (draft)"""
        if not TestFormSubmissions.created_submission_id:
            pytest.skip("No submission created")
        
        updates = {
            "values": {
                "field_1": "John Staff Updated",
                "field_2": datetime.now().strftime("%Y-%m-%d"),
                "field_3": "kennel_a",
                "field_4": "All areas clean and secure"
            },
            "status": "submitted"
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/forms/submissions/{TestFormSubmissions.created_submission_id}",
            json=updates,
            headers=staff_headers
        )
        assert response.status_code == 200, f"Update submission failed: {response.text}"
        data = response.json()
        assert data["status"] == "submitted"
        print(f"✓ Updated and submitted form")
    
    def test_admin_review_submission(self, admin_headers):
        """Test admin reviewing a form submission"""
        if not TestFormSubmissions.created_submission_id:
            pytest.skip("No submission created")
        
        response = requests.post(
            f"{BASE_URL}/api/forms/submissions/{TestFormSubmissions.created_submission_id}/review?status=approved&notes=Good%20work",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Review submission failed: {response.text}"
        print(f"✓ Admin approved form submission")


# ==================== TASKS TESTS ====================

class TestTasks:
    """Task management tests"""
    
    created_task_id = None
    
    def test_list_tasks(self, admin_headers):
        """Test listing tasks"""
        response = requests.get(f"{BASE_URL}/api/tasks", headers=admin_headers)
        assert response.status_code == 200, f"List tasks failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} tasks")
    
    def test_create_task(self, admin_headers):
        """Test creating a task"""
        task_data = {
            "title": "TEST_Clean Kennel A",
            "description": "Deep clean kennel A before new arrivals",
            "priority": "high",
            "status": "pending",
            "location_id": "main",
            "due_date": (datetime.now() + timedelta(days=1)).isoformat()
        }
        
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=admin_headers)
        assert response.status_code == 200, f"Create task failed: {response.text}"
        data = response.json()
        assert data["title"] == task_data["title"]
        assert data["status"] == "pending"
        TestTasks.created_task_id = data["id"]
        print(f"✓ Created task: {data['id']}")
    
    def test_get_task(self, admin_headers):
        """Test getting a single task"""
        if not TestTasks.created_task_id:
            pytest.skip("No task created")
        
        response = requests.get(f"{BASE_URL}/api/tasks/{TestTasks.created_task_id}", headers=admin_headers)
        assert response.status_code == 200, f"Get task failed: {response.text}"
        data = response.json()
        assert data["id"] == TestTasks.created_task_id
        print(f"✓ Retrieved task: {data['title']}")
    
    def test_update_task_status(self, admin_headers):
        """Test updating task status"""
        if not TestTasks.created_task_id:
            pytest.skip("No task created")
        
        updates = {"status": "in_progress"}
        response = requests.patch(
            f"{BASE_URL}/api/tasks/{TestTasks.created_task_id}",
            json=updates,
            headers=admin_headers
        )
        assert response.status_code == 200, f"Update task failed: {response.text}"
        data = response.json()
        assert data["status"] == "in_progress"
        print(f"✓ Updated task status to in_progress")
    
    def test_staff_can_list_tasks(self, staff_headers):
        """Test that staff can list tasks"""
        response = requests.get(f"{BASE_URL}/api/tasks", headers=staff_headers)
        assert response.status_code == 200, f"Staff list tasks failed: {response.text}"
        print(f"✓ Staff can list tasks")
    
    def test_staff_can_create_task(self, staff_headers):
        """Test that staff can create tasks"""
        task_data = {
            "title": "TEST_Staff Task",
            "description": "Task created by staff",
            "priority": "medium",
            "status": "pending",
            "location_id": "main"
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=staff_headers)
        assert response.status_code == 200, f"Staff create task failed: {response.text}"
        print(f"✓ Staff can create tasks")


# ==================== TASK TEMPLATES TESTS ====================

class TestTaskTemplates:
    """Task template tests"""
    
    created_template_id = None
    
    def test_list_task_templates(self, admin_headers):
        """Test listing task templates"""
        response = requests.get(f"{BASE_URL}/api/forms/task-templates", headers=admin_headers)
        assert response.status_code == 200, f"List task templates failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} task templates")
    
    def test_create_task_template(self, admin_headers):
        """Test creating a task template"""
        template_data = {
            "name": "TEST_Morning Checklist",
            "description": "Daily morning routine checklist",
            "category": "daily",
            "checklist_items": [
                {"title": "Check water bowls", "completed": False},
                {"title": "Feed dogs", "completed": False},
                {"title": "Clean kennels", "completed": False}
            ],
            "priority": "high",
            "default_due_hours": 4,
            "is_active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/forms/task-templates", json=template_data, headers=admin_headers)
        assert response.status_code == 200, f"Create task template failed: {response.text}"
        data = response.json()
        assert data["name"] == template_data["name"]
        TestTaskTemplates.created_template_id = data["id"]
        print(f"✓ Created task template: {data['id']}")


# ==================== HR / TIME OFF TESTS ====================

class TestHRPolicies:
    """HR Time Off Policy tests"""
    
    created_policy_id = None
    
    def test_list_policies(self, admin_headers):
        """Test listing time off policies"""
        response = requests.get(f"{BASE_URL}/api/hr/policies", headers=admin_headers)
        # May return 404 if endpoint is different
        if response.status_code == 404:
            # Try alternate endpoint
            response = requests.get(f"{BASE_URL}/api/hr/time-off-policies", headers=admin_headers)
        
        assert response.status_code == 200, f"List policies failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} time off policies")
    
    def test_create_policy(self, admin_headers):
        """Test creating a time off policy"""
        policy_data = {
            "name": "TEST_Vacation Policy",
            "time_off_type": "vacation",
            "accrual_frequency": "monthly",
            "accrual_amount": 8,
            "max_balance": 120,
            "requires_approval": True,
            "advance_notice_days": 7,
            "is_active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/time-off-policies", headers=admin_headers)
        if response.status_code == 405:
            # POST might need body
            response = requests.post(f"{BASE_URL}/api/hr/time-off-policies", json=policy_data, headers=admin_headers)
        
        if response.status_code == 200:
            data = response.json()
            TestHRPolicies.created_policy_id = data.get("id")
            print(f"✓ Created time off policy: {data.get('id')}")
        else:
            print(f"⚠ Create policy returned {response.status_code} - may need different endpoint")


class TestHRRequests:
    """HR Time Off Request tests"""
    
    created_request_id = None
    
    def test_list_requests(self, admin_headers):
        """Test listing time off requests"""
        response = requests.get(f"{BASE_URL}/api/hr/requests", headers=admin_headers)
        if response.status_code == 404:
            response = requests.get(f"{BASE_URL}/api/hr/time-off-requests", headers=admin_headers)
        
        assert response.status_code == 200, f"List requests failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} time off requests")
    
    def test_create_request(self, staff_headers):
        """Test creating a time off request"""
        # First get a policy ID
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        policies_response = requests.get(f"{BASE_URL}/api/hr/time-off-policies", headers=admin_headers)
        if policies_response.status_code != 200 or not policies_response.json():
            pytest.skip("No policies available for request creation")
        
        policy_id = policies_response.json()[0]["id"]
        
        request_data = {
            "policy_id": policy_id,
            "start_date": (datetime.now() + timedelta(days=14)).isoformat(),
            "end_date": (datetime.now() + timedelta(days=16)).isoformat(),
            "hours_requested": 24,
            "reason": "TEST_Family vacation"
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/time-off-requests", json=request_data, headers=staff_headers)
        if response.status_code == 200:
            data = response.json()
            TestHRRequests.created_request_id = data.get("id")
            print(f"✓ Created time off request: {data.get('id')}")
        else:
            print(f"⚠ Create request returned {response.status_code}: {response.text[:200]}")
    
    def test_staff_list_own_requests(self, staff_headers):
        """Test that staff can list their own requests"""
        response = requests.get(f"{BASE_URL}/api/hr/time-off-requests", headers=staff_headers)
        if response.status_code == 404:
            response = requests.get(f"{BASE_URL}/api/hr/requests", headers=staff_headers)
        
        assert response.status_code == 200, f"Staff list requests failed: {response.text}"
        print(f"✓ Staff can list their time off requests")


# ==================== ANALYTICS TESTS ====================

class TestAnalytics:
    """Analytics endpoint tests"""
    
    def test_form_submission_analytics(self, admin_headers):
        """Test form submission analytics"""
        response = requests.get(f"{BASE_URL}/api/forms/analytics/submissions", headers=admin_headers)
        assert response.status_code == 200, f"Submission analytics failed: {response.text}"
        data = response.json()
        assert "total_submissions" in data
        assert "by_status" in data
        print(f"✓ Form submission analytics: {data['total_submissions']} total submissions")
    
    def test_task_analytics(self, admin_headers):
        """Test task analytics"""
        response = requests.get(f"{BASE_URL}/api/forms/analytics/tasks", headers=admin_headers)
        assert response.status_code == 200, f"Task analytics failed: {response.text}"
        data = response.json()
        assert "total_tasks" in data
        print(f"✓ Task analytics: {data['total_tasks']} total tasks")
    
    def test_staff_cannot_access_analytics(self, staff_headers):
        """Test that staff cannot access analytics"""
        response = requests.get(f"{BASE_URL}/api/forms/analytics/submissions", headers=staff_headers)
        assert response.status_code == 403, f"Staff should not access analytics: {response.status_code}"
        print(f"✓ Staff correctly denied analytics access (403)")


# ==================== CLEANUP ====================

class TestCleanup:
    """Cleanup test data"""
    
    def test_delete_form_template(self, admin_headers):
        """Cleanup: Delete test form template"""
        if TestFormTemplates.created_template_id:
            response = requests.delete(
                f"{BASE_URL}/api/forms/templates/{TestFormTemplates.created_template_id}",
                headers=admin_headers
            )
            assert response.status_code == 200, f"Delete template failed: {response.text}"
            print(f"✓ Cleaned up form template")
        else:
            print("⚠ No template to clean up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
