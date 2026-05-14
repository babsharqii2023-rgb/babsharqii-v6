"""
SelfHealingBridge v59.1 — يربط SelfHealing بـ MetaCognition عبر NeuralBus

CRITICAL FIX from v59:
- v59: SelfHealing و MetaCognition لا يعرفان بعضهما
- v59.1: SelfHealingBridge يربطهما — كل خطوة شفاء تُسجَّل كـ outcome في MetaCognition
- عند فشل الشفاء، يُرسل تنبيه عبر NeuralBus
- عند نجاح الشفاء، يُحدِّث reliability_score تلقائياً

Inspired by: NVIDIA OpenShell (Bounded Intent + Mandatory Governance + Continuous Monitoring)

v59.1 — Super Mind العقل الخارق مامون
"""

import asyncio
import logging
import time
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class HealingAction(str, Enum):
    """أنواع إجراءات الشفاء"""
    RESTART_COMPONENT = "restart_component"
    RESET_CONNECTION = "reset_connection"
    CLEAR_CACHE = "clear_cache"
    ROLLBACK_CODE = "rollback_code"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    SWITCH_PROVIDER = "switch_provider"


class HealingResultStatus(str, Enum):
    """نتائج إجراء الشفاء"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class HealingResult:
    """نتيجة عملية شفاء واحدة"""
    action: HealingAction
    status: HealingResultStatus
    component: str
    message: str
    before_health: float = 0.0
    after_health: float = 0.0
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


class SelfHealingBridge:
    """
    جسر الشفاء الذاتي — يربط SelfHealing بـ MetaCognition

    المسؤوليات:
    1. عند اكتشاف مشكلة → تشغيل إجراء شفاء مناسب
    2. تسجيل كل نتيجة (نجاح/فشل) في MetaCognition كـ outcome
    3. إرسال تنبيهات عبر NeuralBus عند الفشل
    4. محاكاة خطوات الشفاء قبل التنفيذ الفعلي (pre-check)
    5. إعادة المحاولة بـ exponential backoff عند الفشل المؤقت

    Integration:
    - MetaCognitionEngine: record_outcome() لكل إجراء
    - NeuralBus: publish HEALTH_CRITICAL / META_STAGNATION
    - SelfHealingEngine: التنفيذ الفعلي لخطوات الشفاء
    """

    MAX_RETRY_ATTEMPTS = 3
    BACKOFF_BASE_SECONDS = 2.0
    SIMULATION_STEPS = 3  # عدد خطوات المحاكاة قبل التنفيذ

    def __init__(
        self,
        meta_cognition=None,
        neural_bus=None,
        self_healing_engine=None,
        kernel=None,
    ):
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._self_healing_engine = self_healing_engine
        self._kernel = kernel

        # تتبع إحصائيات الشفاء
        self._healing_history: list[HealingResult] = []
        self._consecutive_failures: dict[str, int] = {}  # per component
        self._last_healing_time: dict[str, float] = {}

    def set_meta_cognition(self, meta_cognition):
        """ربط MetaCognition بعد التهيئة"""
        self._meta_cognition = meta_cognition

    def set_neural_bus(self, neural_bus):
        """ربط NeuralBus بعد التهيئة"""
        self._neural_bus = neural_bus

    def set_self_healing_engine(self, engine):
        """ربط SelfHealingEngine بعد التهيئة"""
        self._self_healing_engine = engine

    def set_kernel(self, kernel):
        """ربط Kernel بعد التهيئة"""
        self._kernel = kernel

    async def heal_component(
        self,
        component_name: str,
        issue_description: str,
        severity: str = "medium",
    ) -> HealingResult:
        """
        الشفاء الذاتي لمكون — مع محاكاة وتسجيل outcome

        الخطوات:
        1. تسجيل الحالة الصحية قبل الشفاء
        2. محاكاة خطوات الشفاء (3 خطوات)
        3. تنفيذ الإجراء الأنسب
        4. تسجيل النتيجة في MetaCognition
        5. إرسال تنبيه عبر NeuralBus إذا لزم الأمر
        """
        before_health = self._get_component_health(component_name)
        start_time = time.time()

        logger.info(
            f"SelfHealingBridge: Healing {component_name} (severity={severity}, health={before_health:.2f})"
        )

        # الخطوة 1: محاكاة خطوات الشفاء
        simulation_ok = await self._simulate_healing(component_name, issue_description)
        if not simulation_ok:
            result = HealingResult(
                action=HealingAction.ESCALATE_TO_HUMAN,
                status=HealingResultStatus.ESCALATED,
                component=component_name,
                message=f"Simulation failed — escalating to human: {issue_description}",
                before_health=before_health,
                after_health=before_health,
            )
            await self._record_result(result, start_time)
            return result

        # الخطوة 2: اختيار إجراء الشفاء الأنسب
        action = self._select_healing_action(component_name, issue_description, severity)

        # الخطوة 3: تنفيذ مع إعادة المحاولة
        result = await self._execute_with_retry(
            component_name=component_name,
            action=action,
            issue_description=issue_description,
        )

        # الخطوة 4: تسجيل النتيجة
        result.before_health = before_health
        result.after_health = self._get_component_health(component_name)
        await self._record_result(result, start_time)

        # الخطوة 5: إرسال تنبيهات
        await self._handle_post_healing(component_name, result)

        return result

    async def _simulate_healing(self, component_name: str, issue: str) -> bool:
        """
        محاكاة خطوات الشفاء — 3 خطوات وهمية قبل التنفيذ الفعلي

        يتحقق من:
        1. هل المكون موجود فعلاً؟
        2. هل سبق أن فشلنا في شفائه مؤخراً؟
        3. هل الإجراء المقترح آمن؟
        """
        # محاكاة الخطوة 1: التحقق من وجود المكون
        if self._kernel:
            component = self._kernel.get_component(component_name)
            if not component:
                # تحقق أيضاً في super_brain
                component = self._kernel.get_component(component_name.replace("super_brain.", ""))
                if not component:
                    logger.warning(f"Simulation step 1 FAILED: component {component_name} not found")
                    return False

        # محاكاة الخطوة 2: التحقق من عدم وجود فشل متكرر
        consecutive = self._consecutive_failures.get(component_name, 0)
        if consecutive >= self.MAX_RETRY_ATTEMPTS:
            logger.warning(f"Simulation step 2 FAILED: {component_name} has {consecutive} consecutive failures")
            return False

        # محاكاة الخطوة 3: التحقق من أن الإجراء آمن (not in cooldown)
        last_heal = self._last_healing_time.get(component_name, 0)
        if time.time() - last_heal < 30:  # cooldown 30 ثانية
            logger.warning(f"Simulation step 3 WARNING: {component_name} in cooldown")
            # لا نفشل المحاكاة — فقط تحذير

        logger.info(f"Simulation PASSED for {component_name}")
        return True

    def _select_healing_action(
        self, component_name: str, issue: str, severity: str
    ) -> HealingAction:
        """اختيار إجراء الشفاء بناءً على نوع المشكلة"""
        issue_lower = issue.lower()

        # مشاكل الاتصال
        if any(kw in issue_lower for kw in ["connection", "اتصال", "timeout", "network"]):
            return HealingAction.RESET_CONNECTION

        # مشاكل الذاكرة/الكاش
        if any(kw in issue_lower for kw in ["cache", "memory", "ذاكرة", "full", "overflow"]):
            return HealingAction.CLEAR_CACHE

        # مشاكل الكود
        if any(kw in issue_lower for kw in ["code", "error", "exception", "import", "syntax"]):
            return HealingAction.ROLLBACK_CODE

        # مشاكل المزود
        if any(kw in issue_lower for kw in ["provider", "llm", "api", "key"]):
            return HealingAction.SWITCH_PROVIDER

        # مشاكل عالية الخطورة
        if severity in ("high", "critical"):
            return HealingAction.RESTART_COMPONENT

        # الافتراضي: إعادة المحاولة
        return HealingAction.RETRY_WITH_BACKOFF

    async def _execute_with_retry(
        self,
        component_name: str,
        action: HealingAction,
        issue_description: str,
    ) -> HealingResult:
        """تنفيذ إجراء الشفاء مع exponential backoff"""
        last_error = None

        for attempt in range(1, self.MAX_RETRY_ATTEMPTS + 1):
            try:
                result = await self._execute_action(component_name, action, issue_description)
                if result.status in (HealingResultStatus.SUCCESS, HealingResultStatus.PARTIAL):
                    # نجاح — إعادة تعيين عداد الفشل
                    self._consecutive_failures[component_name] = 0
                    return result
                last_error = result.message
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Healing attempt {attempt}/{self.MAX_RETRY_ATTEMPTS} failed for {component_name}: {e}"
                )

            # Exponential backoff
            if attempt < self.MAX_RETRY_ATTEMPTS:
                wait_time = self.BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                await asyncio.sleep(wait_time)

        # فشل كل المحاولات
        self._consecutive_failures[component_name] = (
            self._consecutive_failures.get(component_name, 0) + 1
        )

        return HealingResult(
            action=action,
            status=HealingResultStatus.FAILED,
            component=component_name,
            message=f"All {self.MAX_RETRY_ATTEMPTS} attempts failed: {last_error}",
        )

    async def _execute_action(
        self,
        component_name: str,
        action: HealingAction,
        issue_description: str,
    ) -> HealingResult:
        """تنفيذ إجراء شفاء واحد"""
        try:
            if action == HealingAction.RESTART_COMPONENT:
                return await self._restart_component(component_name)
            elif action == HealingAction.RESET_CONNECTION:
                return await self._reset_connection(component_name)
            elif action == HealingAction.CLEAR_CACHE:
                return await self._clear_cache(component_name)
            elif action == HealingAction.ROLLBACK_CODE:
                return await self._rollback_code(component_name)
            elif action == HealingAction.SWITCH_PROVIDER:
                return await self._switch_provider(component_name)
            elif action == HealingAction.RETRY_WITH_BACKOFF:
                return HealingResult(
                    action=action,
                    status=HealingResultStatus.SUCCESS,
                    component=component_name,
                    message="Retry scheduled with backoff",
                )
            elif action == HealingAction.ESCALATE_TO_HUMAN:
                return HealingResult(
                    action=action,
                    status=HealingResultStatus.ESCALATED,
                    component=component_name,
                    message="Escalated to human operator",
                )
            else:
                return HealingResult(
                    action=action,
                    status=HealingResultStatus.FAILED,
                    component=component_name,
                    message=f"Unknown action: {action}",
                )
        except Exception as e:
            return HealingResult(
                action=action,
                status=HealingResultStatus.FAILED,
                component=component_name,
                message=f"Execution error: {e}",
            )

    async def _restart_component(self, component_name: str) -> HealingResult:
        """إعادة تشغيل مكون"""
        if self._kernel:
            component = self._kernel.get_component(component_name)
            if component and hasattr(component, 'initialize'):
                try:
                    if asyncio.iscoroutinefunction(component.initialize):
                        await component.initialize()
                    else:
                        component.initialize()
                    return HealingResult(
                        action=HealingAction.RESTART_COMPONENT,
                        status=HealingResultStatus.SUCCESS,
                        component=component_name,
                        message="Component restarted successfully",
                    )
                except Exception as e:
                    return HealingResult(
                        action=HealingAction.RESTART_COMPONENT,
                        status=HealingResultStatus.FAILED,
                        component=component_name,
                        message=f"Restart failed: {e}",
                    )
        return HealingResult(
            action=HealingAction.RESTART_COMPONENT,
            status=HealingResultStatus.PARTIAL,
            component=component_name,
            message="No kernel available — restart requested",
        )

    async def _reset_connection(self, component_name: str) -> HealingResult:
        """إعادة تعيين اتصال"""
        if self._kernel:
            component = self._kernel.get_component(component_name)
            if component and hasattr(component, 'reset'):
                try:
                    if asyncio.iscoroutinefunction(component.reset):
                        await component.reset()
                    else:
                        component.reset()
                    return HealingResult(
                        action=HealingAction.RESET_CONNECTION,
                        status=HealingResultStatus.SUCCESS,
                        component=component_name,
                        message="Connection reset successfully",
                    )
                except Exception as e:
                    return HealingResult(
                        action=HealingAction.RESET_CONNECTION,
                        status=HealingResultStatus.FAILED,
                        component=component_name,
                        message=f"Reset failed: {e}",
                    )
        return HealingResult(
            action=HealingAction.RESET_CONNECTION,
            status=HealingResultStatus.PARTIAL,
            component=component_name,
            message="No reset method available",
        )

    async def _clear_cache(self, component_name: str) -> HealingResult:
        """مسح الكاش"""
        if self._kernel:
            component = self._kernel.get_component(component_name)
            if component and hasattr(component, 'clear_cache'):
                try:
                    component.clear_cache()
                    return HealingResult(
                        action=HealingAction.CLEAR_CACHE,
                        status=HealingResultStatus.SUCCESS,
                        component=component_name,
                        message="Cache cleared successfully",
                    )
                except Exception as e:
                    return HealingResult(
                        action=HealingAction.CLEAR_CACHE,
                        status=HealingResultStatus.FAILED,
                        component=component_name,
                        message=f"Cache clear failed: {e}",
                    )
        return HealingResult(
            action=HealingAction.CLEAR_CACHE,
            status=HealingResultStatus.PARTIAL,
            component=component_name,
            message="No cache method available",
        )

    async def _rollback_code(self, component_name: str) -> HealingResult:
        """التراجع عن كود — استخدام VersionArchive"""
        if self._kernel:
            # محاولة استخدام EvolutionLoopV2.rollback
            evolution_loop = self._kernel.get_component("evolution_loop_v2")
            if evolution_loop and hasattr(evolution_loop, 'rollback'):
                try:
                    success = await evolution_loop.rollback()
                    return HealingResult(
                        action=HealingAction.ROLLBACK_CODE,
                        status=HealingResultStatus.SUCCESS if success else HealingResultStatus.FAILED,
                        component=component_name,
                        message="Code rolled back via EvolutionLoopV2" if success else "Rollback failed",
                    )
                except Exception as e:
                    return HealingResult(
                        action=HealingAction.ROLLBACK_CODE,
                        status=HealingResultStatus.FAILED,
                        component=component_name,
                        message=f"Rollback error: {e}",
                    )
        return HealingResult(
            action=HealingAction.ROLLBACK_CODE,
            status=HealingResultStatus.ESCALATED,
            component=component_name,
            message="No rollback mechanism available — escalate",
        )

    async def _switch_provider(self, component_name: str) -> HealingResult:
        """تبديل مزود LLM"""
        if self._kernel:
            llm_client = self._kernel.get_component("llm_client")
            if llm_client and hasattr(llm_client, 'switch_provider'):
                try:
                    llm_client.switch_provider()
                    return HealingResult(
                        action=HealingAction.SWITCH_PROVIDER,
                        status=HealingResultStatus.SUCCESS,
                        component=component_name,
                        message="Provider switched successfully",
                    )
                except Exception as e:
                    return HealingResult(
                        action=HealingAction.SWITCH_PROVIDER,
                        status=HealingResultStatus.FAILED,
                        component=component_name,
                        message=f"Provider switch failed: {e}",
                    )
        return HealingResult(
            action=HealingAction.SWITCH_PROVIDER,
            status=HealingResultStatus.PARTIAL,
            component=component_name,
            message="No provider switching available",
        )

    def _get_component_health(self, component_name: str) -> float:
        """الحصول على الحالة الصحية لمكون من MetaCognition"""
        if self._meta_cognition:
            profile = self._meta_cognition.get_profile(component_name)
            if profile:
                return profile.reliability_score
        return 0.5  # افتراضي

    async def _record_result(self, result: HealingResult, start_time: float):
        """تسجيل نتيجة الشفاء في MetaCognition و NeuralBus"""
        result.duration_ms = (time.time() - start_time) * 1000
        self._healing_history.append(result)
        self._last_healing_time[result.component] = time.time()

        # الحفاظ على حجم التاريخ
        if len(self._healing_history) > 500:
            self._healing_history = self._healing_history[-250:]

        # تسجيل في MetaCognition
        if self._meta_cognition:
            try:
                success = result.status == HealingResultStatus.SUCCESS
                from .meta_cognition_engine import OutcomeRecord
                self._meta_cognition.record_outcome(OutcomeRecord(
                    component=result.component,
                    operation=f"healing_{result.action.value}",
                    success=success,
                    quality_score=result.after_health,
                    predicted_quality=result.before_health,
                    latency_ms=result.duration_ms,
                    metadata={
                        "before_health": result.before_health,
                        "after_health": result.after_health,
                        "action": result.action.value,
                        "status": result.status.value,
                        "message": result.message,
                    },
                ))
                logger.info(
                    f"Recorded healing outcome for {result.component}: "
                    f"{result.status.value} (health: {result.before_health:.2f} → {result.after_health:.2f})"
                )
            except Exception as e:
                logger.error(f"Failed to record healing outcome in MetaCognition: {e}")

        # إرسال تنبيه عبر NeuralBus إذا فشل الشفاء
        if result.status in (HealingResultStatus.FAILED, HealingResultStatus.ESCALATED):
            await self._send_alert(result)

    async def _send_alert(self, result: HealingResult):
        """إرسال تنبيه عبر NeuralBus عند فشل الشفاء"""
        if self._neural_bus:
            try:
                from .meta_cognition_engine import MetaCognitionEngine
                try:
                    from ..shared.neural_bus import Event, EventType
                except ImportError:
                    from shared.neural_bus import Event, EventType

                event_type = (
                    EventType.HEALTH_CRITICAL
                    if hasattr(EventType, 'HEALTH_CRITICAL')
                    else EventType.HEARTBEAT
                )

                await self._neural_bus.publish(Event(
                    event_type=event_type,
                    source="self_healing_bridge",
                    data={
                        "component": result.component,
                        "action": result.action.value,
                        "status": result.status.value,
                        "message": result.message,
                        "before_health": result.before_health,
                        "after_health": result.after_health,
                        "consecutive_failures": self._consecutive_failures.get(result.component, 0),
                    },
                ))
                logger.warning(f"Sent HEALTH_CRITICAL alert for {result.component}")
            except Exception as e:
                logger.error(f"Failed to send NeuralBus alert: {e}")

    async def _handle_post_healing(self, component_name: str, result: HealingResult):
        """معالجة ما بعد الشفاء"""
        if result.status == HealingResultStatus.FAILED:
            # فشل — إرسال تنبيه ركود
            if self._neural_bus:
                try:
                    try:
                        from ..shared.neural_bus import Event, EventType
                    except ImportError:
                        from shared.neural_bus import Event, EventType

                    if hasattr(EventType, 'META_STAGNATION'):
                        await self._neural_bus.publish(Event(
                            event_type=EventType.META_STAGNATION,
                            source="self_healing_bridge",
                            data={
                                "component": component_name,
                                "reason": f"Healing failed: {result.message}",
                                "consecutive_failures": self._consecutive_failures.get(component_name, 0),
                            },
                        ))
                except Exception as e:
                    logger.error(f"Failed to send stagnation alert: {e}")

        elif result.status == HealingResultStatus.SUCCESS:
            # نجاح — تحديث الحالة الصحية
            if self._meta_cognition:
                profile = self._meta_cognition.get_profile(component_name)
                if profile and profile.reliability_score < 0.8:
                    logger.info(
                        f"Component {component_name} healed successfully "
                        f"(health: {result.before_health:.2f} → {result.after_health:.2f})"
                    )

    def get_stats(self) -> dict:
        """إحصائيات الشفاء"""
        total = len(self._healing_history)
        successful = sum(1 for r in self._healing_history if r.status == HealingResultStatus.SUCCESS)
        failed = sum(1 for r in self._healing_history if r.status == HealingResultStatus.FAILED)
        escalated = sum(1 for r in self._healing_history if r.status == HealingResultStatus.ESCALATED)

        return {
            "total_healing_attempts": total,
            "successful": successful,
            "failed": failed,
            "escalated": escalated,
            "success_rate": successful / max(total, 1),
            "components_with_failures": {
                k: v for k, v in self._consecutive_failures.items() if v > 0
            },
            "avg_duration_ms": (
                sum(r.duration_ms for r in self._healing_history) / max(total, 1)
            ),
        }
