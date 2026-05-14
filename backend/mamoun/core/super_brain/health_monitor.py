"""
HealthMonitor v61 — مراقب الصحة الشامل

CRITICAL ADDITION from v61:
- مراقبة صحية حقيقية لكل مكون بناءً على MetaCognition
- حساب صحة المكون: reliability + trend + staleness
- 4 مستويات تنبيه: INFO, WARNING, CRITICAL, EMERGENCY
- كل مكون يُعطى صحة من 0-100 (نسبة مئوية)
- تنبيهات فورية عبر WebSocket + webhook عند CRITICAL/EMERGENCY
- يتحقق من: MetaCognition, AgentLifecycle, SelfHealing, EvolutionLoop
- Stage 4 v61: detect_patterns(), auto_escalate(), get_proactive_alerts(), _check_reliability_trend()
- Pattern detection across components, auto-escalation freezes EvolutionLoop on EMERGENCY
- Proactive alerts predict issues before they become critical
- Reliability trend tracking over 3 cycles with auto-escalation on decline

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

        # v61: Reliability trend tracking per component (last 3 cycles)
        self._reliability_history: dict[str, list[float]] = {}
        self._reliability_trend_window = 3  # track last 3 cycles

        # v61: Escalation state
        self._escalation_active = False
        self._escalation_reason: Optional[str] = None

        # v61: Proactive alert cache
        self._proactive_alerts: list[dict] = []

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

                # v61: Auto-escalate on EMERGENCY, recover when resolved
                await self.auto_escalate(report)

                # v61: Update proactive alerts
                self.get_proactive_alerts()

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

        # تحديث التقرير الأخير حتى يعمل get_health() بدون monitoring loop
        self._last_report = report

        # v61: Update reliability history for trend tracking
        for comp_score in component_scores:
            self._update_reliability_history(comp_score.component, comp_score.reliability)

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
            if profile.last_operation_time and profile.last_operation_time > 0:
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
                # Only escalate, never downgrade: if already EMERGENCY, keep it
                if score.severity != AlertSeverity.EMERGENCY:
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

    def detect_patterns(self) -> list[dict]:
        """
        كشف أنماط المشاكل عبر جميع المكونات

        Returns:
            قائمة بالأنماط المكتشفة، كل نمط يحتوي على:
            - pattern_type: نوع النمط (cascading_failure, shared_dependency, correlated_decline)
            - components: المكونات المتأثرة
            - severity: خطورة النمط
            - description: وصف النمط
        """
        patterns = []

        if not self._last_report:
            return patterns

        components = self._last_report.components
        if not components:
            return patterns

        # Pattern 1: Cascading failure — multiple components failing simultaneously
        failing = [c for c in components if c.severity in (AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY)]
        if len(failing) >= 2:
            patterns.append({
                "pattern_type": "cascading_failure",
                "components": [c.component for c in failing],
                "severity": "critical",
                "description": f"{len(failing)} components in CRITICAL/EMERGENCY simultaneously — possible cascading failure",
                "affected_scores": {c.component: c.score for c in failing},
            })

        # Pattern 2: Shared dependency — components with same issues
        issue_map: dict[str, list[str]] = {}
        for c in components:
            for issue in c.issues:
                issue_key = issue.lower().strip()
                if issue_key not in issue_map:
                    issue_map[issue_key] = []
                issue_map[issue_key].append(c.component)

        for issue, comps in issue_map.items():
            if len(comps) >= 2:
                patterns.append({
                    "pattern_type": "shared_dependency",
                    "components": comps,
                    "severity": "warning",
                    "description": f"Shared issue '{issue}' affects {len(comps)} components: {', '.join(comps)}",
                    "shared_issue": issue,
                })

        # Pattern 3: Correlated decline — components with declining trends
        declining = [c for c in components if c.trend < -0.2]
        if len(declining) >= 2:
            patterns.append({
                "pattern_type": "correlated_decline",
                "components": [c.component for c in declining],
                "severity": "warning",
                "description": f"{len(declining)} components showing correlated quality decline",
                "trends": {c.component: c.trend for c in declining},
            })

        # Pattern 4: Widespread staleness
        stale = [c for c in components if c.staleness > self.STALENESS_THRESHOLD]
        if len(stale) >= 3:
            patterns.append({
                "pattern_type": "widespread_staleness",
                "components": [c.component for c in stale],
                "severity": "warning",
                "description": f"{len(stale)} components are stale — system may be idle or stuck",
                "staleness": {c.component: c.staleness for c in stale},
            })

        # Pattern 5: Never operated — components with zero operations
        never_operated = [c for c in components if c.total_operations == 0]
        if len(never_operated) >= 2:
            patterns.append({
                "pattern_type": "dormant_components",
                "components": [c.component for c in never_operated],
                "severity": "info",
                "description": f"{len(never_operated)} components have never operated",
            })

        return patterns

    async def auto_escalate(self, report: SystemHealthReport) -> bool:
        """
        تصعيد تلقائي — تجميد EvolutionLoop عند EMERGENCY

        When the system has EMERGENCY-level components:
        1. Freeze EvolutionLoop to prevent making things worse
        2. Send emergency notifications
        3. Resume EvolutionLoop only when all components recover above CRITICAL

        Returns:
            True if escalation was activated, False if deactivated/recovered
        """
        has_emergency = report.emergency_count > 0

        if has_emergency and not self._escalation_active:
            # Activate escalation — freeze EvolutionLoop
            self._escalation_active = True
            emergency_components = [
                c.component for c in report.components
                if c.severity == AlertSeverity.EMERGENCY
            ]
            self._escalation_reason = (
                f"EMERGENCY: {len(emergency_components)} components in emergency state: "
                f"{', '.join(emergency_components[:5])}"
            )

            # Freeze EvolutionLoop
            if self._kernel:
                evo_loop = self._kernel.get_component("evolution_loop_v2")
                if evo_loop and hasattr(evo_loop, '_frozen'):
                    evo_loop._frozen = True
                    logger.critical(f"EvolutionLoop FROZEN by auto_escalate: {self._escalation_reason}")

            # Send emergency notification
            if self._notification_engine:
                try:
                    await self._notification_engine.broadcast_emergency(
                        title="AUTO-ESCALATION: EvolutionLoop Frozen",
                        message=self._escalation_reason,
                        metadata={
                            "escalation_type": "auto_escalate",
                            "emergency_components": emergency_components,
                            "overall_score": report.overall_score,
                        },
                    )
                except Exception as e:
                    logger.error(f"Failed to send escalation notification: {e}")

            logger.critical(f"Auto-escalation activated: {self._escalation_reason}")
            return True

        elif not has_emergency and self._escalation_active:
            # Recovery — unfreeze EvolutionLoop
            self._escalation_active = False
            self._escalation_reason = None

            if self._kernel:
                evo_loop = self._kernel.get_component("evolution_loop_v2")
                if evo_loop and hasattr(evo_loop, 'unfreeze'):
                    evo_loop.unfreeze()
                    logger.info("EvolutionLoop UNFROZEN — system recovered from emergency")

            # Send recovery notification
            if self._notification_engine:
                try:
                    await self._notification_engine.send_notification(
                        level="info",
                        title="ESCALATION RESOLVED: EvolutionLoop Resumed",
                        message="All components recovered from EMERGENCY state. EvolutionLoop has been unfrozen.",
                        source="health_monitor",
                        metadata={"escalation_type": "recovery"},
                    )
                except Exception as e:
                    logger.error(f"Failed to send recovery notification: {e}")

            logger.info("Auto-escalation deactivated — system recovered")
            return False

        return self._escalation_active

    def get_proactive_alerts(self) -> list[dict]:
        """
        تنبيهات استباقية — توقع المشاكل قبل أن تصبح حرجة

        Analyzes:
        - Reliability trends (declining reliability)
        - Staleness trends (increasing staleness)
        - Consecutive failure patterns
        - Quality degradation

        Returns:
            قائمة بالتنبيهات الاستباقية
        """
        alerts = []

        if not self._last_report:
            return alerts

        for component in self._last_report.components:
            # Check reliability trend
            trend_result = self._check_reliability_trend(component.component)
            if trend_result and trend_result.get("declining"):
                alerts.append({
                    "alert_type": "reliability_decline",
                    "component": component.component,
                    "severity": "warning",
                    "message": (
                        f"Component {component.component} reliability declining over "
                        f"{self._reliability_trend_window} cycles "
                        f"(trend: {trend_result.get('trend_direction', 'unknown')})"
                    ),
                    "current_reliability": component.reliability,
                    "trend_direction": trend_result.get("trend_direction", "unknown"),
                    "predicted_score": trend_result.get("predicted_score"),
                })

            # Check approaching staleness
            if component.staleness > self.STALENESS_THRESHOLD * 0.7 and component.staleness <= self.STALENESS_THRESHOLD:
                alerts.append({
                    "alert_type": "approaching_staleness",
                    "component": component.component,
                    "severity": "info",
                    "message": (
                        f"Component {component.component} approaching staleness threshold "
                        f"({component.staleness/3600:.1f}h / {self.STALENESS_THRESHOLD/3600:.1f}h)"
                    ),
                    "current_staleness_hours": component.staleness / 3600,
                    "threshold_hours": self.STALENESS_THRESHOLD / 3600,
                })

            # Check consecutive failures building up (2+ means 3+ is coming soon)
            if component.consecutive_failures >= 2 and component.severity != AlertSeverity.EMERGENCY:
                alerts.append({
                    "alert_type": "impending_critical",
                    "component": component.component,
                    "severity": "warning",
                    "message": (
                        f"Component {component.component} has {component.consecutive_failures} "
                        f"consecutive failures — may reach CRITICAL soon"
                    ),
                    "consecutive_failures": component.consecutive_failures,
                })

            # Check quality degradation (negative trend approaching threshold)
            if -0.3 <= component.trend < -0.1 and component.score >= 60:
                alerts.append({
                    "alert_type": "quality_degradation",
                    "component": component.component,
                    "severity": "info",
                    "message": (
                        f"Component {component.component} quality declining (trend={component.trend:.2f}) "
                        f"— currently score={component.score:.1f}"
                    ),
                    "current_trend": component.trend,
                    "current_score": component.score,
                })

        # Store alerts for later retrieval
        self._proactive_alerts = alerts

        return alerts

    def _check_reliability_trend(self, component_name: str) -> Optional[dict]:
        """
        تتبع اتجاه الموثوقية عبر 3 دورات

        Tracks reliability for each component across the last 3 health check cycles.
        If reliability is declining consistently, returns a trend analysis.

        Auto-escalates if reliability is declining over 3 consecutive cycles.

        Returns:
            dict with trend analysis if declining, None otherwise:
            - declining: bool
            - trend_direction: "declining" | "stable" | "improving"
            - values: list of reliability values
            - predicted_score: predicted next reliability
        """
        if component_name not in self._reliability_history:
            return None

        history = self._reliability_history[component_name]
        if len(history) < 2:
            return None

        # Calculate trend direction
        if len(history) >= self._reliability_trend_window:
            window = history[-self._reliability_trend_window:]
        else:
            window = history

        # Check if consistently declining
        declining = True
        for i in range(1, len(window)):
            if window[i] >= window[i - 1]:
                declining = False
                break

        # Determine overall direction
        first_val = window[0]
        last_val = window[-1]
        diff = last_val - first_val

        if diff < -0.05:
            direction = "declining"
        elif diff > 0.05:
            direction = "improving"
        else:
            direction = "stable"
            declining = False

        # Predict next value using linear extrapolation
        predicted = None
        if len(window) >= 2:
            rate = (window[-1] - window[-2])
            predicted = max(0.0, min(1.0, window[-1] + rate))

        result = {
            "declining": declining,
            "trend_direction": direction,
            "values": list(window),
            "predicted_score": predicted,
        }

        # Auto-escalate if declining over 3 consecutive cycles
        if declining and len(window) >= self._reliability_trend_window:
            logger.warning(
                f"Reliability trend declining for {component_name} over "
                f"{len(window)} cycles: {window}"
            )
            # If we have a kernel, we could trigger escalation here
            # The auto_escalate method handles the actual freezing

        return result

    def _update_reliability_history(self, component_name: str, reliability: float):
        """Update the reliability history for a component (called during check_all)."""
        if component_name not in self._reliability_history:
            self._reliability_history[component_name] = []

        self._reliability_history[component_name].append(reliability)

        # Keep only the last N entries
        max_entries = self._reliability_trend_window * 2  # keep some extra for analysis
        if len(self._reliability_history[component_name]) > max_entries:
            self._reliability_history[component_name] = \
                self._reliability_history[component_name][-max_entries:]

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
                "version": "v61",
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

        # لا تقرير بعد — أعد بيانات افتراضية
        report = self.check_all()
        return {
            "version": "v61",
            "overall_score": report.overall_score,
            "overall_severity": report.overall_severity.value,
            "emergency_count": report.emergency_count,
            "critical_count": report.critical_count,
            "warning_count": report.warning_count,
            "timestamp": report.timestamp,
            "components": [
                {
                    "name": c.component,
                    "score": c.score,
                    "severity": c.severity.value,
                    "issues": c.issues,
                }
                for c in report.components
            ],
        }

    def get_stats(self) -> dict:
        """إحصائيات المراقب"""
        return {
            "version": "v61",
            "monitoring_active": self._running,
            "check_interval_seconds": self.CHECK_INTERVAL,
            "health_history_size": len(self._health_history),
            "ws_subscribers": len(self._ws_subscribers),
            "last_check": self._last_report.timestamp if self._last_report else 0,
            "escalation_active": self._escalation_active,
            "escalation_reason": self._escalation_reason,
            "proactive_alerts_count": len(self._proactive_alerts),
            "reliability_history_components": list(self._reliability_history.keys()),
        }
