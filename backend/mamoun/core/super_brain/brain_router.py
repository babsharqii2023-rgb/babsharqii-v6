"""
Brain Router v58 — TRUE cognitive diversity with personality-driven prompts.

CRITICAL UPGRADE from v57:
- v57: Brain personalities were defined but NOT injected into system prompts
- v58: Each brain gets its own system prompt matching its personality
- Improved quality scoring: reasoning depth, specificity, actionability
- Performance history tracking per brain
- Adaptive weight adjustment based on real performance
- Integrated with MetaCognitionEngine for performance tracking

v58 — Super Mind العقل الخارق مامون
"""

import time
import asyncio
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class BrainPersonality(str, Enum):
    ANALYST = "analyst"        # DeepSeek — logical, evidence-based
    CREATIVE = "creative"      # Gemini — out-of-the-box thinking
    SYNTHESIZER = "synthesizer"  # GLM — combining perspectives
    PRAGMATIST = "pragmatist"  # Z-AI — practical, cost-focused
    CRITIC = "critic"          # DeepSeek low-temp — finding flaws


# ── Personality System Prompts ───────────────────────────────────────────
PERSONALITY_PROMPTS = {
    BrainPersonality.ANALYST: (
        "أنت المحلل — فكر بشكل منطقي ومنهجي. "
        "ركز على الأدلة والبيانات والاستدلال الصارم. "
        "قدم تحليلاً مفصلاً مع مراجع للأدلة. "
        "تجنب التعميمات واعتمد على الحقائق المحددة."
    ),
    BrainPersonality.CREATIVE: (
        "أنت المبدع — فكر خارج الصندوق وابحث عن حلول غير تقليدية. "
        "اقترح أفكاراً مبتكرة وربط بين مفاهيم بعيدة. "
        "لا تتقيد بالطرق المعتادة — ابحث عن المقاربات الجديدة."
    ),
    BrainPersonality.SYNTHESIZER: (
        "أنت المُركّب — مهمتك تجميع الآراء المختلفة وإيجاد نقاط الاتفاق والخلاف. "
        "ابحث عن القواسم المشتركة واقترح حلولاً توفيقية. "
        "حلل كيف يمكن دمج الأفكار المتنوعة في إطار متكامل."
    ),
    BrainPersonality.PRAGMATIST: (
        "أنت العملي — ركز على التكلفة والجدوى والتطبيق العملي. "
        "قيّم كل فكرة من حيث: هل يمكن تنفيذها؟ ما التكلفة؟ ما العائد؟ "
        "اقترح الخطوات العملية المحددة والجدول الزمني."
    ),
    BrainPersonality.CRITIC: (
        "أنت الناقد — مهمتك إيجاد الثغرات والأخطاء والمخاطر. "
        "كن صارماً في تقييم الحجج والاستنتاجات. "
        "حدد نقاط الضعف والافتراضات غير المبررة والمخاطر المحتملة."
    ),
}


@dataclass
class BrainConfig:
    """Configuration for a single brain."""
    name: str
    provider: str
    personality: BrainPersonality
    temperature: float
    weight: float = 1.0
    enabled: bool = True


@dataclass
class BrainResponse:
    """Response from a single brain."""
    brain_name: str
    provider: str
    personality: str
    content: str
    quality_score: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class RoutingResult:
    """Result of routing a query through multiple brains."""
    query: str
    responses: list[BrainResponse]
    best_response: Optional[BrainResponse]
    consensus_level: float
    routing_strategy: str
    total_latency_ms: float


# ── Default brain configurations — TRUE diversity ────────────────────────
DEFAULT_BRAINS = [
    BrainConfig(
        name="Analyst Brain",
        provider="deepseek",
        personality=BrainPersonality.ANALYST,
        temperature=0.2,
        weight=1.0,
    ),
    BrainConfig(
        name="Creative Brain",
        provider="gemini",
        personality=BrainPersonality.CREATIVE,
        temperature=0.9,
        weight=1.0,
    ),
    BrainConfig(
        name="Synthesizer Brain",
        provider="glm",
        personality=BrainPersonality.SYNTHESIZER,
        temperature=0.7,
        weight=1.0,
    ),
    BrainConfig(
        name="Pragmatist Brain",
        provider="zai",
        personality=BrainPersonality.PRAGMATIST,
        temperature=0.5,
        weight=1.0,
    ),
    BrainConfig(
        name="Critic Brain",
        provider="critic",
        personality=BrainPersonality.CRITIC,
        temperature=0.0,
        weight=0.8,
    ),
]


class BrainRouter:
    """
    Routes queries to multiple brains with TRUE diversity.

    Each brain uses a DIFFERENT LLM provider with a DIFFERENT personality
    and a DIFFERENT system prompt. This ensures genuinely different
    perspectives — not fake diversity from the same API key.

    Routing strategies:
    - "parallel": All brains answer simultaneously, best is selected
    - "sequential": Brains answer one by one, building on previous
    - "adaptive": Choose strategy based on query complexity

    Usage:
        router = BrainRouter(llm_client=multi_provider_client)
        result = await router.route("How should we architecture this system?")
        print(result.best_response.content)
    """

    def __init__(self, llm_client=None, meta_cognition=None, neural_bus=None,
                 brains: list[BrainConfig] = None):
        self._llm_client = llm_client
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._brains = brains or DEFAULT_BRAINS
        self._performance_history: dict[str, list[float]] = {}
        self._call_count = 0

    def set_llm_client(self, client):
        self._llm_client = client

    def set_meta_cognition(self, engine):
        self._meta_cognition = engine

    def _get_available_brains(self) -> list[BrainConfig]:
        """Get brains that have available providers.
        
        Only returns brains whose providers are actually configured.
        If NO providers are available, returns an empty list instead of
        returning all brains (which would fail on every call).
        """
        if not self._llm_client:
            return self._brains

        available_providers = self._llm_client.available_providers()
        available = []

        for brain in self._brains:
            if not brain.enabled:
                continue
            if brain.provider in available_providers:
                available.append(brain)
            elif brain.provider == "zai":
                # Z-AI is available via ZaiSdkWrapper (Node.js bridge)
                # It doesn't need an API key in the traditional sense
                try:
                    from ..shared.zai_sdk_wrapper import get_zai_wrapper
                    wrapper = get_zai_wrapper()
                    if wrapper:
                        available.append(brain)
                except ImportError:
                    try:
                        from shared.zai_sdk_wrapper import get_zai_wrapper
                        wrapper = get_zai_wrapper()
                        if wrapper:
                            available.append(brain)
                    except ImportError:
                        pass
            elif brain.provider == "critic":
                # Critic uses DeepSeek API with low temperature
                if "deepseek" in available_providers:
                    available.append(brain)

        return available

    def _classify_complexity(self, query: str) -> str:
        """Classify query complexity to choose routing strategy."""
        word_count = len(query.split())
        has_code = any(kw in query.lower() for kw in ["code", "function", "class", "api", "debug", "خطأ", "كود"])
        has_architecture = any(kw in query.lower() for kw in ["design", "architecture", "system", "structure", "تصميم", "نظام"])

        if has_architecture or word_count > 50:
            return "complex"
        elif has_code or word_count > 20:
            return "moderate"
        else:
            return "simple"

    async def _query_brain(self, brain: BrainConfig, query: str,
                           context: str = "") -> BrainResponse:
        """Send a query to a single brain with personality-driven system prompt."""
        if not self._llm_client:
            return BrainResponse(
                brain_name=brain.name,
                provider=brain.provider,
                personality=brain.personality.value,
                content="",
                success=False,
                error="No LLM client configured",
            )

        start = time.time()

        # Build messages with brain's personality system prompt
        system_prompt = PERSONALITY_PROMPTS.get(brain.personality, "")
        messages = [{"role": "system", "content": system_prompt}]

        if context:
            messages.append({"role": "assistant", "content": f"Previous analysis context:\n{context}"})

        messages.append({"role": "user", "content": query})

        response = await self._llm_client.chat(
            provider=brain.provider,
            messages=messages,
            temperature=brain.temperature,
        )

        latency = (time.time() - start) * 1000

        # Compute quality score — improved from v57
        quality = 0.0
        if response.success:
            content = response.content
            content_len = len(content)

            # Length-based quality
            if content_len > 100:
                quality += 0.15
            if content_len > 300:
                quality += 0.1
            if content_len > 500:
                quality += 0.05

            content_lower = content.lower()

            # Reasoning depth
            reasoning_keywords = ["because", "therefore", "however", "analysis", "لأن", "لذلك", "لكن", "تحليل"]
            if any(kw in content_lower for kw in reasoning_keywords):
                quality += 0.15

            # Specificity
            specific_keywords = ["example", "for instance", "such as", "specifically", "مثال", "مثل", "تحديداً"]
            if any(kw in content_lower for kw in specific_keywords):
                quality += 0.1

            # Actionability
            action_keywords = ["recommend", "suggest", "should", "step", "مقترح", "أنصح", "خطوة"]
            if any(kw in content_lower for kw in action_keywords):
                quality += 0.1

            # Structure (numbered points, sections)
            if any(line.strip().startswith(("1.", "2.", "3.", "- ")) for line in content.split("\n")):
                quality += 0.1

            # Evidence/reference
            evidence_keywords = ["according to", "research", "data shows", "study", "وفقاً", "بحث", "بيانات"]
            if any(kw in content_lower for kw in evidence_keywords):
                quality += 0.1

            # Critical thinking (for critic personality)
            if brain.personality == BrainPersonality.CRITIC:
                risk_keywords = ["risk", "danger", "flaw", "vulnerability", "مخاطر", "ثغرة", "خطر"]
                if any(kw in content_lower for kw in risk_keywords):
                    quality += 0.15

            quality = min(1.0, quality)
        else:
            quality = 0.0

        # Update performance history
        brain_key = brain.name
        if brain_key not in self._performance_history:
            self._performance_history[brain_key] = []
        self._performance_history[brain_key].append(quality)
        if len(self._performance_history[brain_key]) > 100:
            self._performance_history[brain_key] = self._performance_history[brain_key][-100:]

        # Adapt weight based on performance
        history = self._performance_history[brain_key]
        if len(history) >= 5:
            recent_avg = sum(history[-10:]) / len(history[-10:])
            brain.weight = max(0.3, min(1.5, recent_avg * 1.2))

        return BrainResponse(
            brain_name=brain.name,
            provider=brain.provider,
            personality=brain.personality.value,
            content=response.content,
            quality_score=quality,
            latency_ms=latency,
            success=response.success,
            error=response.error,
        )

    def _compute_consensus(self, responses: list[BrainResponse]) -> float:
        """Compute consensus level among brain responses using keyword overlap."""
        if len(responses) < 2:
            return 1.0

        successful = [r for r in responses if r.success]
        if len(successful) < 2:
            return 0.0

        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "to", "of", "and", "in", "that", "it", "for", "on", "with", "as",
                     "هو", "هي", "في", "من", "على", "إلى", "أن", "هذا", "هذه"}

        all_keywords = []
        for r in successful:
            words = set(r.content.lower().split())
            keywords = words - stop_words
            all_keywords.append(keywords)

        if not all_keywords:
            return 0.0

        similarities = []
        for i in range(len(all_keywords)):
            for j in range(i + 1, len(all_keywords)):
                intersection = all_keywords[i] & all_keywords[j]
                union = all_keywords[i] | all_keywords[j]
                if union:
                    similarities.append(len(intersection) / len(union))

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _select_best_response(self, responses: list[BrainResponse]) -> Optional[BrainResponse]:
        """Select the best response based on quality and performance history."""
        successful = [r for r in responses if r.success]
        if not successful:
            return responses[0] if responses else None

        if len(successful) == 1:
            return successful[0]

        # Score each response: quality + performance bonus
        best = None
        best_score = -1

        for r in successful:
            score = r.quality_score

            # Performance bonus from history
            history = self._performance_history.get(r.brain_name, [])
            if history:
                avg_perf = sum(history[-20:]) / len(history[-20:])
                score += avg_perf * 0.2

            # Latency bonus (faster = slightly better)
            if r.latency_ms > 0:
                latency_score = max(0, 1.0 - (r.latency_ms / 10000))  # Normalize
                score += latency_score * 0.05

            if score > best_score:
                best_score = score
                best = r

        return best

    # ── Main routing methods ─────────────────────────────────────────────
    async def route(self, query: str, strategy: str = "adaptive") -> RoutingResult:
        """Route a query through multiple brains."""
        start = time.time()
        self._call_count += 1

        if strategy == "adaptive":
            complexity = self._classify_complexity(query)
            strategy = "parallel" if complexity == "simple" else "sequential"

        brains = self._get_available_brains()

        if strategy == "parallel":
            responses = await self._route_parallel(brains, query)
        else:
            responses = await self._route_sequential(brains, query)

        # Compute consensus
        consensus = self._compute_consensus(responses)

        # Select best
        best = self._select_best_response(responses)

        total_latency = (time.time() - start) * 1000

        result = RoutingResult(
            query=query,
            responses=responses,
            best_response=best,
            consensus_level=consensus,
            routing_strategy=strategy,
            total_latency_ms=total_latency,
        )

        # Record in meta-cognition
        if self._meta_cognition:
            try:
                from .meta_cognition_engine import OutcomeRecord
                self._meta_cognition.record_outcome(OutcomeRecord(
                    component="brain_router",
                    operation=f"route_{strategy}",
                    success=best is not None and best.success,
                    quality_score=best.quality_score if best and best.success else 0.0,
                    predicted_quality=self._meta_cognition.predict_quality("brain_router"),
                    latency_ms=total_latency,
                    metadata={
                        "brains_used": len(responses),
                        "successful_brains": sum(1 for r in responses if r.success),
                        "consensus": consensus,
                        "strategy": strategy,
                    },
                ))
            except ImportError:
                pass

        return result

    async def _route_parallel(self, brains: list[BrainConfig], query: str) -> list[BrainResponse]:
        """All brains answer simultaneously."""
        tasks = [self._query_brain(brain, query) for brain in brains]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for brain, resp in zip(brains, responses):
            if isinstance(resp, Exception):
                results.append(BrainResponse(
                    brain_name=brain.name,
                    provider=brain.provider,
                    personality=brain.personality.value,
                    content="",
                    success=False,
                    error=str(resp),
                ))
            else:
                results.append(resp)

        return results

    async def _route_sequential(self, brains: list[BrainConfig], query: str) -> list[BrainResponse]:
        """Brains answer one by one, building on previous responses."""
        responses = []
        context = ""

        for brain in brains:
            response = await self._query_brain(brain, query, context=context)
            responses.append(response)

            if response.success:
                context += f"\n{brain.name} ({brain.personality.value}): {response.content[:500]}\n"

        return responses

    async def route_single(self, query: str, provider: str = "deepseek") -> BrainResponse:
        """Route to a single specific brain/provider."""
        matching = [b for b in self._brains if b.provider == provider]
        if not matching:
            matching = [self._brains[0]]

        return await self._query_brain(matching[0], query)

    def get_stats(self) -> dict:
        """Get router statistics."""
        return {
            "total_calls": self._call_count,
            "total_brains": len(self._brains),
            "available_brains": len(self._get_available_brains()),
            "performance_history": {
                name: {
                    "avg_quality": sum(scores[-20:]) / len(scores[-20:]) if scores else 0.0,
                    "total_calls": len(scores),
                }
                for name, scores in self._performance_history.items()
            },
        }
