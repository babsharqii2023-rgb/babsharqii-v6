"""
BABSHARQII v12.0 — E-commerce Agents Package
وكلاء التجارة الإلكترونية — بناء متجر + ربط موردين
"""

import os

ECOMMERCE_ENABLED = os.getenv("MAMOUN_ECOMMERCE_MODE", "false").lower() == "true"

from mamoun.agents.ecommerce.agentic_store_builder import AgenticStoreBuilder
from mamoun.agents.ecommerce.supplier_connector import SupplierConnector

__all__ = [
    "AgenticStoreBuilder",
    "SupplierConnector",
    "ECOMMERCE_ENABLED",
]
