"""
HealthDashboard v60 — لوحة القيادة الصحية

CRITICAL ADDITION from v60:
- يعرض حالة كل مكون من MetaCognition
- 5 مقاييس رئيسية: reliability, quality_trend, operations, failures, latency
- تنبيهات بصرية عند انخفاض الصحة
- يدعم كل المكونات الـ 19+ في الكيرنل

v60 — Super Mind العقل الخارق مامون
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class HealthLevel(str, Enum):
    """مستويات الصحة"""
    EXCELLENT = "excellent"  # > 0.9
    GOOD = "good"           # 0.7 - 0.9
    WARNING = "warning"     # 0.5 - 0.7
    CRITICAL = "critical"   # 0.3 - 0.5
    EMERGENCY = "emergency" # < 0.3


@dataclass
class ComponentHealthCard:
    """بطاقة صحة مكون واحد"""
    name: str
    health_level: HealthLevel = HealthLevel.GOOD
    reliability_score: float = 0.0
    quality_trend: float = 0.0
    total_operations: int = 0
    consecutive_failures: int = 0
    avg_latency_ms: float = 0.0
    last_operation_time: float = 0.0
    is_active: bool = True
    issues: list[str] = field(default_factory=list)


@dataclass
class SystemHealthSummary:
    """ملخص صحة النظام الكلي"""
    overall_health: float = 0.0
    health_level: HealthLevel = HealthLevel.GOOD
    total_components: int = 0
    healthy_components: int = 0
    warning_components: int = 0
    critical_components: int = 0
    emergency_components: int = 0
    component_cards: list[ComponentHealthCard] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    version: str = "v60"


class HealthDashboard:
    """
    لوحة القيادة الصحية — عرض شامل لحالة كل مكون

    المسؤوليات:
    1. جمع بيانات الصحة من MetaCognition لكل مكون
    2. تصنيف كل مكون حسب مستوى الصحة
    3. حساب الصحة الإجمالية للنظام
    4. كشف المكونات غير الصحية وإصدار تنبيهات
    5. توفير واجهة عرض للواجهة الأمامية

    Integration:
    - MetaCognitionEngine: مصدر بيانات الصحة
    - Kernel: قائمة المكونات المسجلة
    - NotificationEngine: إرسال تنبيهات
    """

    def __init__(self, meta_cognition=None, kernel=None, notification_engine=None):
        self._meta_cognition = meta_cognition
        self._kernel = kernel
        self._notification_engine = notification_engine
        self._last_snapshot: Optional[SystemHealthSummary] = None

    def set_meta_cognition(self, meta_cognition):
        self._meta_cognition = meta_cognition

    def set_kernel(self, kernel):
        self._kernel = kernel

    def set_notification_engine(self, engine):
        self._notification_engine = engine

    def generate_snapshot(self) -> SystemHealthSummary:
        """
        إنشاء لقطة لحالة النظام الكامل

        تجمع البيانات من:
        1. Kernel — قائمة المكونات المسجلة
        2. MetaCognition — بيانات الأداء لكل مكون
        3. تُصدِّر تنبيهات عند الحاجة
        """
        component_cards = []
        component_names = []

        # جمع أسماء المكونات من الكيرنل
        if self._kernel and hasattr(self._kernel, '_components'):
            component_names = list(self._kernel._components.keys())
        elif self._kernel and hasattr(self._kernel, 'get_component'):
            # محاولة بديلة
            component_names = [
                "meta_cognition", "llm_client", "web_search", "brain_router",
                "deliberation_room", "deep_research", "self_modifier",
                "full_self_rewriter", "improvement_proposer", "tool_creator",
                "agent_creator", "external_project_controller",
                "evolution_loop_v2", "research_to_update_pipeline",
                "agent_lifecycle_manager", "self_healing_bridge",
                "rlhf_bridge", "variant_archive", "notification_engine",
            ]

        for name in component_names:
            card = self._build_health_card(name)
            component_cards.append(card)

        # حساب الصحة الإجمالية
        if component_cards:
            overall = sum(c.reliability_score for c in component_cards) / len(component_cards)
        else:
            overall = 0.0

        # تصنيف المكونات
        healthy = sum(1 for c in component_cards if c.health_level in (HealthLevel.EXCELLENT, HealthLevel.GOOD))
        warning = sum(1 for c in component_cards if c.health_level == HealthLevel.WARNING)
        critical = sum(1 for c in component_cards if c.health_level == HealthLevel.CRITICAL)
        emergency = sum(1 for c in component_cards if c.health_level == HealthLevel.EMERGENCY)

        # تحديد المستوى العام
        if emergency > 0:
            level = HealthLevel.EMERGENCY
        elif critical > len(component_cards) * 0.3:
            level = HealthLevel.CRITICAL
        elif warning > len(component_cards) * 0.5:
            level = HealthLevel.WARNING
        elif overall >= 0.7:
            level = HealthLevel.GOOD
        else:
            level = HealthLevel.WARNING

        summary = SystemHealthSummary(
            overall_health=overall,
            health_level=level,
            total_components=len(component_cards),
            healthy_components=healthy,
            warning_components=warning,
            critical_components=critical,
            emergency_components=emergency,
            component_cards=component_cards,
        )

        self._last_snapshot = summary

        # إرسال تنبيهات للمكونات الحرجة
        self._check_for_alerts(summary)

        return summary

    def _build_health_card(self, component_name: str) -> ComponentHealthCard:
        """بناء بطاقة صحة لمكون واحد"""
        card = ComponentHealthCard(name=component_name)

        if self._meta_cognition:
            try:
                profile = self._meta_cognition.get_profile(component_name)
                if profile:
                    card.reliability_score = profile.reliability_score
                    card.quality_trend = profile.quality_trend
                    card.total_operations = profile.total_operations
                    card.consecutive_failures = profile.consecutive_failures
                    card.avg_latency_ms = profile.avg_latency_ms
                    card.last_operation_time = profile.last_operation_time
                else:
                    # لا بيانات — المكون لم يعمل بعد
                    card.reliability_score = 0.5
                    card.is_active = False
            except Exception as e:
                logger.debug(f"Failed to get health for {component_name}: {e}")
                card.reliability_score = 0.5

        # تحديد المستوى
        if card.reliability_score >= 0.9:
            card.health_level = HealthLevel.EXCELLENT
        elif card.reliability_score >= 0.7:
            card.health_level = HealthLevel.GOOD
        elif card.reliability_score >= 0.5:
            card.health_level = HealthLevel.WARNING
        elif card.reliability_score >= 0.3:
            card.health_level = HealthLevel.CRITICAL
        else:
            card.health_level = HealthLevel.EMERGENCY

        # كشف المشاكل
        if card.consecutive_failures >= 3:
            card.issues.append(f"{card.consecutive_failures} consecutive failures")
        if card.quality_trend < -0.2:
            card.issues.append(f"declining quality ({card.quality_trend:.2f})")
        if card.avg_latency_ms > 5000:
            card.issues.append(f"high latency ({card.avg_latency_ms:.0f}ms)")
        if card.total_operations == 0:
            card.issues.append("no operations recorded")

        return card

    def _check_for_alerts(self, summary: SystemHealthSummary):
        """إرسال تنبيهات للمكونات الحرجة"""
        if not self._notification_engine:
            return

        for card in summary.component_cards:
            if card.health_level == HealthLevel.EMERGENCY:
                try:
                    asyncio.ensure_future(self._notification_engine.send_notification(
                        level="emergency",
                        title=f"EMERGENCY: {card.name}",
                        message=f"Component {card.name} is in EMERGENCY state (health={card.reliability_score:.2f}). Issues: {', '.join(card.issues)}",
                        source="health_dashboard",
                        metadata={"component": card.name, "health": card.reliability_score},
                    ))
                except Exception:
                    pass
            elif card.health_level == HealthLevel.CRITICAL:
                try:
                    asyncio.ensure_future(self._notification_engine.send_notification(
                        level="critical",
                        title=f"CRITICAL: {card.name}",
                        message=f"Component {card.name} is CRITICAL (health={card.reliability_score:.2f}). Issues: {', '.join(card.issues)}",
                        source="health_dashboard",
                        metadata={"component": card.name, "health": card.reliability_score},
                    ))
                except Exception:
                    pass

    def get_dashboard_data(self) -> dict:
        """بيانات اللوحة للواجهة الأمامية"""
        if not self._last_snapshot:
            self.generate_snapshot()

        s = self._last_snapshot
        return {
            "version": s.version,
            "timestamp": s.timestamp,
            "overall_health": s.overall_health,
            "health_level": s.health_level.value,
            "summary": {
                "total": s.total_components,
                "healthy": s.healthy_components,
                "warning": s.warning_components,
                "critical": s.critical_components,
                "emergency": s.emergency_components,
            },
            "components": [
                {
                    "name": c.name,
                    "level": c.health_level.value,
                    "reliability": round(c.reliability_score, 3),
                    "trend": round(c.quality_trend, 3),
                    "operations": c.total_operations,
                    "failures": c.consecutive_failures,
                    "latency_ms": round(c.avg_latency_ms, 1),
                    "active": c.is_active,
                    "issues": c.issues,
                }
                for c in s.component_cards
            ],
        }

    def get_stats(self) -> dict:
        """إحصائيات اللوحة"""
        if not self._last_snapshot:
            return {"snapshots_taken": 0}

        return {
            "snapshots_taken": 1,
            "last_overall_health": self._last_snapshot.overall_health,
            "last_health_level": self._last_snapshot.health_level.value,
            "components_monitored": self._last_snapshot.total_components,
        }
