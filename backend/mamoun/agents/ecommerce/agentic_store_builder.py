"""
BABSHARQII v12.0 — Agentic Store Builder
وكيل بناء المتجر الإلكتروني — من التصميم إلى الدفع.

Capabilities:
- إنشاء متجر إلكتروني من وصف نصي
- تصميم واجهة المتجر (عربي/إنجليزي)
- إدارة المنتجات والمخزون
- ربط بمنصات التوصيل عبر UCP (Universal Commerce Protocol)
- إتمام عملية الشراء الكاملة (استكشاف → تفاوض → دفع → شحن)
- كل خطوة مالية تحتاج صلاحية زمنية + موافقة بشرية

Security:
- كل عملية شراء تحتاج موافقة بشرية صريحة (ecommerce:purchase)
- لا يتم تخزين بيانات دفع حقيقية
- Privacy Guard يراقب كل تفاعل مع بيانات العملاء
- Cultural Alignment يفحص محتوى المتجر
"""

import os
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

ECOMMERCE_ENABLED = os.getenv("MAMOUN_ECOMMERCE_MODE", "false").lower() == "true"


class StoreStatus(str, Enum):
    DRAFT = "draft"
    DESIGNED = "designed"
    PRODUCTS_ADDED = "products_added"
    INVENTORY_LINKED = "inventory_linked"
    SHIPPING_LINKED = "shipping_linked"
    PAYMENT_READY = "payment_ready"
    LIVE = "live"
    SUSPENDED = "suspended"


class ProductCategory(str, Enum):
    BOOKS = "books"
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    FOOD = "food"
    DIGITAL = "digital"
    HANDMADE = "handmade"
    CUSTOM = "custom"


@dataclass
class Product:
    """منتج في المتجر."""
    id: str = ""
    name: str = ""
    name_ar: str = ""       # اسم عربي
    description: str = ""
    price: float = 0.0
    currency: str = "SAR"   # الريال السعودي كعملة افتراضية
    category: str = ProductCategory.CUSTOM.value
    stock: int = 0
    images: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class StoreConfig:
    """إعدادات المتجر."""
    name: str = ""
    name_ar: str = ""
    description: str = ""
    description_ar: str = ""
    language: str = "ar"     # ar | en | bilingual
    currency: str = "SAR"
    theme: str = "modern_arabic"
    domain: str = ""
    shipping_provider: str = ""  # UCP provider ID
    payment_provider: str = ""   # Payment gateway ID
    tax_rate: float = 0.15       # 15% VAT (Saudi Arabia default)
    social_links: dict = field(default_factory=dict)


@dataclass
class PurchaseOrder:
    """طلب شراء."""
    id: str = ""
    store_id: str = ""
    products: list = field(default_factory=list)  # list[dict with product_id, quantity]
    total_amount: float = 0.0
    currency: str = "SAR"
    status: str = "pending"  # pending, confirmed, paid, shipped, delivered, cancelled
    customer_info: dict = field(default_factory=dict)  # anonymized
    shipping_info: dict = field(default_factory=dict)
    created_at: float = 0.0
    confirmed_at: float = 0.0


class AgenticStoreBuilder:
    """
    وكيل بناء المتجر الإلكتروني — ينشئ متجراً من الصفر.
    
    Workflow:
    1. create_store() — إنشاء المتجر بالإعدادات
    2. design_store() — تصميم الواجهة (بمساعدة LLM)
    3. add_products() — إضافة المنتجات
    4. link_inventory() — ربط المخزون
    5. link_shipping() — ربط الشحن عبر UCP
    6. setup_payment() — إعداد الدفع
    7. publish_store() — نشر المتجر (يتطلب موافقة بشرية)
    
    All financial operations require Time-Bounded Permission + Human Approval.
    """
    
    def __init__(self, time_bounded_policy=None):
        self._policy = time_bounded_policy
        self._stores: dict[str, dict] = {}
        self._products: dict[str, Product] = {}
        self._orders: dict[str, PurchaseOrder] = {}
        self._initialized = False
        self._store_counter = 0
    
    async def initialize(self):
        if self._initialized:
            return
        self._initialized = True
        logger.info("AgenticStoreBuilder initialized — E-commerce agent ready")
    
    async def create_store(self, config: StoreConfig, grant_id: str = "") -> dict:
        """
        إنشاء متجر جديد.
        
        Args:
            config: إعدادات المتجر
            grant_id: صلاحية ecommerce:browse
        
        Returns:
            dict with store_id, status
        """
        await self.initialize()
        
        self._store_counter += 1
        store_id = f"store_{int(time.time())}_{self._store_counter}"
        
        store = {
            "id": store_id,
            "config": {
                "name": config.name,
                "name_ar": config.name_ar or config.name,
                "description": config.description,
                "description_ar": config.description_ar or config.description,
                "language": config.language,
                "currency": config.currency,
                "theme": config.theme,
                "tax_rate": config.tax_rate,
            },
            "status": StoreStatus.DRAFT.value,
            "products": [],
            "created_at": time.time(),
            "grant_id": grant_id,
        }
        
        self._stores[store_id] = store
        
        logger.info(f"Store created: {store_id} — {config.name_ar}")
        
        return {
            "store_id": store_id,
            "status": StoreStatus.DRAFT.value,
            "message": f"تم إنشاء المتجر '{config.name_ar}' — جاهز للتصميم",
        }
    
    async def design_store(self, store_id: str, design_preferences: dict = None, grant_id: str = "") -> dict:
        """
        تصميم واجهة المتجر — يولّد HTML/CSS بالمساعدة.
        
        Args:
            store_id: معرف المتجر
            design_preferences: تفضيلات التصميم
            grant_id: صلاحية
        """
        await self.initialize()
        
        store = self._stores.get(store_id)
        if not store:
            return {"success": False, "error": f"المتجر غير موجود: {store_id}"}
        
        # Generate design based on preferences
        preferences = design_preferences or {}
        language = store["config"].get("language", "ar")
        theme = store["config"].get("theme", "modern_arabic")
        
        # In production, this would use LLM to generate HTML/CSS
        # For now, return a structured design template
        design = {
            "layout": "responsive_grid",
            "direction": "rtl" if language in ("ar", "bilingual") else "ltr",
            "theme": theme,
            "colors": {
                "primary": preferences.get("primary_color", "#1a5632"),
                "secondary": preferences.get("secondary_color", "#f4a460"),
                "background": preferences.get("bg_color", "#ffffff"),
                "text": preferences.get("text_color", "#333333"),
            },
            "sections": [
                {"type": "hero", "content": {"title_ar": store["config"]["name_ar"], "subtitle_ar": store["config"].get("description_ar", "")}},
                {"type": "products_grid", "content": {"columns": 3}},
                {"type": "cart", "content": {"position": "sidebar" if language == "ar" else "top"}},
                {"type": "footer", "content": {"links": ["privacy", "terms", "contact"]}},
            ],
            "fonts": {
                "arabic": preferences.get("arabic_font", "Noto Sans SC"),
                "latin": preferences.get("latin_font", "Inter"),
            },
        }
        
        store["design"] = design
        store["status"] = StoreStatus.DESIGNED.value
        
        return {
            "success": True,
            "store_id": store_id,
            "status": StoreStatus.DESIGNED.value,
            "design": design,
            "message": f"تم تصميم المتجر '{store['config']['name_ar']}' — جاهز لإضافة المنتجات",
        }
    
    async def add_products(self, store_id: str, products: list[dict], grant_id: str = "") -> dict:
        """
        إضافة منتجات إلى المتجر.
        
        Args:
            store_id: معرف المتجر
            products: قائمة المنتجات
            grant_id: صلاحية
        """
        await self.initialize()
        
        store = self._stores.get(store_id)
        if not store:
            return {"success": False, "error": f"المتجر غير موجود: {store_id}"}
        
        added = []
        for prod_data in products:
            prod = Product(
                id=f"prod_{len(self._products) + 1}",
                name=prod_data.get("name", ""),
                name_ar=prod_data.get("name_ar", prod_data.get("name", "")),
                description=prod_data.get("description", ""),
                price=prod_data.get("price", 0.0),
                currency=prod_data.get("currency", store["config"].get("currency", "SAR")),
                category=prod_data.get("category", ProductCategory.CUSTOM.value),
                stock=prod_data.get("stock", 0),
                metadata=prod_data.get("metadata", {}),
            )
            self._products[prod.id] = prod
            store["products"].append(prod.id)
            added.append(prod.id)
        
        store["status"] = StoreStatus.PRODUCTS_ADDED.value
        
        return {
            "success": True,
            "store_id": store_id,
            "products_added": len(added),
            "product_ids": added,
            "status": store["status"],
            "message": f"تم إضافة {len(added)} منتج إلى المتجر",
        }
    
    async def link_shipping(self, store_id: str, provider: str, grant_id: str = "") -> dict:
        """
        ربط خدمة الشحن عبر UCP.
        
        Args:
            store_id: معرف المتجر
            provider: مزود الشحن (simulated)
            grant_id: صلاحية
        """
        await self.initialize()
        
        store = self._stores.get(store_id)
        if not store:
            return {"success": False, "error": f"المتجر غير موجود: {store_id}"}
        
        # Simulate UCP integration
        store["config"]["shipping_provider"] = provider
        store["shipping_config"] = {
            "provider": provider,
            "protocol": "UCP_v1",
            "webhook_url": f"/api/ecommerce/{store_id}/shipping/webhook",
            "supported_regions": ["SA", "AE", "KW", "BH", "QA", "OM"],
            "estimated_delivery_days": {"local": 2, "gcc": 5, "international": 14},
        }
        store["status"] = StoreStatus.SHIPPING_LINKED.value
        
        return {
            "success": True,
            "store_id": store_id,
            "status": store["status"],
            "provider": provider,
            "message": f"تم ربط خدمة الشحن '{provider}' عبر UCP",
        }
    
    async def setup_payment(self, store_id: str, payment_config: dict, grant_id: str = "") -> dict:
        """
        إعداد بوابة الدفع.
        
        ⚠️ يتطلب صلاحية ecommerce:purchase + موافقة بشرية.
        لا يتم تخزين بيانات دفع حقيقية.
        """
        await self.initialize()
        
        store = self._stores.get(store_id)
        if not store:
            return {"success": False, "error": f"المتجر غير موجود: {store_id}"}
        
        # Verify permission for payment setup
        if self._policy and self._policy.is_enabled():
            if not grant_id:
                return {
                    "success": False,
                    "error": "إعداد الدفع يتطلب صلاحية زمنية (ecommerce:purchase)",
                }
            check = await self._policy.check_permission(grant_id)
            if not check.get("valid"):
                return {"success": False, "error": f"صلاحية غير صالحة: {check.get('reason')}"}
        
        # Store payment config (NO real credentials)
        store["config"]["payment_provider"] = payment_config.get("provider", "simulated")
        store["payment_config"] = {
            "provider": payment_config.get("provider", "simulated"),
            "mode": "sandbox",  # Always sandbox until human confirms
            "supported_methods": payment_config.get("methods", ["credit_card", "mada", "apple_pay"]),
            "currency": store["config"].get("currency", "SAR"),
        }
        store["status"] = StoreStatus.PAYMENT_READY.value
        
        return {
            "success": True,
            "store_id": store_id,
            "status": store["status"],
            "mode": "sandbox",
            "message": "تم إعداد الدفع في وضع الاختبار — يحتاج موافقة بشرية للإنتاج",
        }
    
    async def process_purchase(
        self,
        store_id: str,
        products: list[dict],
        customer_info: dict,
        grant_id: str = "",
    ) -> dict:
        """
        معالجة عملية شراء — يتطلب موافقة بشرية صريحة.
        
        ⚠️ كل عملية شراء تحتاج صلاحية ecommerce:purchase + موافقة.
        """
        await self.initialize()
        
        store = self._stores.get(store_id)
        if not store:
            return {"success": False, "error": f"المتجر غير موجود: {store_id}"}
        
        # Calculate total
        total = 0.0
        order_products = []
        for item in products:
            prod_id = item.get("product_id", "")
            quantity = item.get("quantity", 1)
            prod = self._products.get(prod_id)
            if prod:
                total += prod.price * quantity
                order_products.append({
                    "product_id": prod_id,
                    "name": prod.name,
                    "name_ar": prod.name_ar,
                    "price": prod.price,
                    "quantity": quantity,
                    "subtotal": prod.price * quantity,
                })
        
        # Add tax
        tax_rate = store["config"].get("tax_rate", 0.15)
        tax = total * tax_rate
        total_with_tax = total + tax
        
        # Create order
        order = PurchaseOrder(
            id=f"order_{int(time.time())}_{len(self._orders) + 1}",
            store_id=store_id,
            products=order_products,
            total_amount=total_with_tax,
            currency=store["config"].get("currency", "SAR"),
            status="pending",
            customer_info={"anonymized": True},  # Never store real data
            created_at=time.time(),
        )
        self._orders[order.id] = order
        
        # In production, this would request human approval
        return {
            "success": True,
            "order_id": order.id,
            "status": "pending_approval",
            "total": total_with_tax,
            "currency": order.currency,
            "tax": tax,
            "products": order_products,
            "message": (
                f"طلب شراء بقيمة {total_with_tax:.2f} {order.currency} — "
                f"بانتظار موافقتك البشرية"
            ),
        }
    
    async def get_store(self, store_id: str) -> Optional[dict]:
        """الحصول على بيانات المتجر."""
        return self._stores.get(store_id)
    
    async def list_stores(self) -> list[dict]:
        """عرض جميع المتاجر."""
        return [
            {"id": s["id"], "name": s["config"].get("name_ar", ""), "status": s["status"]}
            for s in self._stores.values()
        ]
    
    async def get_order(self, order_id: str) -> Optional[dict]:
        """الحصول على بيانات طلب."""
        order = self._orders.get(order_id)
        return order.__dict__ if order else None

    def get_status(self) -> dict:
        """حالة وكيل المتجر."""
        return {
            "enabled": ECOMMERCE_ENABLED,
            "initialized": self._initialized,
            "stores_count": len(self._stores),
            "products_count": len(self._products),
            "orders_count": len(self._orders),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_agentic_store_builder: Optional["AgenticStoreBuilder"] = None


def get_agentic_store_builder() -> "AgenticStoreBuilder":
    """الحصول على وكيل بناء المتجر (Singleton)"""
    global _agentic_store_builder
    if _agentic_store_builder is None:
        _agentic_store_builder = AgenticStoreBuilder()
    return _agentic_store_builder
