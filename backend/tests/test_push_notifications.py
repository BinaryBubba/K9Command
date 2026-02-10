"""
Push Notifications API Tests
Tests for Web Push API and Firebase Cloud Messaging endpoints
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPushNotificationEndpoints:
    """Test push notification API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@test.com"
        self.admin_password = "Test123!"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def get_auth_headers(self, token):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {token}"}
    
    # ==================== VAPID KEY ENDPOINT ====================
    
    def test_vapid_key_endpoint_returns_key(self):
        """Test GET /api/moego/push/vapid-key returns VAPID public key"""
        response = self.session.get(f"{BASE_URL}/api/moego/push/vapid-key")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "vapid_public_key" in data, "Response should contain vapid_public_key"
        assert isinstance(data["vapid_public_key"], str), "VAPID key should be a string"
        assert len(data["vapid_public_key"]) > 0, "VAPID key should not be empty"
        print(f"✓ VAPID key endpoint returns key: {data['vapid_public_key'][:20]}...")
    
    def test_vapid_key_no_auth_required(self):
        """Test VAPID key endpoint doesn't require authentication"""
        # Make request without any auth headers
        response = requests.get(f"{BASE_URL}/api/moego/push/vapid-key")
        
        assert response.status_code == 200, "VAPID key endpoint should be public"
        print("✓ VAPID key endpoint is publicly accessible (no auth required)")
    
    # ==================== WEB PUSH SUBSCRIBE ====================
    
    def test_web_push_subscribe_success(self):
        """Test POST /api/moego/push/subscribe/web accepts valid subscription"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        # Create a mock Web Push subscription
        subscription_data = {
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/test-{uuid.uuid4()}",
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                }
            },
            "device_info": {
                "userAgent": "Mozilla/5.0 Test Agent",
                "platform": "Test Platform",
                "language": "en-US"
            }
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/moego/push/subscribe/web",
            json=subscription_data,
            headers=self.get_auth_headers(token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        assert "subscription_id" in data, "Response should contain subscription_id"
        assert data["message"] == "Subscribed to Web Push notifications"
        print(f"✓ Web Push subscribe successful, subscription_id: {data['subscription_id']}")
        
        return data["subscription_id"]
    
    def test_web_push_subscribe_invalid_data(self):
        """Test Web Push subscribe rejects invalid subscription data"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        # Missing endpoint
        invalid_data = {
            "subscription": {
                "keys": {"p256dh": "test", "auth": "test"}
            }
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/moego/push/subscribe/web",
            json=invalid_data,
            headers=self.get_auth_headers(token)
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid data, got {response.status_code}"
        print("✓ Web Push subscribe correctly rejects invalid data")
    
    def test_web_push_subscribe_requires_auth(self):
        """Test Web Push subscribe requires authentication"""
        subscription_data = {
            "subscription": {
                "endpoint": "https://test.endpoint.com",
                "keys": {"p256dh": "test", "auth": "test"}
            }
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/moego/push/subscribe/web",
            json=subscription_data
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Web Push subscribe requires authentication")
    
    # ==================== FCM SUBSCRIBE ====================
    
    def test_fcm_subscribe_success(self):
        """Test POST /api/moego/push/subscribe/fcm accepts valid FCM token"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        fcm_data = {
            "fcm_token": f"test-fcm-token-{uuid.uuid4()}",
            "device_info": {
                "device_type": "android",
                "app_version": "1.0.0"
            }
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/moego/push/subscribe/fcm",
            json=fcm_data,
            headers=self.get_auth_headers(token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        assert "subscription_id" in data, "Response should contain subscription_id"
        assert data["message"] == "Subscribed to FCM notifications"
        print(f"✓ FCM subscribe successful, subscription_id: {data['subscription_id']}")
        
        return data["subscription_id"]
    
    def test_fcm_subscribe_missing_token(self):
        """Test FCM subscribe rejects missing token"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.post(
            f"{BASE_URL}/api/moego/push/subscribe/fcm",
            json={"device_info": {}},
            headers=self.get_auth_headers(token)
        )
        
        assert response.status_code == 400, f"Expected 400 for missing token, got {response.status_code}"
        print("✓ FCM subscribe correctly rejects missing token")
    
    # ==================== GET SUBSCRIPTIONS ====================
    
    def test_get_subscriptions_returns_user_subscriptions(self):
        """Test GET /api/moego/push/subscriptions returns user's subscriptions"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        # First create a subscription
        subscription_data = {
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/get-test-{uuid.uuid4()}",
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                }
            }
        }
        
        self.session.post(
            f"{BASE_URL}/api/moego/push/subscribe/web",
            json=subscription_data,
            headers=self.get_auth_headers(token)
        )
        
        # Now get subscriptions
        response = self.session.get(
            f"{BASE_URL}/api/moego/push/subscriptions",
            headers=self.get_auth_headers(token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Get subscriptions returns {len(data)} subscription(s)")
        
        if len(data) > 0:
            sub = data[0]
            assert "id" in sub, "Subscription should have id"
            assert "user_id" in sub, "Subscription should have user_id"
            assert "subscription_type" in sub, "Subscription should have subscription_type"
            assert "is_active" in sub, "Subscription should have is_active"
            print(f"  - Subscription type: {sub['subscription_type']}, active: {sub['is_active']}")
    
    def test_get_subscriptions_requires_auth(self):
        """Test get subscriptions requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/moego/push/subscriptions")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Get subscriptions requires authentication")
    
    # ==================== UNSUBSCRIBE ====================
    
    def test_unsubscribe_success(self):
        """Test DELETE /api/moego/push/unsubscribe/{id} removes subscription"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        # First create a subscription
        subscription_data = {
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/unsub-test-{uuid.uuid4()}",
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                }
            }
        }
        
        create_response = self.session.post(
            f"{BASE_URL}/api/moego/push/subscribe/web",
            json=subscription_data,
            headers=self.get_auth_headers(token)
        )
        
        assert create_response.status_code == 200
        subscription_id = create_response.json()["subscription_id"]
        
        # Now unsubscribe
        response = self.session.delete(
            f"{BASE_URL}/api/moego/push/unsubscribe/{subscription_id}",
            headers=self.get_auth_headers(token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert data["message"] == "Unsubscribed from push notifications"
        print(f"✓ Unsubscribe successful for subscription {subscription_id}")
    
    def test_unsubscribe_invalid_id(self):
        """Test unsubscribe with invalid subscription ID"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.delete(
            f"{BASE_URL}/api/moego/push/unsubscribe/invalid-id-12345",
            headers=self.get_auth_headers(token)
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid ID, got {response.status_code}"
        print("✓ Unsubscribe correctly returns 404 for invalid ID")
    
    # ==================== TEST PUSH ====================
    
    def test_push_test_endpoint(self):
        """Test POST /api/moego/push/test sends test notification"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.post(
            f"{BASE_URL}/api/moego/push/test",
            headers=self.get_auth_headers(token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        assert "results" in data, "Response should contain results"
        
        results = data["results"]
        assert "web_push_sent" in results
        assert "web_push_failed" in results
        assert "fcm_sent" in results
        assert "fcm_failed" in results
        
        print(f"✓ Test push endpoint works: {data['message']}")
        print(f"  - Web Push sent: {results['web_push_sent']}, failed: {results['web_push_failed']}")
        print(f"  - FCM sent: {results['fcm_sent']}, failed: {results['fcm_failed']}")
    
    def test_push_test_requires_auth(self):
        """Test push test endpoint requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/moego/push/test")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Test push endpoint requires authentication")


class TestPushNotificationIntegration:
    """Test push notification integration with booking flows"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@test.com"
        self.admin_password = "Test123!"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def get_auth_headers(self, token):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {token}"}
    
    def test_push_subscription_flow(self):
        """Test complete push subscription flow: subscribe -> get -> unsubscribe"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        headers = self.get_auth_headers(token)
        
        # 1. Subscribe
        subscription_data = {
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/flow-test-{uuid.uuid4()}",
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                }
            }
        }
        
        sub_response = self.session.post(
            f"{BASE_URL}/api/moego/push/subscribe/web",
            json=subscription_data,
            headers=headers
        )
        assert sub_response.status_code == 200
        subscription_id = sub_response.json()["subscription_id"]
        print(f"✓ Step 1: Subscribed with ID {subscription_id}")
        
        # 2. Get subscriptions - verify it exists
        get_response = self.session.get(
            f"{BASE_URL}/api/moego/push/subscriptions",
            headers=headers
        )
        assert get_response.status_code == 200
        subscriptions = get_response.json()
        found = any(s["id"] == subscription_id for s in subscriptions)
        assert found, "Subscription should be in list"
        print(f"✓ Step 2: Verified subscription exists in list")
        
        # 3. Send test notification
        test_response = self.session.post(
            f"{BASE_URL}/api/moego/push/test",
            headers=headers
        )
        assert test_response.status_code == 200
        print(f"✓ Step 3: Test notification sent")
        
        # 4. Unsubscribe
        unsub_response = self.session.delete(
            f"{BASE_URL}/api/moego/push/unsubscribe/{subscription_id}",
            headers=headers
        )
        assert unsub_response.status_code == 200
        print(f"✓ Step 4: Unsubscribed successfully")
        
        print("✓ Complete push subscription flow passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
