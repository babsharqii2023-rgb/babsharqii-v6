"""
BABSHARQII v17.0 — Brain Router
موجّه الأدمغة — يوزّع الأسئلة على الأدمغة المناسبة بذكاء

The BrainRouter determines WHICH brains to activate for a given query,
and HOW to combine their responses. It replaces the old "all brains always"
approach with intelligent, context-aware routing.

Key Features:
- Query type detection (Arabic keyword analysis)
- Selective brain activation (not all brains for all queries)
- Weighted response combination with conflict resolution
- Adaptive weights based on historical performance
- Parallel brain execution with asyncio.gather
- v40.0 Fusion: API Key diversification with fallback warnings + brain status reporting

Based on research:
- Mixture of Experts (MoE): Route to the right expert, not everyone
- Debate-based LLM reasoning: Multiple models vote, best answer wins
"""

import asyncio
import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from mamoun.core.llm_client import LLMClient, get_llm_client

logger = logging.getLogger("mamoun.brains.brain_router")


# ─────────────────────────────────────────────────────────────────────────────
# Brain Model Registry — Original models and their fallbacks
# v40.0 Fusion: API Key Diversification
# ─────────────────────────────────────────────────────────────────────────────

BRAIN_MODEL_REGISTRY = {
    "neural": {
        "original_model": "glm-5.1",
        "fallback_model": "deepseek-chat",
        "api_key_env": "GLM_API_KEY",
        "name_ar": "العصبي",
    },
    "causal": {
        "original_model": "deepseek-reasoner",
        "fallback_model": "glm-5.1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "name_ar": "السببي",
    },
    "symbolic": {
        "original_model": "glm-4-plus",
        "fallback_model": "deepseek-chat",
        "api_key_env": "GLM_API_KEY",
        "name_ar": "الرمزي",
    },
    "bayesian": {
        "original_model": "gemini-2.0-flash",
        "fallback_model": "glm-5.1",
        "api_key_env": "GEMINI_API_KEY",
        "name_ar": "البيزي",
    },
    "world_model": {
        "original_model": "deepseek-chat",
        "fallback_model": "glm-5.1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "name_ar": "العالمي",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Query Type Detection
# ─────────────────────────────────────────────────────────────────────────────

class QueryClassifier:
    """
    مصنّف الاستعلامات — يحدد نوع السؤال لتوجيهه للدماغ المناسب

    Uses Arabic keyword analysis and pattern matching to classify queries.
    Each query type maps to a specific set of brains and weights.
    """

    # Query types and their brain activation patterns
    # v36.1 FIX: Improved keyword coverage for Arabic verb forms and reduced overlap
    QUERY_PATTERNS = {
        "technical_code": {
            "keywords": ["كود", "برمج", "دالة", "class", "def", "function", "bug", "إصلاح كود", "python", "javascript", "api", "تطوير", "كتابة كود", "برنامج", "سكريبت", "script", "debug", "compile", "ترجمة برمج"],
            "brains": ["neural", "symbolic", "causal"],
            "weights": {"neural": 0.40, "symbolic": 0.30, "causal": 0.30},
        },
        "causal_why": {
            "keywords": ["لماذا", "سبب", "نتيجة", "بسبب", "أدى", "تسبب", "عاقبة", "ما السبب", "كيف حدث", "لما حدث", "خطأ", "علة", "root cause", "why"],
            "brains": ["causal", "neural", "world_model"],
            "weights": {"causal": 0.40, "neural": 0.30, "world_model": 0.30},
        },
        "logical_math": {
            "keywords": ["حساب", "احسب", "حسب", "رياض", "معادل", "إثبات", "منطق", "صحيح أو خطأ", "تناقض", "استنتاج", "قياس", "نسبة", "ضرب", "قسمة", "جمع", "طرح", "مسألة", "math", "equation", "formula", "calculate"],
            "brains": ["symbolic", "bayesian", "causal"],
            "weights": {"symbolic": 0.40, "bayesian": 0.35, "causal": 0.25},
        },
        "probability_uncertainty": {
            "keywords": ["احتمال", "يقين", "ممكن", "غير مؤكد", "مخاطرة", "توقع", "كم نسبة", "ما نسبة"],
            "brains": ["bayesian", "world_model", "causal"],
            "weights": {"bayesian": 0.40, "world_model": 0.30, "causal": 0.30},
        },
        "future_scenario": {
            "keywords": ["ماذا لو", "سيناريو", "مستقبل", "محاكاة", "عواقب", "تأثير", "نتائج محتملة"],
            "brains": ["world_model", "causal", "bayesian"],
            "weights": {"world_model": 0.40, "causal": 0.35, "bayesian": 0.25},
        },
        "creative_general": {
            "keywords": ["اقترح", "فكّر", "أبدع", "اكتب", "صمّم", "ابتكر", "خطة", "استراتيجية"],
            "brains": ["neural", "world_model", "causal"],
            "weights": {"neural": 0.40, "world_model": 0.30, "causal": 0.30},
        },
        "self_reflection": {
            "keywords": ["من أنت", "ماذا تعرف عن نفسك", "كيف تفكر", "برمجتك", "فحص ذاتي", "تأمل", "وعي"],
            "brains": ["neural", "symbolic", "causal"],
            "weights": {"neural": 0.35, "symbolic": 0.35, "causal": 0.30},
        },
        "analysis_research": {
            "keywords": ["حلل", "بحث", "دراسة", "استكشف", "قارن", "قيّم", "راجع", "تحليل"],
            "brains": ["causal", "neural", "bayesian", "symbolic"],
            "weights": {"causal": 0.28, "neural": 0.28, "bayesian": 0.22, "symbolic": 0.22},
        },
    }

    # v18.1: Balanced default — كل دماغ له وزن يعكس دوره الفعلي
    DEFAULT_CONFIG = {
        "type": "general",
        "brains": ["neural", "causal", "symbolic", "bayesian", "world_model"],
        "weights": {"neural": 0.25, "causal": 0.22, "symbolic": 0.18, "bayesian": 0.17, "world_model": 0.18},
    }

    # v36.1 FIX: Priority keywords that strongly indicate a query type.
    # When these are found, the query type gets a bonus score to prevent
    # misclassification by weaker keyword overlaps.
    PRIORITY_KEYWORDS = {
        "causal_why": ["لماذا", "سبب", "بسبب", "ما السبب"],
        "technical_code": ["كود", "برمج", "دالة", "class", "def", "python", "javascript", "api", "debug"],
        "logical_math": ["حساب", "احسب", "رياض", "معادل", "math", "calculate"],
    }

    @classmethod
    def classify(cls, query: str) -> dict:
        """
        تصنيف الاستعلام — يحدد نوعه والأدمغة المناسبة

        v36.1 FIX: Uses priority keywords with bonus scoring to prevent
        misclassification (e.g. "لماذا حدث هذا الخطأ" should be causal_why
        even though "خطأ" overlaps with technical_code).

        Returns:
            {"type": str, "brains": list, "weights": dict}
        """
        query_lower = query.lower()

        best_match = None
        best_score = 0

        for qtype, config in cls.QUERY_PATTERNS.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in query_lower:
                    score += 1
            # v36.1 FIX: Bonus for priority keywords — prevents misclassification
            if qtype in cls.PRIORITY_KEYWORDS:
                for pk in cls.PRIORITY_KEYWORDS[qtype]:
                    if pk in query_lower:
                        score += 2  # Strong signal bonus
            if score > best_score:
                best_score = score
                best_match = qtype

        if best_match and best_score >= 1:
            config = cls.QUERY_PATTERNS[best_match]
            return {
                "type": best_match,
                "brains": config["brains"],
                "weights": config["weights"],
            }

        return cls.DEFAULT_CONFIG.copy()


# ─────────────────────────────────────────────────────────────────────────────
# Routed Response
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RoutedResponse:
    """نتيجة التوجيه — استجابة مركّبة من أدمغة متعددة"""
    query: str = ""
    query_type: str = ""
    activated_brains: list = field(default_factory=list)
    brain_responses: dict = field(default_factory=dict)  # brain_id → response dict
    consensus_level: float = 0.0
    conflict_detected: bool = False
    final_response: str = ""
    final_confidence: float = 0.0
    final_reasoning: str = ""
    winning_brain: str = ""
    deliberation_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "query": self.query[:200],
            "query_type": self.query_type,
            "activated_brains": self.activated_brains,
            "brain_responses": {
                bid: {
                    "response": resp.get("response", "")[:300],
                    "confidence": resp.get("confidence", 0),
                    "stance": resp.get("stance", "neutral"),
                    "model_used": resp.get("model_used", ""),
                }
                for bid, resp in self.brain_responses.items()
            },
            "consensus_level": round(self.consensus_level, 3),
            "conflict_detected": self.conflict_detected,
            "final_response": self.final_response,
            "final_confidence": round(self.final_confidence, 3),
            "final_reasoning": self.final_reasoning[:500],
            "winning_brain": self.winning_brain,
            "deliberation_ms": round(self.deliberation_ms, 1),
        }


# ─────────────────────────────────────────────────────────────────────────────
# The Router
# ─────────────────────────────────────────────────────────────────────────────

class BrainRouter:
    """
    موجّه الأدمغة — يوزّع الأسئلة ويجمع الإجابات بذكاء

    Pipeline:
    1. Classify the query → determine which brains to activate
    2. Execute selected brains in parallel (asyncio.gather)
    3. Detect conflicts (opposing stances)
    4. Resolve conflicts via weighted vote or LLM arbitration
    5. Compose final response with reasoning
    """

    def __init__(self, brains: dict = None, llm_client: LLMClient = None):
        """
        Args:
            brains: dict of brain_id → LivingBrain instances
            llm_client: shared LLM client for arbitration
        """
        self._brains: dict = brains or {}
        self._llm = llm_client or get_llm_client()
        self._classifier = QueryClassifier()
        self._history: list[RoutedResponse] = []

        # Adaptive weights: updated based on brain performance
        self._adaptive_weights: dict[str, float] = {}

        logger.info(
            "BrainRouter initialized with %d brains: %s",
            len(self._brains),
            list(self._brains.keys()),
        )

    def register_brain(self, brain_id: str, brain):
        """Register a living brain."""
        self._brains[brain_id] = brain
        self._adaptive_weights[brain_id] = brain.state.weight

    async def route(self, query: str, context: dict = None) -> RoutedResponse:
        """
        توجيه الاستعلام — المسار الرئيسي

        Classify → Execute → Detect → Resolve → Compose
        
        v40.0 Fusion: Added fallback warning detection for brains using
        alternative models due to missing API keys.
        """
        context = context or {}
        start_time = time.time()

        # Step 1: Classify the query
        classification = self._classifier.classify(query)
        activated_brains = classification["brains"]
        base_weights = classification["weights"]

        logger.info(
            "Query classified as '%s' → activating brains: %s",
            classification["type"],
            activated_brains,
        )

        # Step 2: Execute selected brains in PARALLEL
        brain_responses = await self._execute_brains_parallel(
            query, activated_brains, context
        )

        # v40.0 Fusion: Check for fallback model usage and add warnings
        fallback_warnings = self._check_fallback_models(brain_responses)

        # Step 3: Detect conflicts
        conflict = self._detect_conflict(brain_responses)

        # Step 4: Resolve conflicts if any
        if conflict and len(brain_responses) > 1:
            final = await self._resolve_conflict(
                query, brain_responses, base_weights
            )
        else:
            # Step 5: Compose via weighted vote
            final = self._weighted_vote(brain_responses, base_weights)

        duration = (time.time() - start_time) * 1000

        # Build metadata with classification and fallback warnings
        metadata = {"classification": classification}
        if fallback_warnings:
            metadata["fallback_warnings"] = fallback_warnings

        result = RoutedResponse(
            query=query,
            query_type=classification["type"],
            activated_brains=activated_brains,
            brain_responses=brain_responses,
            consensus_level=self._calculate_consensus(brain_responses),
            conflict_detected=conflict,
            final_response=final["response"],
            final_confidence=final["confidence"],
            final_reasoning=final["reasoning"],
            winning_brain=final["winning_brain"],
            deliberation_ms=duration,
            metadata=metadata,
        )

        self._history.append(result)
        self._update_adaptive_weights(result)

        return result

    def _check_fallback_models(self, brain_responses: dict) -> list[str]:
        """
        v40.0 Fusion: فحص استخدام النماذج البديلة
        يتحقق إن كان أي دماغ يستخدم نموذجاً بديلاً بدلاً من النموذج الأصلي
        بسبب عدم توفر مفتاح API المناسب.
        
        Returns a list of warning strings for brains on fallback models.
        """
        warnings = []
        for brain_id, resp in brain_responses.items():
            model_used = resp.get("model_used", "")
            registry_entry = BRAIN_MODEL_REGISTRY.get(brain_id)
            if registry_entry and model_used:
                original_model = registry_entry["original_model"]
                fallback_model = registry_entry["fallback_model"]
                name_ar = registry_entry["name_ar"]
                api_key_env = registry_entry["api_key_env"]
                
                # Check if the brain is using a fallback model
                if model_used != original_model and model_used == fallback_model:
                    warning = (
                        f"Brain {brain_id} ({name_ar}) is using fallback model "
                        f"{fallback_model} instead of original model {original_model}. "
                        f"Set {api_key_env} to enable original model."
                    )
                    warnings.append(warning)
                    logger.warning(warning)
        return warnings

    def get_brain_status(self) -> dict:
        """
        v40.0 Fusion: تقرير حالة الأدمغة التفصيلي
        يعرض لكل دماغ: النموذج الأصلي، النموذج الفعلي، هل على بديل، ومفتاح API المطلوب
        """
        status = {}
        for brain_id, brain in self._brains.items():
            registry_entry = BRAIN_MODEL_REGISTRY.get(brain_id, {})
            actual_model = brain.state.model
            original_model = registry_entry.get("original_model", actual_model)
            fallback_model = registry_entry.get("fallback_model", "")
            is_on_fallback = actual_model != original_model and actual_model == fallback_model
            
            # Check if the API key is available
            api_key_env = registry_entry.get("api_key_env", "")
            has_api_key = bool(os.environ.get(api_key_env, ""))
            
            status[brain_id] = {
                "brain_id": brain_id,
                "name_ar": registry_entry.get("name_ar", brain.state.name_ar),
                "original_model": original_model,
                "actual_model": actual_model,
                "fallback_model": fallback_model,
                "is_on_fallback": is_on_fallback,
                "api_key_env": api_key_env,
                "has_api_key": has_api_key,
                "status": brain.state.status,
                "confidence": round(brain.state.confidence, 3),
                "weight": brain.state.weight,
                "total_interactions": brain.state.total_interactions,
                "error_count": brain.state.error_count,
                "fallback_warning": (
                    f"Brain {brain_id} is using fallback model {actual_model} instead of "
                    f"original model {original_model}. Set {api_key_env} to enable original model."
                ) if is_on_fallback else None,
            }
        
        # Also include brains from registry that aren't registered yet
        for brain_id, registry_entry in BRAIN_MODEL_REGISTRY.items():
            if brain_id not in status:
                api_key_env = registry_entry.get("api_key_env", "")
                status[brain_id] = {
                    "brain_id": brain_id,
                    "name_ar": registry_entry.get("name_ar", ""),
                    "original_model": registry_entry.get("original_model", ""),
                    "actual_model": "not_loaded",
                    "fallback_model": registry_entry.get("fallback_model", ""),
                    "is_on_fallback": False,
                    "api_key_env": api_key_env,
                    "has_api_key": bool(os.environ.get(api_key_env, "")),
                    "status": "not_registered",
                    "confidence": 0.0,
                    "weight": 0.0,
                    "total_interactions": 0,
                    "error_count": 0,
                    "fallback_warning": f"Brain {brain_id} is not loaded. Set {api_key_env} and restart.",
                }
        
        return status

    async def _execute_brains_parallel(
        self, query: str, brain_ids: list, context: dict
    ) -> dict:
        """
        تنفيذ الأدمغة بالتوازي — كل دماغ يفكر في نفس الوقت

        Uses asyncio.gather for true parallel execution.
        Failed brains are skipped gracefully.
        """
        tasks = {}
        for brain_id in brain_ids:
            brain = self._brains.get(brain_id)
            if brain and brain.state.status != "error":
                tasks[brain_id] = brain.think(query, context)

        if not tasks:
            return {}

        # Execute all brains in parallel
        results = await asyncio.gather(
            *tasks.values(), return_exceptions=True
        )

        responses = {}
        for brain_id, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning("Brain '%s' failed: %s", brain_id, result)
                responses[brain_id] = {
                    "brain_id": brain_id,
                    "response": "",
                    "confidence": 0.0,
                    "reasoning": f"Error: {str(result)}",
                    "stance": "neutral",
                    "model_used": "error",
                }
            else:
                responses[brain_id] = result

        return responses

    def _detect_conflict(self, responses: dict) -> bool:
        """
        كشف التناقض — هل الأدمغة تختلف بشكل جوهري؟

        Conflict is detected when:
        - At least one brain opposes while others support
        - Confidence variance is high (>0.3)
        """
        if len(responses) < 2:
            return False

        stances = [r.get("stance", "neutral") for r in responses.values()]
        has_support = "support" in stances
        has_oppose = "oppose" in stances

        # Direct conflict: some support, some oppose
        if has_support and has_oppose:
            return True

        # Confidence conflict: wide spread
        confidences = [r.get("confidence", 0.5) for r in responses.values()]
        if len(confidences) > 1:
            spread = max(confidences) - min(confidences)
            if spread > 0.4:
                return True

        return False

    async def _resolve_conflict(
        self, query: str, responses: dict, weights: dict
    ) -> dict:
        """
        حل التناقض — استخدام LLM كحَكَم عند اختلاف الأدمغة

        When brains disagree significantly, we ask a "judge" LLM to
        arbitrate by presenting all brain responses and asking for
        the best synthesis.
        """
        logger.info("Conflict detected — invoking LLM arbitration")

        # Build arbitration prompt
        brain_views = []
        for brain_id, resp in responses.items():
            brain_views.append(
                f"الدماغ {brain_id} (ثقة: {resp.get('confidence', 0):.2f}، موقف: {resp.get('stance', 'neutral')}):\n"
                f"الإجابة: {resp.get('response', '')[:500]}\n"
                f"الاستدلال: {resp.get('reasoning', '')[:300]}"
            )

        views_text = "\n\n---\n\n".join(brain_views)

        arbitration_prompt = f"""أنت حَكَم في غرفة مداولة مأمون. الأدمغة التالية اختلفت في إجاباتها على السؤال:

السؤال: {query}

آراء الأدمغة:
{views_text}

المطلوب منك:
1. حلل كل رأي بموضوعية
2. حدد أي رأي أقرب للصواب ولماذا
3. ألّف إجابة نهائية تجمع أفضل ما في كل رأي
4. حدد مستوى ثقتك في الإجابة النهائية

أجب بصيغة JSON:
{{
  "response": "الإجابة النهائية المركّبة",
  "confidence": 0.0-1.0,
  "reasoning": "لماذا اخترت هذا التركيب",
  "winning_brain": "أقرب دماغ للصواب",
  "synthesis_method": "كيف ألّفت الإجابة"
}}"""

        response = await self._llm.think(
            prompt=arbitration_prompt,
            system="أنت حَكَم محايد في مأمون. تحلل الآراء المتضاربة وتصنع إجابة مركّبة أفضل.",
            model="glm-5.1",
            temperature=0.3,
            json_mode=True,
        )

        arbitration = response.extract_json()
        if arbitration:
            return {
                "response": arbitration.get("response", ""),
                "confidence": float(arbitration.get("confidence", 0.6)),
                "reasoning": arbitration.get("reasoning", ""),
                "winning_brain": arbitration.get("winning_brain", "arbitrator"),
            }

        # Fallback to weighted vote if arbitration fails
        return self._weighted_vote(responses, weights)

    def _weighted_vote(self, responses: dict, weights: dict) -> dict:
        """
        التصويت الموزون — جمع إجابات الأدمغة بأوزان مختلفة

        The brain with the highest (confidence × weight) wins.
        Its response becomes the primary, with others as supporting context.
        """
        if not responses:
            return {"response": "", "confidence": 0, "reasoning": "", "winning_brain": ""}

        # Calculate composite scores
        scores = {}
        for brain_id, resp in responses.items():
            base_weight = weights.get(brain_id, 0.2)
            adaptive_weight = self._adaptive_weights.get(brain_id, base_weight)
            # Blend base and adaptive weights
            effective_weight = 0.7 * base_weight + 0.3 * adaptive_weight

            confidence = resp.get("confidence", 0.5)
            relevance = resp.get("relevance", 0.5)

            scores[brain_id] = confidence * 0.6 + relevance * 0.2 + effective_weight * 0.2

        # Winner = highest score
        winner = max(scores, key=scores.get)
        winner_resp = responses[winner]

        # Compose final: winner's response + insights from others
        supporting = []
        for brain_id, resp in responses.items():
            if brain_id != winner and resp.get("response"):
                supporting.append(f"[{brain_id}]: {resp.get('response', '')[:200]}")

        final_response = winner_resp.get("response", "")
        if supporting:
            final_response += "\n\nآراء مساندة:\n" + "\n".join(supporting[:3])

        # Weighted average confidence
        total_weight = sum(weights.get(bid, 0.2) for bid in responses)
        if total_weight > 0:
            weighted_conf = sum(
                resp.get("confidence", 0.5) * weights.get(bid, 0.2)
                for bid, resp in responses.items()
            ) / total_weight
        else:
            weighted_conf = winner_resp.get("confidence", 0.5)

        return {
            "response": final_response,
            "confidence": weighted_conf,
            "reasoning": winner_resp.get("reasoning", ""),
            "winning_brain": winner,
        }

    def _calculate_consensus(self, responses: dict) -> float:
        """Calculate consensus level among brain responses."""
        if len(responses) < 2:
            return 1.0

        stances = [r.get("stance", "neutral") for r in responses.values()]
        support_count = stances.count("support")
        oppose_count = stances.count("oppose")

        # Consensus = how much agreement there is
        total = len(stances)
        max_agreement = max(support_count, oppose_count) / total

        # Also factor in confidence alignment
        confidences = [r.get("confidence", 0.5) for r in responses.values()]
        avg_conf = sum(confidences) / len(confidences)

        return max_agreement * 0.6 + avg_conf * 0.4

    def _update_adaptive_weights(self, result: RoutedResponse):
        """
        تحديث الأوزان التكيفية — الأدمغة الناجحة تزيد وزنها

        If a brain's confidence was high and it was the winner,
        increase its weight slightly. If it was wrong or had low
        confidence, decrease.
        """
        alpha = 0.05  # Small update rate

        for brain_id, resp in result.brain_responses.items():
            current = self._adaptive_weights.get(brain_id, 0.2)

            if brain_id == result.winning_brain:
                # Winner gets a boost
                update = alpha * resp.get("confidence", 0.5)
            else:
                # Others get a slight penalty or neutral
                update = -alpha * 0.1

            self._adaptive_weights[brain_id] = max(0.05, min(0.60, current + update))

    def get_stats(self) -> dict:
        """Get routing statistics."""
        if not self._history:
            return {"total_queries": 0}

        win_counts = {}
        for result in self._history:
            wb = result.winning_brain
            win_counts[wb] = win_counts.get(wb, 0) + 1

        return {
            "total_queries": len(self._history),
            "conflict_rate": sum(1 for r in self._history if r.conflict_detected) / len(self._history),
            "avg_consensus": sum(r.consensus_level for r in self._history) / len(self._history),
            "avg_deliberation_ms": sum(r.deliberation_ms for r in self._history) / len(self._history),
            "brain_wins": win_counts,
            "adaptive_weights": dict(self._adaptive_weights),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────

_brain_router: Optional[BrainRouter] = None


def get_brain_router() -> BrainRouter:
    """Get the global brain router instance."""
    global _brain_router
    if _brain_router is None:
        _brain_router = BrainRouter()
    return _brain_router
