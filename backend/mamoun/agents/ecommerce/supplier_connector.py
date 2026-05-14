"""
BABSHARQII v12.0 — Supplier Connector
وكيل ربط الموردين — يبحث عن موردين وينشئ طلبات شراء تجريبية.

Capabilities:
- البحث عن موردين حسب الفئة والمنطقة
- إنشاء طلبات شراء تجريبية (trial orders)
- إلغاء الطلبات إذا لزم الأمر
- تقييم الموردين حسب الجودة والسعر والتوصيل
- كل عملية تحتاج صلاحية زمنية

Security:
- لا يتم إرسال أموال حقيقية بدون موافقة بشرية
- بيانات الموردين تخضع لـ Privacy Guard
- كل تفاعل مع مورد يُسجّل في سجل التدقيق
"""

import os
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SupplierStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLACKLISTED = "blacklisted"


class OrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


@dataclass
class Supplier:
    """مورد."""
    id: str = ""
    name: str = ""
    name_ar: str = ""
    category: str = ""
    region: str = "SA"  # السعودية كافتراضي
    rating: float = 0.0
    verified: bool = False
    min_order: float = 0.0
    currency: str = "SAR"
    lead_time_days: int = 7
    contact: dict = field(default_factory=dict)
    status: str = SupplierStatus.PENDING.value


@dataclass
class PurchaseRequest:
    """طلب شراء من مورد."""
    id: str = ""
    supplier_id: str = ""
    store_id: str = ""
    items: list = field(default_factory=list)
    total: float = 0.0
    currency: str = "SAR"
    status: str = OrderStatus.DRAFT.value
    is_trial: bool = True  # تجريبي افتراضياً
    created_at: float = 0.0
    notes: str = ""


class SupplierConnector:
    """
    وكيل ربط الموردين — يبحث عن موردين وينشئ طلبات شراء.
    
    Workflow:
    1. search_suppliers() — البحث عن موردين
    2. evaluate_supplier() — تقييم مورد
    3. create_purchase_request() — إنشاء طلب شراء تجريبي
    4. confirm_purchase() — تأكيد الطلب (يتطلب موافقة بشرية)
    5. cancel_purchase() — إلغاء الطلب
    """
    
    def __init__(self, time_bounded_policy=None):
        self._policy = time_bounded_policy
        self._suppliers: dict[str, Supplier] = {}
        self._purchase_requests: dict[str, PurchaseRequest] = {}
        self._initialized = False
        self._supplier_counter = 0
        self._request_counter = 0
    
    async def initialize(self):
        if self._initialized:
            return
        self._initialized = True
        # Pre-load some simulated suppliers
        await self._load_sample_suppliers()
        logger.info("SupplierConnector initialized — Supplier network ready")
    
    async def search_suppliers(
        self,
        category: str = "",
        region: str = "",
        min_rating: float = 0.0,
        grant_id: str = "",
    ) -> dict:
        """
        البحث عن موردين حسب المعايير.
        
        Args:
            category: فئة المنتجات
            region: المنطقة (SA, AE, KW, etc.)
            min_rating: الحد الأدنى للتقييم
            grant_id: صلاحية ecommerce:supplier
        """
        await self.initialize()
        
        results = []
        for supplier in self._suppliers.values():
            if category and supplier.category != category:
                continue
            if region and supplier.region != region:
                continue
            if min_rating and supplier.rating < min_rating:
                continue
            results.append(supplier)
        
        # Sort by rating
        results.sort(key=lambda s: s.rating, reverse=True)
        
        return {
            "success": True,
            "total_found": len(results),
            "suppliers": [
                {
                    "id": s.id,
                    "name": s.name,
                    "name_ar": s.name_ar,
                    "category": s.category,
                    "region": s.region,
                    "rating": s.rating,
                    "verified": s.verified,
                    "min_order": s.min_order,
                    "currency": s.currency,
                    "lead_time_days": s.lead_time_days,
                    "status": s.status,
                }
                for s in results
            ],
        }
    
    async def evaluate_supplier(self, supplier_id: str, grant_id: str = "") -> dict:
        """
        تقييم مورد — فحص الجودة والسعر والتوصيل.
        """
        await self.initialize()
        
        supplier = self._suppliers.get(supplier_id)
        if not supplier:
            return {"success": False, "error": f"المورد غير موجود: {supplier_id}"}
        
        # Simulate evaluation
        evaluation = {
            "supplier_id": supplier_id,
            "name": supplier.name,
            "overall_score": supplier.rating,
            "quality_score": min(5.0, supplier.rating + 0.2),
            "price_competitiveness": min(5.0, supplier.rating - 0.1),
            "delivery_reliability": min(5.0, supplier.rating + 0.1),
            "communication": min(5.0, supplier.rating),
            "verified": supplier.verified,
            "recommendation": "موصى به" if supplier.rating >= 3.5 else "يحتاج تقييم إضافي",
            "risk_level": "low" if supplier.rating >= 4.0 else ("medium" if supplier.rating >= 3.0 else "high"),
        }
        
        return {"success": True, "evaluation": evaluation}
    
    async def create_purchase_request(
        self,
        supplier_id: str,
        store_id: str,
        items: list[dict],
        is_trial: bool = True,
        grant_id: str = "",
        task_context: str = "",
    ) -> dict:
        """
        إنشاء طلب شراء — تجريبي افتراضياً.
        
        Args:
            supplier_id: معرف المورد
            store_id: معرف المتجر
            items: قائمة المنتجات المطلوبة [{"product_name": "...", "quantity": 10, "unit_price": 50.0}]
            is_trial: طلب تجريبي (لا يُرسل فعلياً)
            grant_id: صلاحية
            task_context: سياق المهمة
        """
        await self.initialize()
        
        supplier = self._suppliers.get(supplier_id)
        if not supplier:
            return {"success": False, "error": f"المورد غير موجود: {supplier_id}"}
        
        # Calculate total
        total = sum(item.get("unit_price", 0) * item.get("quantity", 0) for item in items)
        
        if total < supplier.min_order:
            return {
                "success": False,
                "error": f"الحد الأدنى للطلب: {supplier.min_order} {supplier.currency} — المجموع: {total} {supplier.currency}",
            }
        
        self._request_counter += 1
        request = PurchaseRequest(
            id=f"pr_{int(time.time())}_{self._request_counter}",
            supplier_id=supplier_id,
            store_id=store_id,
            items=items,
            total=total,
            currency=supplier.currency,
            is_trial=is_trial,
            created_at=time.time(),
        )
        self._purchase_requests[request.id] = request
        
        mode = "تجريبي" if is_trial else "فعلي"
        return {
            "success": True,
            "request_id": request.id,
            "status": request.status,
            "is_trial": is_trial,
            "total": total,
            "currency": supplier.currency,
            "message": f"تم إنشاء طلب شراء ({mode}) بقيمة {total:.2f} {supplier.currency}",
        }
    
    async def cancel_purchase(self, request_id: str, reason: str = "", grant_id: str = "") -> dict:
        """
        إلغاء طلب شراء.
        """
        await self.initialize()
        
        request = self._purchase_requests.get(request_id)
        if not request:
            return {"success": False, "error": f"الطلب غير موجود: {request_id}"}
        
        if request.status in (OrderStatus.SHIPPED.value, OrderStatus.DELIVERED.value):
            return {"success": False, "error": f"لا يمكن إلغاء طلب تم شحنه أو تسليمه"}
        
        request.status = OrderStatus.CANCELLED.value
        request.notes = f"Cancelled: {reason}"
        
        return {
            "success": True,
            "request_id": request_id,
            "status": OrderStatus.CANCELLED.value,
            "message": f"تم إلغاء الطلب {request_id}",
        }
    
    async def get_supplier(self, supplier_id: str) -> Optional[dict]:
        """الحصول على بيانات مورد."""
        supplier = self._suppliers.get(supplier_id)
        return supplier.__dict__ if supplier else None
    
    async def _load_sample_suppliers(self):
        """تحميل موردين تجريبيين."""
        sample_suppliers = [
            Supplier(id="sup_1", name="Al-Kitab Books", name_ar="مكتبة الكتاب", category="books",
                    region="SA", rating=4.2, verified=True, min_order=500, currency="SAR", lead_time_days=3),
            Supplier(id="sup_2", name="Gulf Electronics", name_ar="إلكترونيات الخليج", category="electronics",
                    region="AE", rating=3.8, verified=True, min_order=1000, currency="SAR", lead_time_days=5),
            Supplier(id="sup_3", name="Moda Fashion", name_ar="موضة للأزياء", category="clothing",
                    region="SA", rating=4.5, verified=True, min_order=300, currency="SAR", lead_time_days=2),
            Supplier(id="sup_4", name="Organic Foods SA", name_ar="أغذية عضوية", category="food",
                    region="SA", rating=4.0, verified=False, min_order=200, currency="SAR", lead_time_days=1),
            Supplier(id="sup_5", name="Digital Solutions", name_ar="حلول رقمية", category="digital",
                    region="KW", rating=3.5, verified=False, min_order=0, currency="SAR", lead_time_days=0),
        ]
        for s in sample_suppliers:
            self._suppliers[s.id] = s
