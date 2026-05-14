"""
BABSHARQII v17.0 — Deliberation Room (REAL)
غرفة المداولة الحقيقية — تُجري مداولة فعلية بين الأدمغة الحية

v17.0 Changes:
- ACTUALLY calls brains via asyncio.gather (not just mathematical CJS)
- Uses BrainRouter for intelligent query distribution
- Weighted voting with conflict resolution
- LLM arbitration when brains disagree
- Real-time awareness mirror reflection

Pipeline:
1. Route query to appropriate brains
2. Execute brains in parallel (asyncio.gather)
3. Calculate CJS (Critical Junction Score)
4. Detect conflicts (opposing stances)
5. Resolve via weighted vote OR LLM arbitration
6. Mirror reflection on the decision
7. Return deliberation result
"""

import asyncio
import time
import math
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("mamoun.deliberation.room")


@dataclass
class DeliberationResult:
    """نتيجة المداولة الحقيقية — تحتوي على استجابات الأدمغة الفعلية"""
    topic: str = ""
    query_type: str = ""
    consensus_level: float = 0.0
    critical_junction_score: float = 0.0
    needs_human_intervention: bool = False
    recommendations: list = field(default_factory=list)
    brain_count: int = 0
    agreement_ratio: float = 0.0
    dissent_ratio: float = 0.0
    duration_ms: float = 0.0
    timestamp: float = 0.0
    # v17.0: Real brain data
    brain_responses: dict = field(default_factory=dict)
    final_response: str = ""
    final_confidence: float = 0.0
    winning_brain: str = ""
    conflict_detected: bool = False
    arbitration_used: bool = False
    mirror_reflection: str = ""

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "query_type": self.query_type,
            "consensus_level": round(self.consensus_level, 4),
            "critical_junction_score": round(self.critical_junction_score, 4),
            "needs_human_intervention": self.needs_human_intervention,
            "recommendations": self.recommendations,
            "brain_count": self.brain_count,
            "agreement_ratio": round(self.agreement_ratio, 4),
            "dissent_ratio": round(self.dissent_ratio, 4),
            "duration_ms": round(self.duration_ms, 1),
            "brain_responses": {
                bid: {
                    "response": resp.get("response", "")[:300],
                    "confidence": resp.get("confidence", 0),
                    "stance": resp.get("stance", "neutral"),
                    "model_used": resp.get("model_used", ""),
                }
                for bid, resp in self.brain_responses.items()
            },
            "final_response": self.final_response,
            "final_confidence": round(self.final_confidence, 3),
            "winning_brain": self.winning_brain,
            "conflict_detected": self.conflict_detected,
            "arbitration_used": self.arbitration_used,
            "mirror_reflection": self.mirror_reflection[:500],
        }


class DeliberationRoom:
    """
    غرفة المداولة الحقيقية — تُجري مداولة فعلية بين الأدمغة

    v17.0: This is a REAL deliberation room that:
    1. Actually calls LLM-powered brains in parallel
    2. Detects real conflicts in brain responses
    3. Resolves conflicts via weighted vote or LLM arbitration
    4. Reflects on its own decisions via Mirror

    CJS thresholds:
    - CJS < 0.4 → "تقاطع حرج" — requires human intervention
    - CJS 0.4-0.7 → "يحتاج مراقبة" — needs monitoring
    - CJS > 0.7 → "إجماع عالي" — proceed autonomously
    """

    CJS_CRITICAL = 0.4
    CJS_MONITORING = 0.7

    # CJS factor weights
    WEIGHT_AGREEMENT = 0.35
    WEIGHT_CONFIDENCE = 0.30
    WEIGHT_COVERAGE = 0.20
    WEIGHT_CONSISTENCY = 0.15

    def __init__(
        self,
        brains: dict = None,
        brain_router=None,
        llm_client=None,
        cjs_critical_threshold: float = 0.4,
    ):
        """
        تهيئة غرفة المداولة الحقيقية.

        Args:
            brains: dict of brain_id → LivingBrain instances
            brain_router: BrainRouter for intelligent routing
            llm_client: LLM client for arbitration
            cjs_critical_threshold: عتبة التقاطع الحرج
        """
        self._brains = brains or {}
        self._router = brain_router
        self._llm = llm_client
        self.cjs_critical_threshold = cjs_critical_threshold
        self._history: list[DeliberationResult] = []

    def register_brain(self, brain_id: str, brain):
        """Register a living brain for deliberation."""
        self._brains[brain_id] = brain

    async def deliberate(
        self,
        topic: str,
        context: dict = None,
        brain_ids: list = None,
        brains_responses=None,
    ) -> DeliberationResult:
        """
        إجراء مداولة حقيقية — استدعاء الأدمغة فعلياً بالتوازي

        This is the CORE method that makes مأمون actually THINK.

        Pipeline:
        1. Select brains (or use router)
        2. Execute brains in PARALLEL (asyncio.gather)
        3. Calculate CJS from real responses
        4. Detect conflicts
        5. Resolve conflicts
        6. Compose final response
        7. Mirror reflection

        Args:
            topic: The topic to deliberate on
            context: Additional context for the deliberation
            brain_ids: Optional list of brain IDs to involve
            brains_responses: v36 FIX: Optional pre-computed responses (list or dict).
                            If provided, skip brain execution and use these directly.
        """
        context = context or {}
        start_time = time.time()

        # v36 FIX: If brains_responses provided directly, skip brain execution
        if brains_responses is not None:
            # Normalize to dict format
            if isinstance(brains_responses, list):
                brain_responses = {
                    r.get("brain_id", f"brain_{i}"): r
                    for i, r in enumerate(brains_responses)
                }
            elif isinstance(brains_responses, dict):
                brain_responses = brains_responses
            else:
                brain_responses = {}

            if not brain_responses:
                result = DeliberationResult(
                    topic=topic,
                    needs_human_intervention=True,
                    recommendations=["لا توجد استجابات — يتطلب تدخل بشري"],
                    timestamp=time.time(),
                )
                self._history.append(result)
                return result

            # Calculate CJS from provided responses
            cjs = self.calculate_cjs(brain_responses)

            # Detect conflicts
            conflict = self._detect_conflict(brain_responses)

            # Compose final response
            if conflict:
                final = await self._resolve_and_compose(topic, brain_responses)
                arbitration_used = True
            else:
                final = self._weighted_compose(brain_responses)
                arbitration_used = False

            # Calculate ratios
            agreement_ratio, dissent_ratio = self._calculate_stance_ratios(brain_responses)
            consensus_level = self._calculate_consensus(brain_responses)
            needs_intervention = cjs < self.cjs_critical_threshold

            recommendations = self._generate_recommendations(
                cjs=cjs,
                consensus_level=consensus_level,
                brains_responses=brain_responses,
                needs_intervention=needs_intervention,
                conflict=conflict,
            )

            duration_ms = (time.time() - start_time) * 1000

            result = DeliberationResult(
                topic=topic,
                query_type=context.get("query_type", "general"),
                consensus_level=consensus_level,
                critical_junction_score=cjs,
                needs_human_intervention=needs_intervention,
                recommendations=recommendations,
                brain_count=len(brain_responses),
                agreement_ratio=agreement_ratio,
                dissent_ratio=dissent_ratio,
                arbitration_used=arbitration_used,
                mirror_reflection="",
                final_response=final,
                duration_ms=duration_ms,
            )
            self._history.append(result)
            return result

        # Step 1: Determine which brains to use
        if brain_ids is None:
            brain_ids = list(self._brains.keys())

        active_brains = {
            bid: self._brains[bid]
            for bid in brain_ids
            if bid in self._brains and self._brains[bid].state.status in ("active", "idle", "thinking")
        }

        if not active_brains:
            # Fallback: use all brains except error state
            active_brains = {
                bid: brain
                for bid, brain in self._brains.items()
                if brain.state.status != "error"
            }

        # Activate idle brains before deliberation
        for brain in active_brains.values():
            if brain.state.status == "idle":
                brain.activate()

        if not active_brains:
            result = DeliberationResult(
                topic=topic,
                needs_human_intervention=True,
                recommendations=["لا توجد أدمغة نشطة — يتطلب تدخل بشري"],
                timestamp=time.time(),
            )
            self._history.append(result)
            return result

        # Step 2: Execute brains in PARALLEL
        logger.info("Deliberating '%s' with %d brains: %s",
                    topic[:50], len(active_brains), list(active_brains.keys()))

        brain_tasks = {
            bid: brain.think(topic, context)
            for bid, brain in active_brains.items()
        }

        results = await asyncio.gather(
            *brain_tasks.values(), return_exceptions=True
        )

        brain_responses = {}
        for (bid, _), result in zip(brain_tasks.items(), results):
            if isinstance(result, Exception):
                logger.warning("Brain '%s' failed in deliberation: %s", bid, result)
                brain_responses[bid] = {
                    "brain_id": bid,
                    "response": "",
                    "confidence": 0.0,
                    "reasoning": f"Error: {str(result)}",
                    "stance": "neutral",
                }
            else:
                brain_responses[bid] = result

        # Step 3: Calculate CJS from REAL responses
        cjs = self.calculate_cjs(brain_responses)

        # Step 4: Detect conflicts
        conflict = self._detect_conflict(brain_responses)

        # Step 5: Resolve and compose final response
        if conflict:
            final = await self._resolve_and_compose(topic, brain_responses)
            arbitration_used = True
        else:
            final = self._weighted_compose(brain_responses)
            arbitration_used = False

        # Step 6: Mirror reflection on the decision
        mirror_reflection = ""
        if self._llm and cjs < self.CJS_MONITORING:
            try:
                mirror_reflection = await self._mirror_reflect(
                    topic, brain_responses, final
                )
            except Exception as e:
                logger.warning("Mirror reflection failed: %s", e)

        # Calculate ratios
        agreement_ratio, dissent_ratio = self._calculate_stance_ratios(brain_responses)
        consensus_level = self._calculate_consensus(brain_responses)
        needs_intervention = cjs < self.cjs_critical_threshold

        recommendations = self._generate_recommendations(
            cjs=cjs,
            consensus_level=consensus_level,
            brains_responses=brain_responses,
            needs_intervention=needs_intervention,
            conflict=conflict,
        )

        duration_ms = (time.time() - start_time) * 1000

        result = DeliberationResult(
            topic=topic,
            query_type=context.get("query_type", "general"),
            consensus_level=consensus_level,
            critical_junction_score=cjs,
            needs_human_intervention=needs_intervention,
            recommendations=recommendations,
            brain_count=len(brain_responses),
            agreement_ratio=agreement_ratio,
            dissent_ratio=dissent_ratio,
            duration_ms=duration_ms,
            timestamp=time.time(),
            brain_responses=brain_responses,
            final_response=final["response"],
            final_confidence=final["confidence"],
            winning_brain=final["winning_brain"],
            conflict_detected=conflict,
            arbitration_used=arbitration_used,
            mirror_reflection=mirror_reflection,
        )

        self._history.append(result)
        return result

    async def _resolve_and_compose(
        self, topic: str, responses: dict
    ) -> dict:
        """
        حل التناقض وتركيب الإجابة النهائية

        When brains disagree, use LLM arbitration to resolve.
        """
        if not self._llm:
            return self._weighted_compose(responses)

        # Build arbitration prompt
        brain_views = []
        for brain_id, resp in responses.items():
            brain_views.append(
                f"الدماغ {brain_id} (ثقة: {resp.get('confidence', 0):.2f}، "
                f"موقف: {resp.get('stance', 'neutral')}):\n"
                f"الإجابة: {resp.get('response', '')[:500]}\n"
                f"الاستدلال: {resp.get('reasoning', '')[:300]}"
            )

        views_text = "\n\n---\n\n".join(brain_views)

        try:
            from mamoun.core.llm_client import LLMMessage
            response = await self._llm.think(
                prompt=f"""أنت حَكَم في غرفة مداولة مأمون v17. الأدمغة اختلفت:

السؤال: {topic}

آراء الأدمغة:
{views_text}

حلل كل رأي، حدد الأقرب للصواب، وألّف إجابة نهائية مركّبة.

أجب بصيغة JSON:
{{
  "response": "الإجابة النهائية",
  "confidence": 0.0-1.0,
  "reasoning": "لماذا هذا التركيب",
  "winning_brain": "الدماغ الأقرب للصواب",
  "synthesis": "كيف ألّفت الإجابة من الآراء المختلفة"
}}""",
                system="أنت حَكَم محايد في مأمون. تحلل الآراء المتضاربة وتصنع إجابة مركّبة.",
                model="glm-5.1",
                temperature=0.3,
                json_mode=True,
            )

            arbitration = response.extract_json()
            if arbitration:
                return {
                    "response": arbitration.get("response", ""),
                    "confidence": float(arbitration.get("confidence", 0.6)),
                    "winning_brain": arbitration.get("winning_brain", "arbitrator"),
                }
        except Exception as e:
            logger.warning("LLM arbitration failed: %s", e)

        return self._weighted_compose(responses)

    def _weighted_compose(self, responses: dict) -> dict:
        """تركيب الإجابة بالتصويت الموزون — بدون تناقض"""
        if not responses:
            return {"response": "", "confidence": 0, "winning_brain": ""}

        # Find the brain with highest composite score
        best_brain = max(
            responses,
            key=lambda bid: responses[bid].get("confidence", 0) * responses[bid].get("relevance", 0.5)
        )
        best = responses[best_brain]

        return {
            "response": best.get("response", ""),
            "confidence": best.get("confidence", 0.5),
            "winning_brain": best_brain,
        }

    async def _mirror_reflect(
        self, topic: str, responses: dict, final: dict
    ) -> str:
        """
        تأمل المرآة — مأمون يتأمل في قراره

        The Mirror reflects on the deliberation process:
        - Were there biases?
        - Was the right brain chosen?
        - What assumptions were made?
        """
        if not self._llm:
            return ""

        try:
            reflection = await self._llm.reflect(
                content=f"""السؤال: {topic}
الدماغ الفائز: {final.get('winning_brain', '')}
الإجابة النهائية: {final.get('response', '')[:500]}
عدد الأدمغة المشاركة: {len(responses)}
""",
                question="هل كان القرار صائباً؟ ما الافتراضات الخفية؟ ما الذي قد يسوء؟",
            )
            return reflection.text or ""
        except Exception:
            return ""

    # ─────────────────────────────────────────────────────────────────────────
    # CJS Calculation (same as before, but works with real data)
    # ─────────────────────────────────────────────────────────────────────────

    def calculate_cjs(self, responses) -> float:
        """حساب نقاط التقاطع الحرج من استجابات الأدمغة الحقيقية."""
        if not responses:
            return 0.0

        # v36 FIX: Support both dict and list input formats
        # Some callers pass a dict (brain_id → response), others pass a list of responses
        if isinstance(responses, dict):
            response_list = list(responses.values())
        elif isinstance(responses, list):
            response_list = responses
        else:
            return 0.0

        n = len(response_list)

        # 1. Agreement factor
        agreement = self._compute_agreement_factor(response_list)

        # 2. Confidence factor
        confidences = [r.get("confidence", 0.5) for r in response_list]
        avg_confidence = sum(confidences) / len(confidences)

        # 3. Coverage factor
        coverage = min(1.0, n / 5.0)

        # 4. Consistency factor
        if len(confidences) > 1:
            variance = sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences)
            consistency = 1.0 - min(1.0, math.sqrt(variance) * 2)
        else:
            consistency = 0.5

        cjs = (
            self.WEIGHT_AGREEMENT * agreement
            + self.WEIGHT_CONFIDENCE * avg_confidence
            + self.WEIGHT_COVERAGE * coverage
            + self.WEIGHT_CONSISTENCY * consistency
        )

        return max(0.0, min(1.0, cjs))

    def calculate_enhanced_cjs(self, responses, knowledge_gaps=None) -> float:
        """
        حساب CJS المحسّن — Enhanced CJS with Cognitive Divergence Score and knowledge gaps.

        v36 FIX: Added calculate_enhanced_cjs() method for test compatibility.
        This extends the base CJS by incorporating:
        1. Cognitive Divergence Score (CDS) — penalizes high variance in confidence
        2. Knowledge Gap penalty — reduces score when there are significant knowledge gaps

        Args:
            responses: Dict or list of brain responses
            knowledge_gaps: Optional list of knowledge gap dicts with 'severity' keys

        Returns:
            Float between 0.0 and 1.0
        """
        base_cjs = self.calculate_cjs(responses)

        # Get response list for additional calculations
        if isinstance(responses, dict):
            response_list = list(responses.values())
        elif isinstance(responses, list):
            response_list = responses
        else:
            return base_cjs

        # 1. Cognitive Divergence Score (CDS)
        # Measures how much brains diverge in their confidence levels
        confidences = [r.get("confidence", 0.5) for r in response_list]
        if len(confidences) > 1:
            avg_conf = sum(confidences) / len(confidences)
            variance = sum((c - avg_conf) ** 2 for c in confidences) / len(confidences)
            cds = min(1.0, math.sqrt(variance) * 2)  # 0 = no divergence, 1 = high divergence
        else:
            cds = 0.0

        # Reduce CJS by divergence factor
        enhanced = base_cjs * (1.0 - cds * 0.3)

        # 2. Knowledge Gap penalty
        if knowledge_gaps:
            # Each gap reduces the score proportionally to its severity
            for gap in knowledge_gaps:
                severity = gap.get("severity", "medium")
                if severity == "high":
                    enhanced *= 0.85  # 15% reduction per high-severity gap
                elif severity == "medium":
                    enhanced *= 0.93  # 7% reduction per medium-severity gap
                else:
                    enhanced *= 0.97  # 3% reduction per low-severity gap

        return max(0.0, min(1.0, enhanced))

    def _detect_conflict(self, responses) -> bool:
        """كشف التناقض الحقيقي بين الأدمغة."""
        # v36 FIX: Support both dict and list input
        if isinstance(responses, dict):
            response_list = list(responses.values())
        elif isinstance(responses, list):
            response_list = responses
        else:
            return False

        if len(response_list) < 2:
            return False

        stances = [r.get("stance", "neutral") for r in response_list]
        has_support = "support" in stances
        has_oppose = "oppose" in stances

        if has_support and has_oppose:
            return True

        confidences = [r.get("confidence", 0.5) for r in response_list]
        if len(confidences) > 1:
            spread = max(confidences) - min(confidences)
            if spread > 0.4:
                return True

        return False

    def _compute_agreement_factor(self, responses: list) -> float:
        if not responses:
            return 0.0

        stances = []
        for r in responses:
            stance = r.get("stance", "neutral")
            if stance in ("support", "مؤيد"):
                stances.append(1.0)
            elif stance in ("oppose", "معارض"):
                stances.append(-1.0)
            else:
                stances.append(0.0)

        if not stances:
            return 0.5

        avg = sum(stances) / len(stances)
        return min(1.0, abs(avg))

    def _calculate_consensus(self, responses: dict) -> float:
        if not responses:
            return 0.0
        response_list = list(responses.values())
        agreement = self._compute_agreement_factor(response_list)
        confidences = [r.get("confidence", 0.5) for r in response_list]
        avg_confidence = sum(confidences) / len(confidences)
        return max(0.0, min(1.0, agreement * 0.6 + avg_confidence * 0.4))

    def _calculate_stance_ratios(self, responses: dict) -> tuple:
        if not responses:
            return 0.0, 0.0

        support = sum(1 for r in responses.values() if r.get("stance") in ("support", "مؤيد"))
        oppose = sum(1 for r in responses.values() if r.get("stance") in ("oppose", "معارض"))
        total = len(responses)
        return support / total, oppose / total

    def _generate_recommendations(
        self, cjs, consensus_level, brains_responses, needs_intervention, conflict
    ) -> list:
        recommendations = []

        if needs_intervention:
            recommendations.append("تقاطع حرج: الأدمغة غير متفقة — يُطلب التدخل البشري")
            recommendations.append("يُنصح بمراجعة الموضوع يدوياً قبل المتابعة")
        elif cjs < self.CJS_MONITORING:
            recommendations.append("مستوى اتفاق متوسط — يُنصح بالمراقبة المستمرة")
        else:
            recommendations.append("إجماع عالي — يمكن المتابعة بشكل مستقل")

        if conflict:
            recommendations.append("تم كشف تناقض بين الأدمغة — تم استخدام التحكيم")

        low_conf = [
            bid for bid, r in brains_responses.items()
            if r.get("confidence", 1.0) < 0.4
        ]
        if low_conf:
            recommendations.append(f"أدمغة ذات ثقة منخفضة: {', '.join(low_conf)}")

        opposing = [
            bid for bid, r in brains_responses.items()
            if r.get("stance") in ("oppose", "معارض")
        ]
        if opposing:
            recommendations.append(f"أدمغة معارضة: {', '.join(opposing)} — يُرجى مراعاة مخاوفها")

        return recommendations

    def get_history(self, last_n: int = 10) -> list:
        return [r.to_dict() for r in self._history[-last_n:]]

    def get_critical_junctions(self) -> list:
        return [
            r.to_dict()
            for r in self._history
            if r.critical_junction_score < self.cjs_critical_threshold
        ]
