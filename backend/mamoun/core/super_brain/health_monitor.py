"""
HealthMonitor v61 — مراقب الصحة الشامل

CRITICAL ADDITION from v61:
- مراقبة صحية حقيقية لكل مكون بناءً على MetaCognition
- حساب صحة المكون: reliability + trend + staleness
- 4 مستويات تنبيه: INFO, WARNING, CRITICAL, EMERGENCY
- كل مكون يُعطى صحة من 0-100 (نسبة مئوية)
- تنبيهات فورية عبر WebSocket + webhook عند CRITICAL/EMERGENCY
- يتحقق من: MetaCognition, AgentLifecycle, SelfHealing, EvolutionLoop

v61 — Super Mind العقل الخارق مامون
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """مستويات التنبيه"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ComponentHealthScore:
    """درجة صحة مكون (0-100)"""
    component: str
    score: float  # 0-100
    severity: AlertSeverity = AlertSeverity.INFO
    reliability: float = 0.0
    trend: float = 0.0
    staleness: float = 0.0  # زمن منذ آخر عملية (ثواني)
    consecutive_failures: int = 0
    total_operations: int = 0
    last_checked: float = field(default_factory=time.time)
    issues: list[str] = field(default_factory=list)


@dataclass
class SystemHealthReport:
    """تقرير صحة النظام الكامل"""
    overall_score: float  # 0-100
    overall_severity: AlertSeverity
    components: list[ComponentHealthScore]
    emergency_count: int = 0
    critical_count: int = 0
    warning_count: int = 0
    timestamp: float = field(default_factory=time.time)
    version: str = "v61"


class HealthMonitor:
    """
    مراقب الصحة الشامل — يراقب كل مكون في النظام

    المسؤوليات:
    1. فحص دوري لكل مكون (كل 30 ثانية)
    2. حساب درجة الصحة: reliability × (1 + trend) × (1 - staleness_penalty)
    3. إرسال تنبيهات عند الانخفاض الحاد
    4. توفير API endpoint للاستعلام
    5. إرسال WebSocket push عند EMERGENCY

    Formula:
    health_score = reliability * 100
    adjusted = health_score * (1 + quality_trend) * (1 - staleness_penalty)
    staleness_penalty = min(0.5, time_since_last_op / 3600)  # max 50% penalty

    Integration:
    - MetaCognitionEngine: مصدر بيانات reliability و quality_trend
    - AgentLifecycleManager: حالة الوكلاء
    - SelfHealingBridge: نتائج الشفاء
    - EvolutionLoopV2: نتائج التطور
    - NotificationEngine: إرسال التنبيهات
    """

    CHECK_INTERVAL = 30  # ثانية
    STALENESS_THRESHOLD = 3600  # ساعة واحدة بدون عمليات = stale

    def __init__(
        self,
        meta_cognition=None,
        kernel=None,
        notification_engine=None,
        neural_bus=None,
        healing_bridge=None,
    ):
        self._meta_cognition = meta_cognition
        self._kernel = kernel
        self._notification_engine = notification_engine
        self._neural_bus = neural_bus
        self._healing_bridge = healing_bridge

        self._last_report: Optional[SystemHealthReport] = None
        self._health_history: list[SystemHealthReport] = []
        self._running = False
        self._check_task: Optional[asyncio.Task] = None

        # WebSocket subscribers
        self._ws_subscribers: list[Callable] = []

    def set_meta_cognition(self, mc):
        self._meta_cognition = mc

    def set_kernel(self, kernel):
        self._kernel = kernel

    def set_notification_engine(self, ne):
        self._notification_engine = ne

    def set_neural_bus(self, nb):
        self._neural_bus = nb

    def set_healing_bridge(self, hb):
        self._healing_bridge = hb

    def subscribe_ws(self, callback: Callable):
        """اشتراك WebSocket لاستقبال تحديثات الصحة"""
        self._ws_subscribers.append(callback)

    async def start_monitoring(self):
        """بدء المراقبة الدورية"""
        if self._running:
            return
        self._running = True
        self._check_task = asyncio.create_task(self._monitoring_loop())
        logger.info("HealthMonitor v61 started")

    async def stop_monitoring(self):
        """إيقاف المراقبة"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("HealthMonitor stopped")

    async def _monitoring_loop(self):
        """حلقة المراقبة الدورية"""
        while self._running:
            try:
                report = self.check_all()
                self._last_report = report
                self._health_history.append(report)

                # الحفاظ على حجم التاريخ
                if len(self._health_history) > 2880:  # 24 ساعة بفارق 30 ثانية
                    self._health_history = self._health_history[-1440:]

                # إرسال تحديث عبر WebSocket
                await self._push_ws_update(report)

                # إرسال تنبيهات عند الحاجة
                await self._handle_alerts(report)

            except Exception as e:
                logger.error(f"HealthMonitor loop error: {e}")

            await asyncio.sleep(self.CHECK_INTERVAL)

    def check_all(self) -> SystemHealthReport:
        """فحص كل المكونات وإنتاج تقرير"""
        component_scores = []

        # جمع أسماء المكونات
        component_names = self._get_component_names()

        for name in component_names:
            score = self._check_component(name)
            component_scores.append(score)

        # حساب الصحة الإجمالية
        if component_scores:
            overall = sum(c.score for c in component_scores) / len(component_scores)
        else:
            overall = 50.0

        # تحديد المستوى العام
        emergency_count = sum(1 for c in component_scores if c.severity == AlertSeverity.EMERGENCY)
        critical_count = sum(1 for c in component_scores if c.severity == AlertSeverity.CRITICAL)
        warning_count = sum(1 for c in component_scores if c.severity == AlertSeverity.WARNING)

        if emergency_count > 0:
            overall_severity = AlertSeverity.EMERGENCY
        elif critical_count > len(component_scores) * 0.3:
            overall_severity = AlertSeverity.CRITICAL
        elif warning_count > len(component_scores) * 0.5:
            overall_severity = AlertSeverity.WARNING
        else:
            overall_severity = AlertSeverity.INFO

        report = SystemHealthReport(
            overall_score=overall,
            overall_severity=overall_severity,
            components=component_scores,
            emergency_count=emergency_count,
            critical_count=critical_count,
            warning_count=warning_count,
        )

        logger.info(
            f"Health check: overall={overall:.1f}/100 ({overall_severity.value}), "
            f"emergency={emergency_count}, critical={critical_count}, warning={warning_count}"
        )

        return report

    def _get_component_names(self) -> list[str]:
        """الحصول على أسماء المكونات المسجلة"""
        if self._kernel and hasattr(self._kernel, '_components'):
            return list(self._kernel._components.keys())

        # قائمة افتراضية
        return [
            "meta_cognition", "llm_client", "web_search", "brain_router",
            "deliberation_room", "deep_research", "self_modifier",
            "full_self_rewriter", "improvement_proposer", "tool_creator",
            "agent_creator", "external_project_controller",
            "evolution_loop_v2", "research_to_update_pipeline",
            "agent_lifecycle_manager", "self_healing_bridge",
            "rlhf_bridge", "variant_archive", "notification_engine",
            "health_dashboard", "health_monitor",
        ]

    def _check_component(self, name: str) -> ComponentHealthScore:
        """فحص مكون واحد وحساب درجة صحته"""
        score = ComponentHealthScore(component=name, score=50.0)

        if not self._meta_cognition:
            return score

        try:
            profile = self._meta_cognition.get_profile(name)
            if not profile:
                # لا بيانات — يحتاج تفعيل
                score.score = 50.0
                score.severity = AlertSeverity.WARNING
                score.issues.append("no data — component may not be active")
                return score

            # البيانات الأساسية
            score.reliability = profile.reliability_score
            score.trend = profile.quality_trend
            score.consecutive_failures = profile.consecutive_failures
            score.total_operations = profile.total_operations

            # حساب staleness
            if profile.last_operation_time > 0:
                score.staleness = time.time() - profile.last_operation_time
            else:
                score.staleness = float('inf')

            # حساب الدرجة: reliability * 100 * (1 + trend) * (1 - staleness_penalty)
            base_score = score.reliability * 100
            trend_bonus = max(-0.5, min(0.5, score.trend))  # حد أقصى ±50%
            staleness_penalty = min(0.5, score.staleness / self.STALENESS_THRESHOLD)

            adjusted = base_score * (1 + trend_bonus) * (1 - staleness_penalty)
            score.score = max(0.0, min(100.0, adjusted))

            # تحديد المستوى
            if score.score >= 80:
                score.severity = AlertSeverity.INFO
            elif score.score >= 60:
                score.severity = AlertSeverity.WARNING
            elif score.score >= 30:
                score.severity = AlertSeverity.CRITICAL
            else:
                score.severity = AlertSeverity.EMERGENCY

            # كشف المشاكل
            if score.consecutive_failures >= 3:
                score.issues.append(f"{score.consecutive_failures} consecutive failures")
                score.severity = AlertSeverity.CRITICAL
            if score.staleness > self.STALENESS_THRESHOLD:
                score.issues.append(f"stale for {score.staleness/3600:.1f} hours")
            if score.trend < -0.3:
                score.issues.append(f"declining quality ({score.trend:.2f})")
            if score.total_operations == 0:
                score.issues.append("never operated")

        except Exception as e:
            score.score = 0.0
            score.severity = AlertSeverity.EMERGENCY
            score.issues.append(f"check failed: {str(e)[:100]}")

        return score

    async def _push_ws_update(self, report: SystemHealthReport):
        """إرسال تحديث عبر WebSocket"""
        data = {
            "type": "health_update",
            "overall_score": report.overall_score,
            "overall_severity": report.overall_severity.value,
            "emergency_count": report.emergency_count,
            "critical_count": report.critical_count,
            "timestamp": report.timestamp,
        }

        for callback in self._ws_subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.debug(f"WS subscriber failed: {e}")

    async def _handle_alerts(self, report: SystemHealthReport):
        """معالجة التنبيهات"""
        if not self._notification_engine:
            return

        # تنبيهات EMERGENCY — إرسال فوري
        for component in report.components:
            if component.severity == AlertSeverity.EMERGENCY:
                try:
                    await self._notification_engine.send_notification(
                        level="emergency",
                        title=f"EMERGENCY: {component.component}",
                        message=f"Component {component.component} health={component.score:.1f}/100. Issues: {', '.join(component.issues)}",
                        source="health_monitor",
                        metadata={
                            "component": component.component,
                            "score": component.score,
                            "issues": component.issues,
                        },
                    )
                except Exception:
                    pass

                # تشغيل شفاء تلقائي
                if self._healing_bridge:
                    try:
                        await self._healing_bridge.heal_component(
                            component_name=component.component,
                            issue_description=f"EMERGENCY: {', '.join(component.issues)}",
                            severity="critical",
                        )
                    except Exception as e:
                        logger.error(f"Auto-healing failed for {component.component}: {e}")

    def get_health(self, component_name: str = None) -> dict:
        """الحصول على بيانات الصحة"""
        if component_name:
            score = self._check_component(component_name)
            return {
                "component": score.component,
                "score": score.score,
                "severity": score.severity.value,
                "reliability": score.reliability,
                "trend": score.trend,
                "staleness_seconds": score.staleness,
                "consecutive_failures": score.consecutive_failures,
                "total_operations": score.total_operations,
                "issues": score.issues,
            }

        if self._last_report:
            return {
                "overall_score": self._last_report.overall_score,
                "overall_severity": self._last_report.overall_severity.value,
                "emergency_count": self._last_report.emergency_count,
                "critical_count": self._last_report.critical_count,
                "warning_count": self._last_report.warning_count,
                "timestamp": self._last_report.timestamp,
                "components": [
                    {
                        "name": c.component,
                        "score": c.score,
                        "severity": c.severity.value,
                        "issues": c.issues,
                    }
                    for c in self._last_report.components
                ],
            }

        return {"status": "no_data", "version": "v61"}

    def get_stats(self) -> dict:
        """إحصائيات المراقب"""
        return {
            "monitoring_active": self._running,
            "check_interval_seconds": self.CHECK_INTERVAL,
            "health_history_size": len(self._health_history),
            "ws_subscribers": len(self._ws_subscribers),
            "last_check": self._last_report.timestamp if self._last_report else 0,
        }
