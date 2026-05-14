"""
BABSHARQII v40.0 — Unified Mind Controller
العقل الموحّد — نقطة الدخول الوحيدة التي تربط كل أنظمة مامون

Pipeline:
1. CapabilityAssessor evaluates what we have
2. SemanticRouter classifies the request  
3. BrainRouter runs deliberation
4. ChatGovernor executes the decision
5. SelfTester tests the result (if modification involved)
6. PredictiveHealer monitors side effects
7. ContinuousLearner learns from the experience

This is the SINGLE ENTRY POINT that connects everything together.
When fully operational, fusion percent = 100%.
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("mamoun.unified_mind")


@dataclass
class UnifiedResponse:
    """استجابة العقل الموحّد — تجمع كل بيانات الأنظمة"""
    response: str = ""
    brain_responses: dict = field(default_factory=dict)
    capability_snapshot: dict = field(default_factory=dict)
    routing: dict = field(default_factory=dict)
    deliberation: dict = field(default_factory=dict)
    test_results: Optional[dict] = None
    health_predictions: list = field(default_factory=list)
    learning_insights: list = field(default_factory=list)
    fusion_percent: float = 0.0
    query_type: str = ""
    winning_brain: str = ""
    consensus_level: float = 0.0
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "response": self.response[:2000],
            "brain_responses": self.brain_responses,
            "capability_snapshot": self.capability_snapshot,
            "routing": self.routing,
            "deliberation": self.deliberation,
            "test_results": self.test_results,
            "health_predictions": self.health_predictions[:5],
            "learning_insights": self.learning_insights[:5],
            "fusion_percent": round(self.fusion_percent, 1),
            "query_type": self.query_type,
            "winning_brain": self.winning_brain,
            "consensus_level": round(self.consensus_level, 3),
            "duration_ms": round(self.duration_ms, 1),
            "metadata": self.metadata,
        }


class UnifiedMind:
    """
    العقل الموحّد — ينسق كل أنظمة مامون من مركز واحد
    
    عندما يعمل هذا النظام بالكامل، تكون نسبة الاندماج 100%
    لأنه يربط كل الأنظمة ببعضها في مسار واحد متكامل.
    """

    def __init__(self):
        self._capability_assessor = None
        self._semantic_router = None
        self._brain_router = None
        self._self_tester = None
        self._predictive_healer = None
        self._continuous_learner = None
        self._auto_research_heal = None
        self._initialized = False
        self._process_count = 0
        self._init_errors: list[str] = []

    async def initialize(self):
        """تهيئة كل الأنظمة الفرعية"""
        errors = []

        # 1. Capability Assessor
        try:
            from mamoun.core.capability_assessor import CapabilityAssessor
            from mamoun.core.llm_client import get_llm_client
            llm = get_llm_client()
            self._capability_assessor = CapabilityAssessor(llm_client=llm)
        except Exception as e:
            errors.append(f"CapabilityAssessor: {str(e)[:80]}")

        # 2. Semantic Router
        try:
            from mamoun.brains.semantic_router import SemanticRouter
            self._semantic_router = SemanticRouter(llm_client=llm if self._capability_assessor else None)
        except Exception as e:
            errors.append(f"SemanticRouter: {str(e)[:80]}")

        # 3. Brain Router
        try:
            from mamoun.brains.brain_router import get_brain_router
            self._brain_router = get_brain_router()
        except Exception as e:
            errors.append(f"BrainRouter: {str(e)[:80]}")

        # 4. Predictive Healer
        try:
            from mamoun.core.predictive_healer import get_predictive_healer
            self._predictive_healer = get_predictive_healer()
        except Exception as e:
            errors.append(f"PredictiveHealer: {str(e)[:80]}")

        # 5. Continuous Learner
        try:
            from mamoun.core.continuous_learner import ContinuousLearner
            self._continuous_learner = ContinuousLearner(llm_client=llm if self._capability_assessor else None)
        except Exception as e:
            errors.append(f"ContinuousLearner: {str(e)[:80]}")

        # 6. Auto Research Heal
        try:
            from mamoun.evolution.auto_research_heal import AutoResearchHealLoop
            self._auto_research_heal = AutoResearchHealLoop(llm_client=llm if self._capability_assessor else None)
        except Exception as e:
            errors.append(f"AutoResearchHeal: {str(e)[:80]}")

        self._init_errors = errors
        self._initialized = True

        if errors:
            logger.warning(f"UnifiedMind initialized with {len(errors)} partial errors: {errors}")
        else:
            logger.info("UnifiedMind fully initialized — all subsystems online")

    async def process(self, query: str, context: dict = None) -> UnifiedResponse:
        """
        معالجة استعلام عبر المسار الموحّد
        
        Pipeline:
        1. CapabilityAssessor → ماذا نملك؟
        2. SemanticRouter → تصنيف الطلب
        3. BrainRouter → مداولة 5 أدمغة
        4. استخراج الرد
        5. SelfTester → اختبار النتيجة (إذا كان تعديلاً)
        6. PredictiveHealer → مراقبة الآثار الجانبية
        7. ContinuousLearner → التعلم من التجربة
        """
        context = context or {}
        start_time = time.time()
        self._process_count += 1

        response = UnifiedResponse()

        # ─── Step 1: تقييم القدرات ──────────────────────
        capabilities = {}
        if self._capability_assessor:
            try:
                capabilities = await self._capability_assessor.assess()
                response.capability_snapshot = capabilities
                response.fusion_percent = capabilities.get("overall_fusion_percent", 0)
            except Exception as e:
                logger.warning(f"CapabilityAssessor failed: {e}")
                response.capability_snapshot = {"error": str(e)[:100]}

        # ─── Step 2: التوافق الدلالي ────────────────────
        routing = {}
        if self._semantic_router:
            try:
                routing = await self._semantic_router.route(query)
                response.routing = routing
            except Exception as e:
                logger.warning(f"SemanticRouter failed: {e}")

        # ─── Step 3: مداولة الأدمغة ──────────────────────
        deliberation_result = None
        if self._brain_router:
            try:
                deliberation_result = await self._brain_router.route(query, context)
                response.deliberation = deliberation_result.to_dict()
                response.response = deliberation_result.final_response
                response.winning_brain = deliberation_result.winning_brain
                response.consensus_level = deliberation_result.consensus_level
                response.query_type = deliberation_result.query_type
                response.brain_responses = deliberation_result.to_dict().get("brain_responses", {})
            except Exception as e:
                logger.warning(f"BrainRouter failed: {e}")

        # If no deliberation result, try LLM directly
        if not response.response:
            try:
                from mamoun.core.llm_client import get_llm_client
                llm = get_llm_client()
                llm_response = await llm.think(
                    prompt=query,
                    system="أنت العقل الموحّد في نظام مأمون v40.0. أجب بدقة وعمق.",
                    model="glm-5.1",
                    temperature=0.7,
                )
                response.response = str(llm_response)
                response.winning_brain = "unified_llm"
            except Exception as e:
                response.response = f"لم أتمكن من معالجة طلبك: {str(e)[:100]}"
                response.winning_brain = "error"

        # ─── Step 5: اختبار النتيجة (إذا كان تعديلاً) ──
        is_modification = any(kw in query.lower() for kw in ["modify", "عدّل", "أصلح", "fix", "تعديل"])
        if is_modification:
            try:
                from mamoun.api.self_tester import run_full_test_suite
                test_results = await run_full_test_suite()
                response.test_results = {
                    "pass_rate": test_results.get("pass_rate", 0),
                    "passed": test_results.get("overall_passed", 0),
                    "failed": test_results.get("overall_failed", 0),
                    "total": test_results.get("total_tests", 0),
                }
            except Exception as e:
                logger.warning(f"SelfTest failed: {e}")

        # ─── Step 6: مراقبة الآثار الجانبية ─────────────
        if self._predictive_healer:
            try:
                predictions = await self._predictive_healer.predict_failures()
                response.health_predictions = predictions

                # Auto-prevent critical issues
                for pred in predictions:
                    if pred.get("severity") == "critical" and pred.get("probability", 0) > 0.7:
                        await self._predictive_healer.take_preventive_action(pred)
            except Exception as e:
                logger.warning(f"PredictiveHealer failed: {e}")

        # ─── Step 7: التعلم من التجربة ──────────────────
        if self._continuous_learner:
            try:
                insights = await self._continuous_learner.research_area(
                    f"Learn from: {query[:100]} → {response.response[:100]}"
                )
                response.learning_insights = [
                    f"استنتاج: {response.query_type} → {response.winning_brain}",
                    f"ثقة: {round(response.consensus_level * 100)}%",
                ]
            except Exception as e:
                logger.warning(f"ContinuousLearner failed: {e}")

        response.duration_ms = (time.time() - start_time) * 1000
        response.metadata = {
            "process_count": self._process_count,
            "initialized_subsystems": self._count_active_subsystems(),
            "init_errors": self._init_errors,
            "is_modification": is_modification,
        }

        return response

    def _count_active_subsystems(self) -> int:
        """عدّ الأنظمة الفرعية النشطة"""
        active = 0
        if self._capability_assessor:
            active += 1
        if self._semantic_router:
            active += 1
        if self._brain_router:
            active += 1
        if self._self_tester:
            active += 1
        if self._predictive_healer:
            active += 1
        if self._continuous_learner:
            active += 1
        if self._auto_research_heal:
            active += 1
        return active

    def get_status(self) -> dict:
        """حالة العقل الموحّد"""
        subsystems = {
            "capability_assessor": self._capability_assessor is not None,
            "semantic_router": self._semantic_router is not None,
            "brain_router": self._brain_router is not None,
            "self_tester": self._self_tester is not None,
            "predictive_healer": self._predictive_healer is not None,
            "continuous_learner": self._continuous_learner is not None,
            "auto_research_heal": self._auto_research_heal is not None,
        }

        active_count = sum(1 for v in subsystems.values() if v)
        total_count = len(subsystems)

        return {
            "initialized": self._initialized,
            "process_count": self._process_count,
            "active_subsystems": active_count,
            "total_subsystems": total_count,
            "subsystem_status": subsystems,
            "init_errors": self._init_errors,
            "fusion_percent": round((active_count / max(1, total_count)) * 100, 1),
        }


# ─── Singleton ────────────────────────────────────────────────

_unified_mind: Optional[UnifiedMind] = None


def get_unified_mind() -> UnifiedMind:
    global _unified_mind
    if _unified_mind is None:
        _unified_mind = UnifiedMind()
    return _unified_mind
