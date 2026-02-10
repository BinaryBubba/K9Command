"""
POS & Retail Service
Handles inventory management, POS checkout, and CRM functionality.
"""
import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from enum import Enum


class ProductCategory(str, Enum):
    FOOD = "food"
    TREATS = "treats"
    TOYS = "toys"
    GROOMING = "grooming"
    ACCESSORIES = "accessories"
    MEDICATION = "medication"
    OTHER = "other"


class InventoryStatus(str, Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class CustomerLifecycle(str, Enum):
    LEAD = "lead"
    NEW = "new"
    ACTIVE = "active"
    AT_RISK = "at_risk"
    LAPSED = "lapsed"
    CHURNED = "churned"


class TransactionType(str, Enum):
    SALE = "sale"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


# ==================== INVENTORY MODELS ====================

class ProductCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    category: ProductCategory
    price_cents: int
    cost_cents: Optional[int] = None
    quantity: int = 0
    reorder_point: int = 5
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True


class ProductResponse(BaseModel):
    id: str
    sku: str
    name: str
    description: Optional[str]
    category: ProductCategory
    price_cents: int
    cost_cents: Optional[int]
    quantity: int
    reorder_point: int
    status: InventoryStatus
    barcode: Optional[str]
    image_url: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str


class InventoryAdjustment(BaseModel):
    product_id: str
    quantity_change: int  # Positive for add, negative for remove
    reason: str
    reference_id: Optional[str] = None  # Order ID, POS transaction, etc.


# ==================== POS MODELS ====================

class POSCartItem(BaseModel):
    product_id: str
    quantity: int
    price_override: Optional[int] = None  # For discounts


class POSTransaction(BaseModel):
    items: List[POSCartItem]
    customer_id: Optional[str] = None
    payment_method: str = "cash"  # cash, card, card_on_file
    card_id: Optional[str] = None  # If paying with saved card
    notes: Optional[str] = None
    discount_cents: int = 0


# ==================== CRM MODELS ====================

class LeadCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    source: str = "walk_in"  # walk_in, website, referral, social, other
    notes: Optional[str] = None
    dog_info: Optional[Dict[str, Any]] = None


class CustomerMetrics(BaseModel):
    customer_id: str
    total_visits: int
    total_spent_cents: int
    average_visit_value_cents: int
    first_visit_date: Optional[str]
    last_visit_date: Optional[str]
    days_since_last_visit: int
    lifecycle_stage: CustomerLifecycle
    lifetime_value_cents: int


# ==================== SERVICES ====================

class InventoryService:
    """Manages retail inventory and stock levels"""
    
    def __init__(self, db):
        self.db = db
    
    async def create_product(self, data: ProductCreate) -> ProductResponse:
        """Create a new product in inventory"""
        product_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Determine status based on quantity
        status = self._calculate_status(data.quantity, data.reorder_point)
        
        product_doc = {
            "id": product_id,
            "sku": data.sku.upper(),
            "name": data.name,
            "description": data.description,
            "category": data.category,
            "price_cents": data.price_cents,
            "cost_cents": data.cost_cents,
            "quantity": data.quantity,
            "reorder_point": data.reorder_point,
            "status": status,
            "barcode": data.barcode,
            "image_url": data.image_url,
            "is_active": data.is_active,
            "created_at": now,
            "updated_at": now
        }
        
        await self.db.products.insert_one(product_doc)
        product_doc.pop('_id', None)
        
        return ProductResponse(**product_doc)
    
    def _calculate_status(self, quantity: int, reorder_point: int) -> InventoryStatus:
        """Calculate inventory status based on quantity"""
        if quantity <= 0:
            return InventoryStatus.OUT_OF_STOCK
        elif quantity <= reorder_point:
            return InventoryStatus.LOW_STOCK
        return InventoryStatus.IN_STOCK
    
    async def get_product(self, product_id: str) -> Optional[ProductResponse]:
        """Get a product by ID"""
        product = await self.db.products.find_one({"id": product_id}, {"_id": 0})
        if product:
            return ProductResponse(**product)
        return None
    
    async def get_product_by_sku(self, sku: str) -> Optional[ProductResponse]:
        """Get a product by SKU"""
        product = await self.db.products.find_one({"sku": sku.upper()}, {"_id": 0})
        if product:
            return ProductResponse(**product)
        return None
    
    async def list_products(
        self,
        category: Optional[ProductCategory] = None,
        status: Optional[InventoryStatus] = None,
        active_only: bool = True,
        limit: int = 100
    ) -> List[ProductResponse]:
        """List products with optional filters"""
        query = {}
        if category:
            query["category"] = category
        if status:
            query["status"] = status
        if active_only:
            query["is_active"] = True
        
        products = await self.db.products.find(query, {"_id": 0}).limit(limit).to_list(limit)
        return [ProductResponse(**p) for p in products]
    
    async def update_product(self, product_id: str, updates: Dict[str, Any]) -> Optional[ProductResponse]:
        """Update a product"""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Recalculate status if quantity changed
        if "quantity" in updates:
            product = await self.db.products.find_one({"id": product_id}, {"_id": 0})
            if product:
                reorder_point = updates.get("reorder_point", product.get("reorder_point", 5))
                updates["status"] = self._calculate_status(updates["quantity"], reorder_point)
        
        result = await self.db.products.update_one(
            {"id": product_id},
            {"$set": updates}
        )
        
        if result.modified_count > 0:
            return await self.get_product(product_id)
        return None
    
    async def adjust_inventory(self, adjustment: InventoryAdjustment, adjusted_by: str) -> Dict[str, Any]:
        """Adjust inventory quantity and log the change"""
        product = await self.db.products.find_one({"id": adjustment.product_id}, {"_id": 0})
        if not product:
            raise Exception("Product not found")
        
        new_quantity = product["quantity"] + adjustment.quantity_change
        if new_quantity < 0:
            raise Exception("Cannot reduce inventory below 0")
        
        # Update product quantity
        new_status = self._calculate_status(new_quantity, product.get("reorder_point", 5))
        await self.db.products.update_one(
            {"id": adjustment.product_id},
            {"$set": {
                "quantity": new_quantity,
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Log the adjustment
        log_id = str(uuid.uuid4())
        log_doc = {
            "id": log_id,
            "product_id": adjustment.product_id,
            "product_sku": product["sku"],
            "product_name": product["name"],
            "previous_quantity": product["quantity"],
            "quantity_change": adjustment.quantity_change,
            "new_quantity": new_quantity,
            "reason": adjustment.reason,
            "reference_id": adjustment.reference_id,
            "adjusted_by": adjusted_by,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await self.db.inventory_logs.insert_one(log_doc)
        log_doc.pop('_id', None)
        
        return {
            "product_id": adjustment.product_id,
            "previous_quantity": product["quantity"],
            "new_quantity": new_quantity,
            "status": new_status,
            "log_id": log_id
        }
    
    async def get_low_stock_products(self) -> List[ProductResponse]:
        """Get products that are low or out of stock"""
        products = await self.db.products.find(
            {"status": {"$in": [InventoryStatus.LOW_STOCK, InventoryStatus.OUT_OF_STOCK]}, "is_active": True},
            {"_id": 0}
        ).to_list(100)
        return [ProductResponse(**p) for p in products]


class POSService:
    """Handles point-of-sale transactions"""
    
    def __init__(self, db):
        self.db = db
        self.inventory = InventoryService(db)
    
    async def process_transaction(
        self,
        transaction: POSTransaction,
        cashier_id: str
    ) -> Dict[str, Any]:
        """Process a POS transaction"""
        transaction_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Calculate totals and validate inventory
        line_items = []
        subtotal_cents = 0
        
        for item in transaction.items:
            product = await self.inventory.get_product(item.product_id)
            if not product:
                raise Exception(f"Product {item.product_id} not found")
            
            if product.quantity < item.quantity:
                raise Exception(f"Insufficient stock for {product.name}. Available: {product.quantity}")
            
            price = item.price_override if item.price_override is not None else product.price_cents
            line_total = price * item.quantity
            subtotal_cents += line_total
            
            line_items.append({
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "quantity": item.quantity,
                "unit_price_cents": price,
                "line_total_cents": line_total
            })
        
        # Apply discount
        total_cents = subtotal_cents - transaction.discount_cents
        if total_cents < 0:
            total_cents = 0
        
        # Calculate tax (simplified - 8% tax rate)
        tax_rate = 0.08
        tax_cents = int(total_cents * tax_rate)
        grand_total_cents = total_cents + tax_cents
        
        # Create transaction record
        transaction_doc = {
            "id": transaction_id,
            "type": TransactionType.SALE,
            "customer_id": transaction.customer_id,
            "line_items": line_items,
            "subtotal_cents": subtotal_cents,
            "discount_cents": transaction.discount_cents,
            "tax_cents": tax_cents,
            "total_cents": grand_total_cents,
            "payment_method": transaction.payment_method,
            "card_id": transaction.card_id,
            "notes": transaction.notes,
            "cashier_id": cashier_id,
            "status": "completed",
            "created_at": now.isoformat()
        }
        
        await self.db.pos_transactions.insert_one(transaction_doc)
        transaction_doc.pop('_id', None)
        
        # Deduct inventory
        for item in transaction.items:
            await self.inventory.adjust_inventory(
                InventoryAdjustment(
                    product_id=item.product_id,
                    quantity_change=-item.quantity,
                    reason="POS Sale",
                    reference_id=transaction_id
                ),
                adjusted_by=cashier_id
            )
        
        # Update customer metrics if customer provided
        if transaction.customer_id:
            await self._update_customer_metrics(transaction.customer_id, grand_total_cents, now)
        
        return transaction_doc
    
    async def _update_customer_metrics(self, customer_id: str, amount_cents: int, visit_date: datetime):
        """Update customer CRM metrics after a transaction"""
        metrics = await self.db.customer_metrics.find_one({"customer_id": customer_id}, {"_id": 0})
        
        if metrics:
            total_visits = metrics.get("total_visits", 0) + 1
            total_spent = metrics.get("total_spent_cents", 0) + amount_cents
            
            await self.db.customer_metrics.update_one(
                {"customer_id": customer_id},
                {"$set": {
                    "total_visits": total_visits,
                    "total_spent_cents": total_spent,
                    "average_visit_value_cents": total_spent // total_visits,
                    "last_visit_date": visit_date.isoformat(),
                    "updated_at": visit_date.isoformat()
                }}
            )
        else:
            await self.db.customer_metrics.insert_one({
                "customer_id": customer_id,
                "total_visits": 1,
                "total_spent_cents": amount_cents,
                "average_visit_value_cents": amount_cents,
                "first_visit_date": visit_date.isoformat(),
                "last_visit_date": visit_date.isoformat(),
                "lifecycle_stage": CustomerLifecycle.NEW,
                "created_at": visit_date.isoformat(),
                "updated_at": visit_date.isoformat()
            })
    
    async def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get a transaction by ID"""
        transaction = await self.db.pos_transactions.find_one({"id": transaction_id}, {"_id": 0})
        return transaction
    
    async def get_daily_sales(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get sales summary for a day"""
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        transactions = await self.db.pos_transactions.find(
            {
                "type": TransactionType.SALE,
                "created_at": {"$regex": f"^{date}"}
            },
            {"_id": 0}
        ).to_list(500)
        
        total_sales = sum(t.get("total_cents", 0) for t in transactions)
        total_tax = sum(t.get("tax_cents", 0) for t in transactions)
        transaction_count = len(transactions)
        
        # Group by payment method
        by_payment = {}
        for t in transactions:
            method = t.get("payment_method", "unknown")
            if method not in by_payment:
                by_payment[method] = {"count": 0, "total_cents": 0}
            by_payment[method]["count"] += 1
            by_payment[method]["total_cents"] += t.get("total_cents", 0)
        
        return {
            "date": date,
            "transaction_count": transaction_count,
            "total_sales_cents": total_sales,
            "total_tax_cents": total_tax,
            "average_transaction_cents": total_sales // transaction_count if transaction_count > 0 else 0,
            "by_payment_method": by_payment
        }


class CRMService:
    """Manages customer relationships and lifecycle"""
    
    def __init__(self, db):
        self.db = db
    
    async def create_lead(self, lead: LeadCreate, created_by: str) -> Dict[str, Any]:
        """Create a new lead in the pipeline"""
        lead_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        lead_doc = {
            "id": lead_id,
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "source": lead.source,
            "notes": lead.notes,
            "dog_info": lead.dog_info,
            "status": "new",  # new, contacted, qualified, converted, lost
            "lifecycle_stage": CustomerLifecycle.LEAD,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now
        }
        
        await self.db.leads.insert_one(lead_doc)
        lead_doc.pop('_id', None)
        
        return lead_doc
    
    async def get_leads(
        self,
        status: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get leads with optional filters"""
        query = {}
        if status:
            query["status"] = status
        if source:
            query["source"] = source
        
        leads = await self.db.leads.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        return leads
    
    async def update_lead_status(self, lead_id: str, status: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """Update lead status"""
        updates = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if notes:
            updates["notes"] = notes
        
        await self.db.leads.update_one({"id": lead_id}, {"$set": updates})
        lead = await self.db.leads.find_one({"id": lead_id}, {"_id": 0})
        return lead
    
    async def convert_lead_to_customer(self, lead_id: str) -> Dict[str, Any]:
        """Convert a lead to a customer (mark as converted)"""
        await self.db.leads.update_one(
            {"id": lead_id},
            {"$set": {
                "status": "converted",
                "lifecycle_stage": CustomerLifecycle.NEW,
                "converted_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        lead = await self.db.leads.find_one({"id": lead_id}, {"_id": 0})
        return lead
    
    async def get_customer_metrics(self, customer_id: str) -> Optional[CustomerMetrics]:
        """Get metrics for a specific customer"""
        metrics = await self.db.customer_metrics.find_one({"customer_id": customer_id}, {"_id": 0})
        if not metrics:
            return None
        
        # Calculate days since last visit
        days_since = 0
        if metrics.get("last_visit_date"):
            last_visit = datetime.fromisoformat(metrics["last_visit_date"].replace('Z', '+00:00'))
            days_since = (datetime.now(timezone.utc) - last_visit).days
        
        # Determine lifecycle stage based on activity
        lifecycle = self._calculate_lifecycle(
            days_since,
            metrics.get("total_visits", 0),
            metrics.get("lifecycle_stage", CustomerLifecycle.NEW)
        )
        
        return CustomerMetrics(
            customer_id=customer_id,
            total_visits=metrics.get("total_visits", 0),
            total_spent_cents=metrics.get("total_spent_cents", 0),
            average_visit_value_cents=metrics.get("average_visit_value_cents", 0),
            first_visit_date=metrics.get("first_visit_date"),
            last_visit_date=metrics.get("last_visit_date"),
            days_since_last_visit=days_since,
            lifecycle_stage=lifecycle,
            lifetime_value_cents=metrics.get("total_spent_cents", 0)
        )
    
    def _calculate_lifecycle(self, days_since: int, total_visits: int, current_stage: str) -> CustomerLifecycle:
        """Calculate customer lifecycle stage based on activity"""
        if current_stage == CustomerLifecycle.LEAD:
            return CustomerLifecycle.LEAD
        
        if total_visits == 0:
            return CustomerLifecycle.NEW
        elif total_visits == 1 and days_since <= 30:
            return CustomerLifecycle.NEW
        elif days_since <= 60:
            return CustomerLifecycle.ACTIVE
        elif days_since <= 120:
            return CustomerLifecycle.AT_RISK
        elif days_since <= 365:
            return CustomerLifecycle.LAPSED
        else:
            return CustomerLifecycle.CHURNED
    
    async def get_retention_metrics(self) -> Dict[str, Any]:
        """Get overall retention and CRM metrics"""
        # Get all customer metrics
        all_metrics = await self.db.customer_metrics.find({}, {"_id": 0}).to_list(10000)
        
        if not all_metrics:
            return {
                "total_customers": 0,
                "by_lifecycle": {},
                "average_ltv_cents": 0,
                "repeat_rate_percent": 0,
                "average_visits": 0
            }
        
        total = len(all_metrics)
        total_ltv = sum(m.get("total_spent_cents", 0) for m in all_metrics)
        total_visits = sum(m.get("total_visits", 0) for m in all_metrics)
        repeat_customers = sum(1 for m in all_metrics if m.get("total_visits", 0) > 1)
        
        # Count by lifecycle
        by_lifecycle = {}
        now = datetime.now(timezone.utc)
        for m in all_metrics:
            days_since = 0
            if m.get("last_visit_date"):
                last_visit = datetime.fromisoformat(m["last_visit_date"].replace('Z', '+00:00'))
                days_since = (now - last_visit).days
            
            stage = self._calculate_lifecycle(
                days_since,
                m.get("total_visits", 0),
                m.get("lifecycle_stage", CustomerLifecycle.NEW)
            )
            if stage not in by_lifecycle:
                by_lifecycle[stage] = 0
            by_lifecycle[stage] += 1
        
        return {
            "total_customers": total,
            "by_lifecycle": by_lifecycle,
            "average_ltv_cents": total_ltv // total if total > 0 else 0,
            "repeat_rate_percent": round((repeat_customers / total) * 100, 1) if total > 0 else 0,
            "average_visits": round(total_visits / total, 1) if total > 0 else 0
        }
