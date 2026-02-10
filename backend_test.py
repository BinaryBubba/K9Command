#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class KennelAPITester:
    def __init__(self, base_url="https://petbiz-system.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}  # Store tokens for different roles
        self.users = {}   # Store user data for different roles
        self.test_data = {}  # Store created test data
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None, 
                 role: Optional[str] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        # Add authorization if role specified
        if role and role in self.tokens:
            test_headers['Authorization'] = f'Bearer {self.tokens[role]}'
        elif headers:
            test_headers.update(headers)

        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    'test': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:200]
                })

            try:
                return success, response.json() if response.text else {}
            except:
                return success, {'raw_response': response.text}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}", "ERROR")
            self.failed_tests.append({
                'test': name,
                'error': str(e)
            })
            return False, {}

    def test_user_registration_and_login(self):
        """Test user registration and login for all roles"""
        self.log("=== Testing User Authentication ===")
        
        roles = ['customer', 'staff', 'admin']
        timestamp = datetime.now().strftime("%H%M%S")
        
        for role in roles:
            # Register user
            user_data = {
                "email": f"test_{role}_{timestamp}@example.com",
                "password": "TestPass123!",
                "full_name": f"Test {role.title()} User",
                "phone": "+1234567890",
                "role": role
            }
            
            success, response = self.run_test(
                f"Register {role}",
                "POST",
                "auth/register",
                200,
                data=user_data
            )
            
            if success and 'token' in response:
                self.tokens[role] = response['token']
                self.users[role] = response['user']
                self.log(f"✅ {role} registered and token stored")
            else:
                self.log(f"❌ Failed to register {role}", "ERROR")
                return False
                
            # Test login
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            
            success, response = self.run_test(
                f"Login {role}",
                "POST",
                "auth/login",
                200,
                data=login_data
            )
            
            if success and 'token' in response:
                self.log(f"✅ {role} login successful")
            else:
                self.log(f"❌ Failed to login {role}", "ERROR")
        
        return True

    def test_auth_me_endpoint(self):
        """Test /auth/me endpoint for all roles"""
        self.log("=== Testing Auth Me Endpoint ===")
        
        for role in ['customer', 'staff', 'admin']:
            if role in self.tokens:
                success, response = self.run_test(
                    f"Get current user ({role})",
                    "GET",
                    "auth/me",
                    200,
                    role=role
                )
                
                if success and response.get('email'):
                    self.log(f"✅ {role} /auth/me working")
                else:
                    self.log(f"❌ {role} /auth/me failed", "ERROR")

    def test_dashboard_stats(self):
        """Test dashboard stats for all roles"""
        self.log("=== Testing Dashboard Stats ===")
        
        for role in ['customer', 'staff', 'admin']:
            if role in self.tokens:
                success, response = self.run_test(
                    f"Dashboard stats ({role})",
                    "GET",
                    "dashboard/stats",
                    200,
                    role=role
                )
                
                if success:
                    self.log(f"✅ {role} dashboard stats: {response}")
                else:
                    self.log(f"❌ {role} dashboard stats failed", "ERROR")

    def test_dog_management(self):
        """Test dog CRUD operations"""
        self.log("=== Testing Dog Management ===")
        
        if 'customer' not in self.tokens:
            self.log("❌ No customer token available for dog tests", "ERROR")
            return
        
        # Create a dog
        dog_data = {
            "name": "Buddy Test",
            "breed": "Golden Retriever",
            "age": 3,
            "weight": 30.5,
            "behavioral_notes": "Friendly and energetic",
            "diet_requirements": "Regular kibble"
        }
        
        success, response = self.run_test(
            "Create dog",
            "POST",
            "dogs",
            200,
            data=dog_data,
            role='customer'
        )
        
        if success and 'id' in response:
            dog_id = response['id']
            self.test_data['dog_id'] = dog_id
            self.log(f"✅ Dog created with ID: {dog_id}")
            
            # Get all dogs
            success, response = self.run_test(
                "Get all dogs",
                "GET",
                "dogs",
                200,
                role='customer'
            )
            
            if success and isinstance(response, list):
                self.log(f"✅ Retrieved {len(response)} dogs")
            
            # Get specific dog
            success, response = self.run_test(
                "Get specific dog",
                "GET",
                f"dogs/{dog_id}",
                200,
                role='customer'
            )
            
            if success and response.get('name') == dog_data['name']:
                self.log(f"✅ Retrieved specific dog: {response['name']}")
        else:
            self.log("❌ Failed to create dog", "ERROR")

    def test_booking_system(self):
        """Test booking creation and management"""
        self.log("=== Testing Booking System ===")
        
        if 'customer' not in self.tokens or 'dog_id' not in self.test_data:
            self.log("❌ Prerequisites not met for booking tests", "ERROR")
            return
        
        # Create a booking
        check_in = datetime.now() + timedelta(days=1)
        check_out = datetime.now() + timedelta(days=3)
        
        booking_data = {
            "dog_ids": [self.test_data['dog_id']],
            "location_id": "test-location-1",
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "notes": "Test booking for API testing"
        }
        
        success, response = self.run_test(
            "Create booking",
            "POST",
            "bookings",
            200,
            data=booking_data,
            role='customer'
        )
        
        if success and 'id' in response:
            booking_id = response['id']
            self.test_data['booking_id'] = booking_id
            self.log(f"✅ Booking created with ID: {booking_id}")
            self.log(f"   Total price: ${response.get('total_price', 0)}")
            
            # Get all bookings
            success, response = self.run_test(
                "Get all bookings",
                "GET",
                "bookings",
                200,
                role='customer'
            )
            
            if success and isinstance(response, list):
                self.log(f"✅ Retrieved {len(response)} bookings")
        else:
            self.log("❌ Failed to create booking", "ERROR")

    def test_staff_functionality(self):
        """Test staff-specific functionality"""
        self.log("=== Testing Staff Functionality ===")
        
        if 'staff' not in self.tokens:
            self.log("❌ No staff token available", "ERROR")
            return
        
        # Test clock in
        clock_in_data = {
            "staff_id": self.users['staff']['id'],
            "location_id": "test-location-1"
        }
        
        success, response = self.run_test(
            "Staff clock in",
            "POST",
            "time-entries/clock-in",
            200,
            data=clock_in_data,
            role='staff'
        )
        
        if success:
            self.log("✅ Staff clocked in successfully")
            
            # Test clock out
            success, response = self.run_test(
                "Staff clock out",
                "POST",
                "time-entries/clock-out",
                200,
                role='staff'
            )
            
            if success:
                self.log("✅ Staff clocked out successfully")
        
        # Test task creation
        task_data = {
            "title": "Test Task",
            "description": "This is a test task for API testing",
            "location_id": "test-location-1",
            "due_date": (datetime.now() + timedelta(hours=2)).isoformat()
        }
        
        success, response = self.run_test(
            "Create task",
            "POST",
            "tasks",
            200,
            data=task_data,
            role='staff'
        )
        
        if success and 'id' in response:
            task_id = response['id']
            self.log(f"✅ Task created with ID: {task_id}")
            
            # Get all tasks
            success, response = self.run_test(
                "Get all tasks",
                "GET",
                "tasks",
                200,
                role='staff'
            )
            
            if success and isinstance(response, list):
                self.log(f"✅ Retrieved {len(response)} tasks")
            
            # Complete task
            success, response = self.run_test(
                "Complete task",
                "PATCH",
                f"tasks/{task_id}/complete",
                200,
                role='staff'
            )
            
            if success:
                self.log("✅ Task completed successfully")

    def test_daily_updates(self):
        """Test daily update creation and AI summary generation"""
        self.log("=== Testing Daily Updates ===")
        
        if 'staff' not in self.tokens or 'booking_id' not in self.test_data:
            self.log("❌ Prerequisites not met for daily update tests", "ERROR")
            return
        
        # Create daily update
        update_data = {
            "household_id": self.users['customer']['household_id'],
            "booking_id": self.test_data['booking_id'],
            "staff_notes": "Buddy had a great day playing in the yard and made friends with other dogs!"
        }
        
        success, response = self.run_test(
            "Create daily update",
            "POST",
            "daily-updates",
            200,
            data=update_data,
            role='staff'
        )
        
        if success and 'id' in response:
            update_id = response['id']
            self.log(f"✅ Daily update created with ID: {update_id}")
            
            # Test AI summary generation
            success, response = self.run_test(
                "Generate AI summary",
                "POST",
                f"daily-updates/{update_id}/generate-summary",
                200,
                role='staff'
            )
            
            if success and 'summary' in response:
                self.log(f"✅ AI summary generated: {response['summary'][:100]}...")
            else:
                self.log("⚠️  AI summary generation may have failed - check GPT-5.2 API key")
            
            # Get all daily updates
            success, response = self.run_test(
                "Get daily updates",
                "GET",
                "daily-updates",
                200,
                role='customer'
            )
            
            if success and isinstance(response, list):
                self.log(f"✅ Retrieved {len(response)} daily updates")

    def test_admin_functionality(self):
        """Test admin-specific functionality"""
        self.log("=== Testing Admin Functionality ===")
        
        if 'admin' not in self.tokens:
            self.log("❌ No admin token available", "ERROR")
            return
        
        # Test audit logs
        success, response = self.run_test(
            "Get audit logs",
            "GET",
            "audit-logs",
            200,
            role='admin'
        )
        
        if success and isinstance(response, list):
            self.log(f"✅ Retrieved {len(response)} audit log entries")
        
        # Test incident creation
        incident_data = {
            "title": "Test Incident",
            "description": "This is a test incident for API testing",
            "severity": "low",
            "location_id": "test-location-1"
        }
        
        success, response = self.run_test(
            "Create incident",
            "POST",
            "incidents",
            200,
            data=incident_data,
            role='admin'
        )
        
        if success and 'id' in response:
            self.log(f"✅ Incident created with ID: {response['id']}")
            
            # Get all incidents
            success, response = self.run_test(
                "Get incidents",
                "GET",
                "incidents",
                200,
                role='admin'
            )
            
            if success and isinstance(response, list):
                self.log(f"✅ Retrieved {len(response)} incidents")

    def test_role_based_access_control(self):
        """Test that role-based access control is working"""
        self.log("=== Testing Role-Based Access Control ===")
        
        # Customer should not be able to access admin endpoints
        success, response = self.run_test(
            "Customer accessing audit logs (should fail)",
            "GET",
            "audit-logs",
            403,
            role='customer'
        )
        
        if success:
            self.log("✅ RBAC working - customer blocked from audit logs")
        
        # Staff should not be able to create dogs
        dog_data = {
            "name": "Unauthorized Dog",
            "breed": "Test Breed"
        }
        
        success, response = self.run_test(
            "Staff creating dog (should fail)",
            "POST",
            "dogs",
            403,
            data=dog_data,
            role='staff'
        )
        
        if success:
            self.log("✅ RBAC working - staff blocked from creating dogs")

    def run_all_tests(self):
        """Run all test suites"""
        self.log("🚀 Starting Kennel Operations API Tests")
        self.log(f"Testing against: {self.base_url}")
        
        try:
            # Core authentication tests
            if not self.test_user_registration_and_login():
                self.log("❌ Authentication tests failed - stopping", "ERROR")
                return False
            
            self.test_auth_me_endpoint()
            self.test_dashboard_stats()
            
            # Feature tests
            self.test_dog_management()
            self.test_booking_system()
            self.test_staff_functionality()
            self.test_daily_updates()
            self.test_admin_functionality()
            
            # Security tests
            self.test_role_based_access_control()
            
        except Exception as e:
            self.log(f"❌ Unexpected error during testing: {str(e)}", "ERROR")
            return False
        
        # Print summary
        self.log("=" * 50)
        self.log(f"📊 Test Summary:")
        self.log(f"   Tests Run: {self.tests_run}")
        self.log(f"   Tests Passed: {self.tests_passed}")
        self.log(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        self.log(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ Failed Tests:")
            for failure in self.failed_tests:
                self.log(f"   - {failure.get('test', 'Unknown')}: {failure}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = KennelAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())