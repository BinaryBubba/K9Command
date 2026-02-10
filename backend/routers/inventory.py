"""
Inventory Router - K9Command
Handles retail inventory management and POS transactions
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timezone
import uuid

from models import UserRole
from auth import get_current_user
from services.pos_crm import InventoryService, POSService

router = APIRouter(prefix="/api/k9", tags=["Inventory & POS"])
security = HTTPBearer()


def get_db():
    """Get database connection"""
    from server import db
    return db


# ==================== INVENTORY ====================

@router.post("/inventory/products")
async def create_product(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new retail product"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = InventoryService(db)
    product = await service.create_product(data)
    
    return {"message": "Product created", "product": product}


@router.get("/inventory/products")
async def list_products(
    category: Optional[str] = None,
    active_only: bool = False,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List all products"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = InventoryService(db)
    products = await service.list_products(category, active_only)
    
    return {"products": products, "count": len(products)}


@router.get("/inventory/products/{product_id}")
async def get_product(
    product_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single product"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = InventoryService(db)
    product = await service.get_product(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.put("/inventory/products/{product_id}")
async def update_product(
    product_id: str,
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a product"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = InventoryService(db)
    product = await service.update_product(product_id, data)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product updated", "product": product}


@router.post("/inventory/adjust")
async def adjust_inventory(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Adjust inventory quantity"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = InventoryService(db)
    
    adjustment = {
        "product_id": data.get("product_id"),
        "quantity_change": data.get("quantity_change"),
        "reason": data.get("reason"),
        "reference_id": data.get("reference_id")
    }
    
    result = await service.adjust_inventory(adjustment, user.id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Inventory adjusted", "product": result}


@router.get("/inventory/low-stock")
async def get_low_stock_products(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get products with low stock"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = InventoryService(db)
    products = await service.get_low_stock_products()
    
    return {"products": products, "count": len(products)}


# ==================== POS ====================

@router.post("/pos/transaction")
async def create_pos_transaction(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a POS transaction"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = POSService(db)
    transaction = await service.process_transaction(data, user.id)
    
    return {"message": "Transaction completed", "transaction": transaction}


@router.get("/pos/transaction/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a transaction by ID"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = POSService(db)
    transaction = await service.get_transaction(transaction_id)
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return transaction


@router.get("/pos/daily-sales")
async def get_daily_sales(
    date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get daily sales summary"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    service = POSService(db)
    summary = await service.get_daily_sales(date)
    
    return summary
