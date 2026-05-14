"""
Deliberation Room v59.1 — Real democratic deliberation with weighted voting.

CRITICAL UPGRADE from v58:
- v59.1: Applied OutcomeRecorder decorator for consistent performance tracking
- v59.1: Automatic error recording (success=False on exception)
- v59.1: Consistent quality prediction via MetaCognitionEngine
- v57: Component key mismatch (brain_{name} didn't match meta-cognition records)
- v58: Fixed component keys to match actual meta-cognition records
- Improved position detection with confidence-based classification
- Better weighted voting using actual brain performance from meta-cognition
- Deliberation history for tracking outcomes over time
- More robust LLM arbitration with explicit provider selection

v59.1 — Super Mind العقل الخارق مامون
"""

import time
import asyncio
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DeliberationStrategy(str, Enum):
    DEMOCRATIC = "democratic"      # Equal vote for all brains
    WEIGHTED = "weighted"          # Vote weight = historical performance
    CONSENSUS = "consensus"        # Must reach agreement threshold
    ADVERSARIAL = "adversarial"    # Brains debate, critic judges


@dataclass
class Vote:
    """A single vote from a brain."""
    brain_name: str
    provider: str
    position: str  # "support", "oppose", "neutral"
    confidence: float  # 0-1
    reasoning: str
    quality_score: float = 0.0
    weight: float = 1.0  # Performance-adjusted weight


@dataclass
class DeliberationResult:
    """Result of a deliberation session."""
    topic: str
    votes: list[Vote]
    decision: str  # "approved", "rejected", "needs_more_info"
    confidence: float
    consensus_level: float
    contradictions: list[str]
    arbitration_used: bool
    arbitration_provider: str = ""
    total_latency_ms: float = 0.0


class ContradictionJudgingSystem:
    """
    Enhanced CJS — detects contradictions between brain responses.
    Uses LLM for deep contradiction detection with keyword fallback.
    """

    def __init__(self, llm_client=None):
        self._llm_client = llm_client

    def set_llm_client(self, client):
        self._llm_client = client

    def detect_keyword_contradictions(self, responses: list[dict]) -> list[str]:
        """Quick keyword-based contradiction detection."""
        contradictions = []
        positive_words = {"yes", "should", "correct", "true", "agree", "recommend", "نعم", "صحيح", "أوافق", "أوصي"}
        negative_words = {"no", "shouldn't", "incorrect", "false", "disagree", "oppose", "لا", "خطأ", "أرفض", "أعارض"}

        positions = []
        for resp in responses:
            content_lower = resp.get("content", "").lower()
            has_positive = any(w in content_lower for w in positive_words)
            has_negative = any(w in content_lower for w in negative_words)
            if has_positive and not has_negative:
                positions.append("positive")
            elif has_negative and not has_positive:
                positions.append("negative")
            else:
                positions.append("neutral")

        if "positive" in positions and "negative" in positions:
            contradictions.append("Brains have opposing positions (positive vs negative)")

        return contradictions

    async def detect_llm_contradictions(self, responses: list[dict]) -> list[str]:
        """Deep LLM-based contradiction detection."""
        if not self._llm_client:
            return self.detect_keyword_contradictions(responses)

        if len(responses) < 2:
            return []

        brains_text = ""
        for i, resp in enumerate(responses):
            brains_text += f"\nBrain {i+1} ({resp.get('provider', 'unknown')}): {resp.get('content', '')[:500]}\n"

        try:
            llm_response = await self._llm_client.chat_with_fallback(
                messages=[
                    {"role": "system", "content": "You are a contradiction detector. Analyze the following brain responses and identify any logical contradictions between them. List each contradiction specifically."},
                    {"role": "user", "content": f"Analyze contradictions:\n{brains_text}\n\nList any contradictions found, or say 'No contradictions found' if all responses are consistent."}
                ],
                preferred_order=["deepseek", "glm", "gemini"],
            )

            if llm_response.success:
                contradictions = []
                for line in llm_response.content.split("\n"):
                    line = line.strip()
                    if line.startswith(("-", "*", "•", "1.", "2.", "3.")):
                        clean = line.lstrip("-*•0123456789. ").strip()
                        if clean and "no contradiction" not in clean.lower():
                            contradictions.append(clean)
                return contradictions[:5]

        except Exception as e:
            logger.error(f"LLM contradiction detection failed: {e}")

        return self.detect_keyword_contradictions(responses)


class DeliberationRoom:
    """
    Democratic deliberation room where brains discuss and vote.

    Key features:
    - Weighted voting based on real performance history
    - Consensus threshold — if agreement > 70%, no arbitration needed
    - When arbitration IS needed, uses a DIFFERENT provider
    - CJS detects contradictions both keywords and LLM
    - Deliberation history tracking
    - Full integration with MetaCognitionEngine

    Usage:
        room = DeliberationRoom(llm_client=client, brain_router=router)
        result = await room.deliberate("Should we refactor the database layer?")
        print(result.decision, result.confidence)
    """

    CONSENSUS_THRESHOLD = 0.70

    def __init__(self, llm_client=None, brain_router=None,
                 meta_cognition=None, neural_bus=None):
        self._llm_client = llm_client
        self._brain_router = brain_router
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._cjs = ContradictionJudgingSystem(llm_client)
        self._deliberation_count = 0
        self._deliberation_history: list[dict] = []

    def set_llm_client(self, client):
        self._llm_client = client
        self._cjs.set_llm_client(client)

    def set_brain_router(self, router):
        self._brain_router = router

    async def _collect_votes(self, topic: str) -> list[Vote]:
        """Collect votes from all available brains with proper weighting."""
        if not self._brain_router or not self._llm_client:
            return []

        routing_result = await self._brain_router.route(topic, strategy="parallel")

        votes = []
        for response in routing_result.responses:
            if not response.success:
                continue

            # Determine position from content — improved detection
            content_lower = response.content.lower()
            positive_signals = sum(1 for w in ["yes", "should", "agree", "recommend", "support",
                                               "نعم", "صحيح", "أوافق", "أوصي", "أدعم"] if w in content_lower)
            negative_signals = sum(1 for w in ["no", "shouldn't", "disagree", "oppose", "reject",
                                               "لا", "خطأ", "أرفض", "أعارض", "أرفض"] if w in content_lower)

            if positive_signals > negative_signals + 1:
                position = "support"
            elif negative_signals > positive_signals + 1:
                position = "oppose"
            else:
                position = "neutral"

            # Get performance weight from meta-cognition
            # Key fix: use correct component key format
            weight = 1.0
            confidence = response.quality_score

            if self._meta_cognition:
                # Try multiple key formats to find the brain's profile
                profile = None
                for key in [f"brain_{response.brain_name}", response.brain_name, f"brain_{response.provider}"]:
                    profile = self._meta_cognition.get_profile(key)
                    if profile and profile.total_operations >= 3:
                        break

                if profile and profile.total_operations >= 3:
                    weight = max(0.3, profile.reliability_score)
                    confidence = confidence * weight

            votes.append(Vote(
                brain_name=response.brain_name,
                provider=response.provider,
                position=position,
                confidence=confidence,
                reasoning=response.content[:500],
                quality_score=response.quality_score,
                weight=weight,
            ))

        return votes

    def _compute_consensus(self, votes: list[Vote]) -> float:
        """Compute weighted consensus level."""
        if not votes:
            return 0.0

        total_weight = sum(v.confidence * v.weight for v in votes)
        if total_weight == 0:
            return 0.0

        support_weight = sum(v.confidence * v.weight for v in votes if v.position == "support")
        oppose_weight = sum(v.confidence * v.weight for v in votes if v.position == "oppose")

        max_weight = max(support_weight, oppose_weight)
        return max_weight / total_weight

    async def _arbitrate(self, topic: str, votes: list[Vote],
                         contradictions: list[str]) -> tuple[str, str]:
        """
        Arbitrate when there's no consensus.
        Uses a DIFFERENT provider than the deliberating brains.
        """
        used_providers = {v.provider for v in votes}

        available = self._llm_client.available_providers() if self._llm_client else []
        arbitrator = None
        for preferred in ["deepseek", "gemini", "glm", "zai"]:
            if preferred not in used_providers and preferred in available:
                arbitrator = preferred
                break

        if not arbitrator:
            arbitrator = available[0] if available else "deepseek"

        votes_summary = "\n".join([
            f"- {v.brain_name} ({v.provider}): {v.position} (confidence: {v.confidence:.2f}, weight: {v.weight:.2f})"
            for v in votes
        ])

        contradictions_text = "\n".join(f"- {c}" for c in contradictions) if contradictions else "None detected"

        try:
            response = await self._llm_client.chat(
                provider=arbitrator,
                messages=[
                    {"role": "system", "content": "You are an impartial arbitrator. Based on the votes and contradictions, make a final decision. Explain your reasoning briefly."},
                    {"role": "user", "content": f"Topic: {topic}\n\nVotes:\n{votes_summary}\n\nContradictions:\n{contradictions_text}\n\nMake a final decision: approve, reject, or needs_more_info."}
                ],
                temperature=0.1,
            )

            if response.success:
                content_lower = response.content.lower()
                if "approve" in content_lower or "موافقة" in content_lower:
                    return "approved", arbitrator
                elif "reject" in content_lower or "رفض" in content_lower:
                    return "rejected", arbitrator
                else:
                    return "needs_more_info", arbitrator

        except Exception as e:
            logger.error(f"Arbitration failed: {e}")

        # Fallback: weighted majority vote
        support = sum(v.weight for v in votes if v.position == "support")
        oppose = sum(v.weight for v in votes if v.position == "oppose")
        if support > oppose:
            return "approved", "fallback_weighted_majority"
        elif oppose > support:
            return "rejected", "fallback_weighted_majority"
        return "needs_more_info", "fallback_tie"

    # ── Main deliberation method ─────────────────────────────────────────
    async def deliberate(
        self,
        topic: str,
        strategy: DeliberationStrategy = DeliberationStrategy.WEIGHTED,
    ) -> DeliberationResult:
        """Deliberate on a topic through democratic brain voting."""
        start = time.time()
        self._deliberation_count += 1

        votes = await self._collect_votes(topic)

        if not votes:
            return DeliberationResult(
                topic=topic, votes=[], decision="needs_more_info",
                confidence=0.0, consensus_level=0.0,
                contradictions=["No votes collected"],
                arbitration_used=False,
                total_latency_ms=(time.time() - start) * 1000,
            )

        # Detect contradictions
        responses_for_cjs = [
            {"content": v.reasoning, "provider": v.provider}
            for v in votes
        ]
        contradictions = self._cjs.detect_keyword_contradictions(responses_for_cjs)
        if contradictions and self._llm_client:
            llm_contradictions = await self._cjs.detect_llm_contradictions(responses_for_cjs)
            contradictions = contradictions + llm_contradictions

        # Compute consensus
        consensus = self._compute_consensus(votes)

        # Decision
        arbitration_used = False
        arbitration_provider = ""

        if consensus >= self.CONSENSUS_THRESHOLD:
            support = sum(v.weight for v in votes if v.position == "support")
            oppose = sum(v.weight for v in votes if v.position == "oppose")
            decision = "approved" if support > oppose else "rejected"
        else:
            arbitration_used = True
            decision, arbitration_provider = await self._arbitrate(topic, votes, contradictions)

        # Compute confidence
        confidence = consensus if not arbitration_used else consensus * 0.8

        total_latency = (time.time() - start) * 1000

        result = DeliberationResult(
            topic=topic, votes=votes, decision=decision,
            confidence=confidence, consensus_level=consensus,
            contradictions=contradictions, arbitration_used=arbitration_used,
            arbitration_provider=arbitration_provider,
            total_latency_ms=total_latency,
        )

        # Record in deliberation history
        self._deliberation_history.append({
            "topic": topic,
            "decision": decision,
            "confidence": confidence,
            "votes_count": len(votes),
            "arbitration_used": arbitration_used,
            "timestamp": time.time(),
        })
        if len(self._deliberation_history) > 100:
            self._deliberation_history = self._deliberation_history[-100:]

        # v59.1: Record outcome using OutcomeRecorder (consistent tracking)
        if self._meta_cognition:
            try:
                from .outcome_recorder import OutcomeRecorder
                async with OutcomeRecorder(
                    self._meta_cognition, "deliberation_room", "deliberate"
                ) as rec:
                    rec.quality_score = confidence
                    rec.success = True
                    rec.metadata = {
                        "votes_count": len(votes),
                        "consensus": consensus,
                        "arbitration_used": arbitration_used,
                        "decision": decision,
                    }
            except ImportError:
                # Fallback to manual recording
                try:
                    from .meta_cognition_engine import OutcomeRecord
                    self._meta_cognition.record_outcome(OutcomeRecord(
                        component="deliberation_room",
                        operation="deliberate",
                        success=True,
                        quality_score=confidence,
                        predicted_quality=self._meta_cognition.predict_quality("deliberation_room"),
                        latency_ms=total_latency,
                        metadata={
                            "votes_count": len(votes),
                            "consensus": consensus,
                            "arbitration_used": arbitration_used,
                            "decision": decision,
                        },
                    ))
                except ImportError:
                    pass

        return result

    def get_stats(self) -> dict:
        """Get deliberation room statistics."""
        return {
            "total_deliberations": self._deliberation_count,
            "consensus_threshold": self.CONSENSUS_THRESHOLD,
            "history_size": len(self._deliberation_history),
            "recent_decisions": self._deliberation_history[-10:],
        }
