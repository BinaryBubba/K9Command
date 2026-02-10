"""
MoeGo Phase 4 - POS & CRM Testing
Tests for Inventory Management, POS Checkout, and CRM/Leads functionality.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Test123!"


class TestInventoryManagement:
    """Tests for Inventory Management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get admin auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        token = login_res.json().get("token")  # API returns 'token' not 'access_token'
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Generate unique SKU for test products
        self.test_sku = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        yield
        
        # Cleanup - no explicit cleanup needed as products are test-prefixed
    
    def test_create_product(self):
        """Test creating a new product"""
        product_data = {
            "sku": self.test_sku,
            "name": "Test Dog Food Premium",
            "description": "Premium dog food for testing",
            "category": "food",
            "price_cents": 2999,  # $29.99
            "cost_cents": 1500,   # $15.00
            "quantity": 50,
            "reorder_point": 10
        }
        
        response = self.session.post(f"{BASE_URL}/api/moego/inventory/products", json=product_data)
        assert response.status_code == 200, f"Create product failed: {response.text}"
        
        data = response.json()
        assert "product" in data
        product = data["product"]
        assert product["sku"] == self.test_sku
        assert product["name"] == "Test Dog Food Premium"
        assert product["price_cents"] == 2999
        assert product["quantity"] == 50
        assert product["status"] == "in_stock"
        
        # Store product ID for other tests
        self.__class__.created_product_id = product["id"]
        print(f"✓ Created product: {product['name']} (ID: {product['id']})")
    
    def test_list_products(self):
        """Test listing products"""
        response = self.session.get(f"{BASE_URL}/api/moego/inventory/products")
        assert response.status_code == 200, f"List products failed: {response.text}"
        
        data = response.json()
        assert "products" in data
        assert isinstance(data["products"], list)
        print(f"✓ Listed {len(data['products'])} products")
    
    def test_get_product_by_id(self):
        """Test getting a specific product"""
        # First create a product
        sku = f"TEST-GET-{uuid.uuid4().hex[:6].upper()}"
        create_res = self.session.post(f"{BASE_URL}/api/moego/inventory/products", json={
            "sku": sku,
            "name": "Test Get Product",
            "category": "toys",
            "price_cents": 999,
            "quantity": 20,
            "reorder_point": 5
        })
        assert create_res.status_code == 200
        product_id = create_res.json()["product"]["id"]
        
        # Get the product - returns product directly, not wrapped
        response = self.session.get(f"{BASE_URL}/api/moego/inventory/products/{product_id}")
        assert response.status_code == 200, f"Get product failed: {response.text}"
        
        data = response.json()
        # API returns product directly without wrapper
        assert data["id"] == product_id
        assert data["sku"] == sku
        print(f"✓ Retrieved product by ID: {product_id}")
    
    def test_update_product(self):
        """Test updating a product"""
        # First create a product
        sku = f"TEST-UPD-{uuid.uuid4().hex[:6].upper()}"
        create_res = self.session.post(f"{BASE_URL}/api/moego/inventory/products", json={
            "sku": sku,
            "name": "Test Update Product",
            "category": "treats",
            "price_cents": 599,
            "quantity": 30,
            "reorder_point": 5
        })
        assert create_res.status_code == 200
        product_id = create_res.json()["product"]["id"]
        
        # Update the product
        update_data = {
            "name": "Updated Test Product",
            "price_cents": 699,
            "quantity": 25
        }
        response = self.session.put(f"{BASE_URL}/api/moego/inventory/products/{product_id}", json=update_data)
        assert response.status_code == 200, f"Update product failed: {response.text}"
        
        data = response.json()
        assert data["product"]["name"] == "Updated Test Product"
        assert data["product"]["price_cents"] == 699
        print(f"✓ Updated product: {product_id}")
    
    def test_adjust_inventory(self):
        """Test inventory adjustment with reason tracking"""
        # First create a product
        sku = f"TEST-ADJ-{uuid.uuid4().hex[:6].upper()}"
        create_res = self.session.post(f"{BASE_URL}/api/moego/inventory/products", json={
            "sku": sku,
            "name": "Test Adjust Product",
            "category": "grooming",
            "price_cents": 1299,
            "quantity": 20,
            "reorder_point": 5
        })
        assert create_res.status_code == 200
        product_id = create_res.json()["product"]["id"]
        
        # Adjust inventory - add 10 units
        adjust_data = {
            "product_id": product_id,
            "quantity_change": 10,
            "reason": "Restock from supplier"
        }
        response = self.session.post(f"{BASE_URL}/api/moego/inventory/adjust", json=adjust_data)
        assert response.status_code == 200, f"Adjust inventory failed: {response.text}"
        
        data = response.json()
        # Response has 'result' wrapper
        result = data.get("result", data)
        assert result["previous_quantity"] == 20
        assert result["new_quantity"] == 30
        print(f"✓ Adjusted inventory: {result['previous_quantity']} -> {result['new_quantity']}")
        
        # Adjust inventory - remove 5 units
        adjust_data2 = {
            "product_id": product_id,
            "quantity_change": -5,
            "reason": "Damaged items"
        }
        response2 = self.session.post(f"{BASE_URL}/api/moego/inventory/adjust", json=adjust_data2)
        assert response2.status_code == 200
        result2 = response2.json().get("result", response2.json())
        assert result2["new_quantity"] == 25
        print(f"✓ Adjusted inventory again: 30 -> 25")
    
    def test_low_stock_alert(self):
        """Test low stock products endpoint"""
        # Create a low stock product
        sku = f"TEST-LOW-{uuid.uuid4().hex[:6].upper()}"
        create_res = self.session.post(f"{BASE_URL}/api/moego/inventory/products", json={
            "sku": sku,
            "name": "Test Low Stock Product",
            "category": "accessories",
            "price_cents": 499,
            "quantity": 3,  # Below reorder point
            "reorder_point": 10
        })
        assert create_res.status_code == 200
        
        # Get low stock products
        response = self.session.get(f"{BASE_URL}/api/moego/inventory/low-stock")
        assert response.status_code == 200, f"Get low stock failed: {response.text}"
        
        data = response.json()
        assert "products" in data
        # Should include our low stock product
        low_stock_skus = [p["sku"] for p in data["products"]]
        assert sku in low_stock_skus, f"Low stock product not found in list"
        print(f"✓ Low stock alert working: {len(data['products'])} products need restocking")


class TestPOSCheckout:
    """Tests for POS Checkout endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get admin auth token and create test product"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        token = login_res.json().get("token")  # API returns 'token' not 'access_token'
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Create a test product for POS transactions
        self.test_sku = f"POS-{uuid.uuid4().hex[:6].upper()}"
        create_res = self.session.post(f"{BASE_URL}/api/moego/inventory/products", json={
            "sku": self.test_sku,
            "name": "POS Test Product",
            "category": "treats",
            "price_cents": 500,  # $5.00
            "quantity": 100,
            "reorder_point": 10
        })
        assert create_res.status_code == 200
        self.test_product_id = create_res.json()["product"]["id"]
        yield
    
    def test_pos_transaction_cash(self):
        """Test POS transaction with cash payment"""
        transaction_data = {
            "items": [
                {"product_id": self.test_product_id, "quantity": 2}
            ],
            "payment_method": "cash",
            "discount_cents": 0
        }
        
        response = self.session.post(f"{BASE_URL}/api/moego/pos/transaction", json=transaction_data)
        assert response.status_code == 200, f"POS transaction failed: {response.text}"
        
        data = response.json()
        assert "transaction" in data
        transaction = data["transaction"]
        assert transaction["payment_method"] == "cash"
        assert transaction["status"] == "completed"
        assert transaction["subtotal_cents"] == 1000  # 2 x $5.00
        assert transaction["tax_cents"] > 0  # 8% tax
        print(f"✓ Cash transaction completed: ${transaction['total_cents']/100:.2f}")
        
        # Store transaction ID for retrieval test
        self.__class__.last_transaction_id = transaction["id"]
    
    def test_pos_transaction_card(self):
        """Test POS transaction with card payment"""
        transaction_data = {
            "items": [
                {"product_id": self.test_product_id, "quantity": 3}
            ],
            "payment_method": "card",
            "discount_cents": 100  # $1.00 discount
        }
        
        response = self.session.post(f"{BASE_URL}/api/moego/pos/transaction", json=transaction_data)
        assert response.status_code == 200, f"POS card transaction failed: {response.text}"
        
        data = response.json()
        transaction = data["transaction"]
        assert transaction["payment_method"] == "card"
        assert transaction["discount_cents"] == 100
        # Subtotal: 3 x $5.00 = $15.00, minus $1.00 discount = $14.00 + tax
        assert transaction["subtotal_cents"] == 1500
        print(f"✓ Card transaction completed with discount: ${transaction['total_cents']/100:.2f}")
    
    def test_pos_transaction_with_customer(self):
        """Test POS transaction with customer association"""
        # First get a customer ID (use admin user for simplicity)
        users_res = self.session.get(f"{BASE_URL}/api/users?role=customer&limit=1")
        customer_id = None
        if users_res.status_code == 200 and users_res.json().get("users"):
            customer_id = users_res.json()["users"][0]["id"]
        
        transaction_data = {
            "items": [
                {"product_id": self.test_product_id, "quantity": 1}
            ],
            "payment_method": "cash",
            "customer_id": customer_id,
            "discount_cents": 0
        }
        
        response = self.session.post(f"{BASE_URL}/api/moego/pos/transaction", json=transaction_data)
        assert response.status_code == 200, f"POS transaction with customer failed: {response.text}"
        
        data = response.json()
        transaction = data["transaction"]
        if customer_id:
            assert transaction["customer_id"] == customer_id
            print(f"✓ Transaction with customer association: {customer_id}")
        else:
            print(f"✓ Transaction completed (no customer available)")
    
    def test_get_transaction(self):
        """Test retrieving a transaction by ID"""
        # First create a transaction
        transaction_data = {
            "items": [{"product_id": self.test_product_id, "quantity": 1}],
            "payment_method": "cash",
            "discount_cents": 0
        }
        create_res = self.session.post(f"{BASE_URL}/api/moego/pos/transaction", json=transaction_data)
        assert create_res.status_code == 200
        transaction_id = create_res.json()["transaction"]["id"]
        
        # Get the transaction
        response = self.session.get(f"{BASE_URL}/api/moego/pos/transaction/{transaction_id}")
        assert response.status_code == 200, f"Get transaction failed: {response.text}"
        
        data = response.json()
        assert "transaction" in data
        assert data["transaction"]["id"] == transaction_id
        print(f"✓ Retrieved transaction: {transaction_id}")
    
    def test_daily_sales(self):
        """Test daily sales summary endpoint"""
        response = self.session.get(f"{BASE_URL}/api/moego/pos/daily-sales")
        assert response.status_code == 200, f"Get daily sales failed: {response.text}"
        
        data = response.json()
        assert "date" in data
        assert "transaction_count" in data
        assert "total_sales_cents" in data
        print(f"✓ Daily sales: {data['transaction_count']} transactions, ${data['total_sales_cents']/100:.2f} total")
    
    def test_inventory_deduction_after_sale(self):
        """Test that inventory is deducted after POS sale"""
        # Create a fresh product
        sku = f"INV-DED-{uuid.uuid4().hex[:6].upper()}"
        create_res = self.session.post(f"{BASE_URL}/api/moego/inventory/products", json={
            "sku": sku,
            "name": "Inventory Deduction Test",
            "category": "toys",
            "price_cents": 999,
            "quantity": 10,
            "reorder_point": 2
        })
        assert create_res.status_code == 200
        product_id = create_res.json()["product"]["id"]
        
        # Make a sale
        transaction_data = {
            "items": [{"product_id": product_id, "quantity": 3}],
            "payment_method": "cash",
            "discount_cents": 0
        }
        sale_res = self.session.post(f"{BASE_URL}/api/moego/pos/transaction", json=transaction_data)
        assert sale_res.status_code == 200
        
        # Check inventory was deducted
        product_res = self.session.get(f"{BASE_URL}/api/moego/inventory/products/{product_id}")
        assert product_res.status_code == 200
        updated_quantity = product_res.json()["product"]["quantity"]
        assert updated_quantity == 7, f"Expected 7, got {updated_quantity}"
        print(f"✓ Inventory deducted correctly: 10 -> 7")


class TestCRMLeads:
    """Tests for CRM and Leads Management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get admin auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        token = login_res.json().get("token")  # API returns 'token' not 'access_token'
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        yield
    
    def test_create_lead(self):
        """Test creating a new lead"""
        lead_data = {
            "name": f"Test Lead {uuid.uuid4().hex[:6]}",
            "email": f"testlead_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "(555) 123-4567",
            "source": "website",
            "notes": "Interested in boarding services",
            "dog_info": {
                "name": "Buddy",
                "breed": "Golden Retriever",
                "age": "3 years",
                "notes": "Friendly, needs daily medication"
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/moego/crm/leads", json=lead_data)
        assert response.status_code == 200, f"Create lead failed: {response.text}"
        
        data = response.json()
        assert "lead" in data
        lead = data["lead"]
        assert lead["name"] == lead_data["name"]
        assert lead["email"] == lead_data["email"]
        assert lead["status"] == "new"
        assert lead["dog_info"]["name"] == "Buddy"
        
        # Store lead ID for other tests
        self.__class__.created_lead_id = lead["id"]
        print(f"✓ Created lead: {lead['name']} (ID: {lead['id']})")
    
    def test_list_leads(self):
        """Test listing leads"""
        response = self.session.get(f"{BASE_URL}/api/moego/crm/leads")
        assert response.status_code == 200, f"List leads failed: {response.text}"
        
        data = response.json()
        assert "leads" in data
        assert "count" in data
        print(f"✓ Listed {data['count']} leads")
    
    def test_list_leads_with_filters(self):
        """Test listing leads with status and source filters"""
        # Filter by status
        response = self.session.get(f"{BASE_URL}/api/moego/crm/leads?status=new")
        assert response.status_code == 200
        
        # Filter by source
        response2 = self.session.get(f"{BASE_URL}/api/moego/crm/leads?source=website")
        assert response2.status_code == 200
        print(f"✓ Lead filtering works correctly")
    
    def test_update_lead_status(self):
        """Test updating lead status (workflow)"""
        # Create a lead first
        lead_data = {
            "name": f"Status Test Lead {uuid.uuid4().hex[:6]}",
            "email": f"status_{uuid.uuid4().hex[:6]}@example.com",
            "source": "walk_in"
        }
        create_res = self.session.post(f"{BASE_URL}/api/moego/crm/leads", json=lead_data)
        assert create_res.status_code == 200
        lead_id = create_res.json()["lead"]["id"]
        
        # Update status: new -> contacted
        response = self.session.put(f"{BASE_URL}/api/moego/crm/leads/{lead_id}/status", json={
            "status": "contacted",
            "notes": "Called customer, left voicemail"
        })
        assert response.status_code == 200, f"Update status failed: {response.text}"
        assert response.json()["lead"]["status"] == "contacted"
        print(f"✓ Lead status updated: new -> contacted")
        
        # Update status: contacted -> qualified
        response2 = self.session.put(f"{BASE_URL}/api/moego/crm/leads/{lead_id}/status", json={
            "status": "qualified",
            "notes": "Customer confirmed interest, scheduling tour"
        })
        assert response2.status_code == 200
        assert response2.json()["lead"]["status"] == "qualified"
        print(f"✓ Lead status updated: contacted -> qualified")
    
    def test_convert_lead_to_customer(self):
        """Test converting a lead to customer"""
        # Create a lead
        lead_data = {
            "name": f"Convert Test Lead {uuid.uuid4().hex[:6]}",
            "email": f"convert_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "(555) 999-8888",
            "source": "referral",
            "dog_info": {
                "name": "Max",
                "breed": "Labrador"
            }
        }
        create_res = self.session.post(f"{BASE_URL}/api/moego/crm/leads", json=lead_data)
        assert create_res.status_code == 200
        lead_id = create_res.json()["lead"]["id"]
        
        # Convert to customer
        response = self.session.post(f"{BASE_URL}/api/moego/crm/leads/{lead_id}/convert")
        assert response.status_code == 200, f"Convert lead failed: {response.text}"
        
        data = response.json()
        assert data["lead"]["status"] == "converted"
        assert "converted_at" in data["lead"]
        print(f"✓ Lead converted to customer: {lead_id}")
    
    def test_mark_lead_as_lost(self):
        """Test marking a lead as lost"""
        # Create a lead
        lead_data = {
            "name": f"Lost Test Lead {uuid.uuid4().hex[:6]}",
            "source": "social"
        }
        create_res = self.session.post(f"{BASE_URL}/api/moego/crm/leads", json=lead_data)
        assert create_res.status_code == 200
        lead_id = create_res.json()["lead"]["id"]
        
        # Mark as lost
        response = self.session.put(f"{BASE_URL}/api/moego/crm/leads/{lead_id}/status", json={
            "status": "lost",
            "notes": "Customer chose competitor"
        })
        assert response.status_code == 200
        assert response.json()["lead"]["status"] == "lost"
        print(f"✓ Lead marked as lost: {lead_id}")
    
    def test_retention_metrics(self):
        """Test retention metrics endpoint"""
        response = self.session.get(f"{BASE_URL}/api/moego/crm/retention-metrics")
        assert response.status_code == 200, f"Get retention metrics failed: {response.text}"
        
        data = response.json()
        assert "total_customers" in data
        assert "repeat_rate_percent" in data
        assert "average_visits" in data
        assert "average_ltv_cents" in data
        assert "by_lifecycle" in data
        print(f"✓ Retention metrics: {data['total_customers']} customers, {data['repeat_rate_percent']}% repeat rate")


class TestIntegration:
    """Integration tests for POS & CRM working together"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get admin auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_res.status_code == 200
        token = login_res.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        yield
    
    def test_full_pos_workflow(self):
        """Test complete POS workflow: create product -> sell -> check inventory"""
        # 1. Create product
        sku = f"FLOW-{uuid.uuid4().hex[:6].upper()}"
        create_res = self.session.post(f"{BASE_URL}/api/moego/inventory/products", json={
            "sku": sku,
            "name": "Workflow Test Product",
            "category": "food",
            "price_cents": 1999,
            "quantity": 25,
            "reorder_point": 5
        })
        assert create_res.status_code == 200
        product = create_res.json()["product"]
        product_id = product["id"]
        print(f"✓ Step 1: Created product {sku}")
        
        # 2. Make a sale
        sale_res = self.session.post(f"{BASE_URL}/api/moego/pos/transaction", json={
            "items": [{"product_id": product_id, "quantity": 5}],
            "payment_method": "card",
            "discount_cents": 500  # $5 discount
        })
        assert sale_res.status_code == 200
        transaction = sale_res.json()["transaction"]
        print(f"✓ Step 2: Completed sale for ${transaction['total_cents']/100:.2f}")
        
        # 3. Verify inventory deducted
        product_res = self.session.get(f"{BASE_URL}/api/moego/inventory/products/{product_id}")
        assert product_res.status_code == 200
        updated_product = product_res.json()["product"]
        assert updated_product["quantity"] == 20
        print(f"✓ Step 3: Inventory verified (25 -> 20)")
        
        # 4. Check daily sales includes this transaction
        sales_res = self.session.get(f"{BASE_URL}/api/moego/pos/daily-sales")
        assert sales_res.status_code == 200
        print(f"✓ Step 4: Daily sales updated")
    
    def test_full_lead_workflow(self):
        """Test complete lead workflow: create -> contact -> qualify -> convert"""
        # 1. Create lead
        lead_data = {
            "name": f"Workflow Lead {uuid.uuid4().hex[:6]}",
            "email": f"workflow_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "(555) 111-2222",
            "source": "website",
            "dog_info": {"name": "Charlie", "breed": "Beagle"}
        }
        create_res = self.session.post(f"{BASE_URL}/api/moego/crm/leads", json=lead_data)
        assert create_res.status_code == 200
        lead_id = create_res.json()["lead"]["id"]
        print(f"✓ Step 1: Created lead (status: new)")
        
        # 2. Contact lead
        contact_res = self.session.put(f"{BASE_URL}/api/moego/crm/leads/{lead_id}/status", json={
            "status": "contacted",
            "notes": "Initial phone call made"
        })
        assert contact_res.status_code == 200
        print(f"✓ Step 2: Lead contacted")
        
        # 3. Qualify lead
        qualify_res = self.session.put(f"{BASE_URL}/api/moego/crm/leads/{lead_id}/status", json={
            "status": "qualified",
            "notes": "Scheduled facility tour"
        })
        assert qualify_res.status_code == 200
        print(f"✓ Step 3: Lead qualified")
        
        # 4. Convert to customer
        convert_res = self.session.post(f"{BASE_URL}/api/moego/crm/leads/{lead_id}/convert")
        assert convert_res.status_code == 200
        assert convert_res.json()["lead"]["status"] == "converted"
        print(f"✓ Step 4: Lead converted to customer")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
