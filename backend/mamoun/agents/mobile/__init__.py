"""
BABSHARQII v12.0 — Mobile Agents Package
وكلاء تطبيقات الجوال — بناء ونشر تطبيقات React Native
"""

import os

MOBILE_BUILDER_ENABLED = os.getenv("MAMOUN_MOBILE_BUILDER", "false").lower() == "true"

from mamoun.agents.mobile.mobile_app_builder import MobileAppBuilder
from mamoun.agents.mobile.self_deployment import SelfDeployment

__all__ = [
    "MobileAppBuilder",
    "SelfDeployment",
    "MOBILE_BUILDER_ENABLED",
]
