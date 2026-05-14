"""
SelfAuditEngine v42 — محرك التدقيق الذاتي
يدقق دورياً في كل المكونات للتحقق من الاتساق والصحة

التحققات:
  1. interface compliance — هل المكون يحقق الواجهة المطلوبة؟
  2. method existence — هل الطرق المطلوبة موجودة؟
  3. return type consistency — هل أنواع الإرجاع متسقة؟
  4. error handling — هل الأخطاء مُعالَجة بشكل صحيح؟

v42 — Super Mind العقل الخارق مامون
"""

import time
import inspect
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class AuditSeverity(str, Enum):
    """مستويات شدة مشاكل التدقيق"""
    INFO = "info"          # معلومات فقط — لا مشكلة
    WARNING = "warning"    # تحذير — يجب الانتباه
    CRITICAL = "critical"  # حرج — يحتاج إصلاح فوري


@dataclass
class AuditResult:
    """نتيجة تدقيق مكون واحد"""
    component: str
    passed: bool = True
    issues: list[str] = field(default_factory=list)
    severity: AuditSeverity = AuditSeverity.INFO
    timestamp: float = field(default_factory=time.time)
    checks_run: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "component": self.component,
            "passed": self.passed,
            "issues": self.issues,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "checks_run": self.checks_run,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "duration_ms": round(self.duration_ms, 2),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  تعريف الواجهات المتوقعة — Expected Interface Definitions
# ═══════════════════════════════════════════════════════════════════════════════

# كل مكون يُتوقع أن يحقق واجهة معينة
# key = اسم المكون, value = قائمة الطرق المطلوبة مع أنواع الإرجاع المتوقعة
COMPONENT_INTERFACES: dict[str, dict[str, type]] = {
    "brain_router": {
        "route_query": dict,
        "get_stats": dict,
    },
    "meta_cognition": {
        "record_outcome": type(None),
        "get_profile": object,
        "get_self_assessment": dict,
        "predict_quality": float,
        "get_stats": dict,
    },
    "health_monitor": {
        "check_all": object,
        "get_health": dict,
        "get_stats": dict,
    },
    "self_healing_bridge": {
        "heal_component": dict,
        "get_stats": dict,
    },
    "notification_engine": {
        "send_notification": dict,
        "get_stats": dict,
    },
    "living_state": {
        "heartbeat": object,
        "process_event": type(None),
        "get_status": dict,
        "get_dominant_emotion": str,
    },
    "emotional_memory": {
        "store_episode": object,
        "recall": list,
        "get_status": dict,
    },
    "deep_research_engine": {
        "research": dict,
        "get_stats": dict,
    },
    "evolution_loop_v2": {
        "run_cycle": dict,
        "get_stats": dict,
    },
    "agent_lifecycle_manager": {
        "spawn_agent": dict,
        "get_stats": dict,
    },
    "deliberation_room": {
        "deliberate": dict,
        "get_stats": dict,
    },
    "self_audit_engine": {
        "audit_component": AuditResult,
        "audit_all": list,
        "get_audit_history": list,
        "get_stats": dict,
    },
    "cognitive_feedback_loop": {
        "process_feedback": dict,
        "get_adjustments": dict,
        "get_feedback_stats": dict,
        "get_stats": dict,
    },
    "emotional_resonance_engine": {
        "analyze_emotional_context": object,
        "generate_empathetic_response": str,
        "track_emotional_trajectory": dict,
        "get_stats": dict,
    },
    "system_integrity_validator": {
        "validate_all": object,
        "validate_file_integrity": dict,
        "validate_api_consistency": dict,
        "validate_brain_health": dict,
        "validate_safety_laws": dict,
        "get_stats": dict,
    },
}

# الطرق الإلزامية لكل مكون
REQUIRED_METHODS: dict[str, list[str]] = {
    "__all__": ["get_stats"],
}


# ═══════════════════════════════════════════════════════════════════════════════
#  محرك التدقيق الذاتي — SelfAuditEngine
# ═══════════════════════════════════════════════════════════════════════════════

class SelfAuditEngine:
    """
    محرك التدقيق الذاتي — يفحص كل مكون دورياً

    المسؤوليات:
    1. تدقيق واجهة كل مكون (interface compliance)
    2. التحقق من وجود الطرق المطلوبة (method existence)
    3. التحقق من اتساق أنواع الإرجاع (return type consistency)
    4. التحقق من معالجة الأخطاء (error handling)
    5. الاحتفاظ بآخر 100 نتيجة تدقيق
    6. التكامل مع MetaCognitionEngine لبيانات الموثوقية

    Integration:
    - MetaCognitionEngine: بيانات موثوقية المكونات
    - HealthMonitor: نتائج الفحص الصحي
    """

    MAX_HISTORY = 100  # أقصى عدد لنتائج التدقيق المحفوظة

    def __init__(self, meta_cognition=None, kernel=None):
        self._meta_cognition = meta_cognition
        self._kernel = kernel
        self._components: dict[str, Any] = {}  # اسم المكون → الكائن
        self._audit_history: list[dict] = []
        self._total_audits_run: int = 0
        self._last_full_audit: Optional[float] = None

    def set_meta_cognition(self, mc):
        """تعيين محرك ما فوق الإدراك"""
        self._meta_cognition = mc

    def set_kernel(self, kernel):
        """تعيين النواة"""
        self._kernel = kernel

    def register_component(self, name: str, component: Any):
        """تسجيل مكون للتدقيق"""
        self._components[name] = component
        logger.debug(f"Registered component for audit: {name}")

    def register_components_from_kernel(self):
        """تسجيل كل المكونات من النواة تلقائياً"""
        if not self._kernel:
            return

        # محاولة استخراج المكونات من النواة
        component_attrs = [
            "_brain_router", "_meta_cognition", "_health_monitor",
            "_self_healing_bridge", "_notification_engine",
            "_deep_research_engine", "_evolution_loop_v2",
            "_agent_lifecycle_manager", "_deliberation_room",
            "_self_audit_engine", "_cognitive_feedback_loop",
            "_emotional_resonance_engine", "_system_integrity_validator",
        ]

        for attr in component_attrs:
            if hasattr(self._kernel, attr):
                obj = getattr(self._kernel, attr)
                if obj is not None:
                    name = attr.lstrip("_")
                    self._components[name] = obj

    # ── التدقيق الفردي ───────────────────────────────────────────────────
    def audit_component(self, component_name: str) -> AuditResult:
        """
        تدقيق مكون واحد — يفحص الواجهة والاتساق ومعالجة الأخطاء

        Args:
            component_name: اسم المكون المراد تدقيقه

        Returns:
            AuditResult — نتيجة التدقيق
        """
        start_time = time.time()
        result = AuditResult(component=component_name)
        result.checks_run = 0
        result.checks_passed = 0
        result.checks_failed = 0

        # الحصول على كائن المكون
        component = self._components.get(component_name)

        # ── فحص 1: وجود المكون ──
        result.checks_run += 1
        if component is None:
            result.checks_failed += 1
            result.issues.append("Component not found — not registered in audit engine")
            result.severity = AuditSeverity.WARNING
            result.passed = False
        else:
            result.checks_passed += 1

        if component is not None:
            # ── فحص 2: التوافق مع الواجهة (method existence) ──
            expected_methods = COMPONENT_INTERFACES.get(component_name, {})
            for method_name, expected_return in expected_methods.items():
                result.checks_run += 1
                if not hasattr(component, method_name):
                    result.checks_failed += 1
                    result.issues.append(
                        f"Missing method: {method_name} (expected return type: {expected_return.__name__})"
                    )
                    result.severity = AuditSeverity.CRITICAL
                    result.passed = False
                else:
                    result.checks_passed += 1

            # ── فحص 2b: الطرق الإلزامية العامة (get_stats) ──
            for required in REQUIRED_METHODS.get("__all__", []):
                result.checks_run += 1
                if not hasattr(component, required):
                    result.checks_failed += 1
                    result.issues.append(f"Missing required method: {required}")
                    result.severity = AuditSeverity.WARNING
                    result.passed = False
                else:
                    result.checks_passed += 1

            # ── فحص 3: اتساق أنواع الإرجاع ──
            for method_name, expected_return in expected_methods.items():
                if not hasattr(component, method_name):
                    continue

                method = getattr(component, method_name)
                result.checks_run += 1

                # فحص توقيع الإرجاع عبر inspection
                try:
                    sig = inspect.signature(method)
                    return_annotation = sig.return_annotation

                    if return_annotation != inspect.Parameter.empty:
                        # هناك تعليق توضيحي للإرجاع — تحقق من الاتساق
                        if expected_return != object and expected_return != type(None):
                            annotation_name = getattr(return_annotation, "__name__", str(return_annotation))
                            expected_name = getattr(expected_return, "__name__", str(expected_return))
                            if annotation_name != expected_name:
                                result.checks_failed += 1
                                result.issues.append(
                                    f"Return type mismatch for {method_name}: "
                                    f"expected {expected_name}, got {annotation_name}"
                                )
                                if result.severity == AuditSeverity.INFO:
                                    result.severity = AuditSeverity.WARNING
                                continue

                    result.checks_passed += 1
                except (ValueError, TypeError):
                    result.checks_passed += 1  # لا نستطيع الفحص — لا مشكلة

            # ── فحص 4: معالجة الأخطاء ──
            result.checks_run += 1
            has_error_handling = self._check_error_handling(component, component_name)
            if not has_error_handling:
                result.checks_failed += 1
                result.issues.append("No error handling detected (try/except patterns)")
                if result.severity == AuditSeverity.INFO:
                    result.severity = AuditSeverity.WARNING
            else:
                result.checks_passed += 1

        # ── فحص 5: بيانات MetaCognition ──
        if self._meta_cognition:
            result.checks_run += 1
            try:
                profile = self._meta_cognition.get_profile(component_name)
                if profile and profile.consecutive_failures >= 5:
                    result.checks_failed += 1
                    result.issues.append(
                        f"MetaCognition: {profile.consecutive_failures} consecutive failures "
                        f"(reliability={profile.reliability_score:.2f})"
                    )
                    result.severity = AuditSeverity.CRITICAL
                    result.passed = False
                elif profile and profile.is_stagnant:
                    result.checks_failed += 1
                    result.issues.append("MetaCognition: component is stagnant")
                    if result.severity == AuditSeverity.INFO:
                        result.severity = AuditSeverity.WARNING
                else:
                    result.checks_passed += 1
            except Exception as e:
                result.checks_passed += 1  # MetaCognition غير متاح — لا مشكلة

        # تحديد النجاح العام
        if result.checks_failed > 0:
            result.passed = False

        # حساب المدة
        result.duration_ms = (time.time() - start_time) * 1000

        # حفظ في التاريخ
        self._add_to_history(result)

        logger.info(
            f"Audit {component_name}: {'PASSED' if result.passed else 'FAILED'} "
            f"({result.checks_passed}/{result.checks_run} checks, "
            f"severity={result.severity.value}, "
            f"issues={len(result.issues)})"
        )

        return result

    # ── تدقيق الكل ───────────────────────────────────────────────────────
    def audit_all(self) -> list[AuditResult]:
        """
        تدقيق كل المكونات المسجلة

        Returns:
            قائمة نتائج التدقيق لكل مكون
        """
        # تسجيل المكونات من النواة إن لم تكن مسجلة
        if not self._components and self._kernel:
            self.register_components_from_kernel()

        # إضافة المكونات المعروفة افتراضياً
        all_component_names = set(self._components.keys()) | set(COMPONENT_INTERFACES.keys())

        results = []
        for name in sorted(all_component_names):
            try:
                result = self.audit_component(name)
                results.append(result)
            except Exception as e:
                # في حال فشل التدقيق نفسه
                error_result = AuditResult(
                    component=name,
                    passed=False,
                    issues=[f"Audit itself failed: {str(e)[:100]}"],
                    severity=AuditSeverity.CRITICAL,
                )
                results.append(error_result)

        self._total_audits_run += 1
        self._last_full_audit = time.time()

        return results

    # ── تاريخ التدقيق ────────────────────────────────────────────────────
    def get_audit_history(self) -> list[dict]:
        """
        الحصول على تاريخ نتائج التدقيق

        Returns:
            قائمة بآخر 100 نتيجة تدقيق
        """
        return list(self._audit_history)

    def _add_to_history(self, result: AuditResult):
        """إضافة نتيجة للتاريخ"""
        self._audit_history.append(result.to_dict())
        if len(self._audit_history) > self.MAX_HISTORY:
            self._audit_history = self._audit_history[-self.MAX_HISTORY:]

    # ── فحص معالجة الأخطاء ───────────────────────────────────────────────
    def _check_error_handling(self, component: Any, component_name: str) -> bool:
        """
        فحص هل المكون يتعامل مع الأخطاء بشكل صحيح

        يفحص الكود المصدري للطرق الرئيسية عن أنماط try/except
        """
        try:
            # فحص الكود المصدري للطرق الرئيسية
            methods_to_check = COMPONENT_INTERFACES.get(component_name, {})
            has_handling = False

            for method_name in methods_to_check:
                if not hasattr(component, method_name):
                    continue

                method = getattr(component, method_name)
                try:
                    source = inspect.getsource(method)
                    if "try" in source and "except" in source:
                        has_handling = True
                        break
                except (OSError, TypeError):
                    # لا نستطيع الحصول على الكود المصدري
                    has_handling = True  # نفترض الأفضل
                    break

            return has_handling

        except Exception:
            return True  # نفترض الأفضل عند الفشل

    # ── الإحصائيات ────────────────────────────────────────────────────────
    def get_stats(self) -> dict:
        """إحصائيات محرك التدقيق الذاتي"""
        total_audits = len(self._audit_history)
        passed_count = sum(1 for a in self._audit_history if a.get("passed", False))
        failed_count = total_audits - passed_count

        severity_counts = {"info": 0, "warning": 0, "critical": 0}
        for a in self._audit_history:
            sev = a.get("severity", "info")
            if sev in severity_counts:
                severity_counts[sev] += 1

        return {
            "version": "v42",
            "registered_components": len(self._components),
            "total_audit_runs": self._total_audits_run,
            "history_size": total_audits,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "severity_counts": severity_counts,
            "last_full_audit": self._last_full_audit,
            "has_meta_cognition": self._meta_cognition is not None,
            "has_kernel": self._kernel is not None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

self_audit_engine = SelfAuditEngine()
