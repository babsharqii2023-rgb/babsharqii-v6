"""
Deliberation Room v57 — Real democratic deliberation with weighted voting.

CRITICAL UPGRADE from v56:
- v56: Arbitration by the same provider = biased
- v57: Weighted voting by real performance + different-provider arbitration
- CJS (Contradiction Judging System) enhanced with cross-provider verification
- Consensus threshold — if agreement is high, no arbitration needed
- Arbitration uses a DIFFERENT provider than the deliberating brains

v57 — Super Mind العقل الخارق مامون
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
    Now uses LLM to detect real logical contradictions.
    """

    def __init__(self, llm_client=None):
        self._llm_client = llm_client

    def set_llm_client(self, client):
        self._llm_client = client

    def detect_keyword_contradictions(self, responses: list[dict]) -> list[str]:
        """Quick keyword-based contradiction detection."""
        contradictions = []
        positive_words = {"yes", "should", "correct", "true", "agree", "recommend", "نعم", "صحيح"}
        negative_words = {"no", "shouldn't", "incorrect", "false", "disagree", "oppose", "لا", "خطأ"}

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

        # Build comparison prompt
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
                # Parse contradictions from LLM response
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
    - Full integration with MetaCognitionEngine

    Usage:
        room = DeliberationRoom(llm_client=client, brain_router=router)
        result = await room.deliberate("Should we refactor the database layer?")
        print(result.decision, result.confidence)
    """

    CONSENSUS_THRESHOLD = 0.70  # If 70% agree, no arbitration needed

    def __init__(self, llm_client=None, brain_router=None,
                 meta_cognition=None, neural_bus=None):
        self._llm_client = llm_client
        self._brain_router = brain_router
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._cjs = ContradictionJudgingSystem(llm_client)
        self._deliberation_count = 0

    def set_llm_client(self, client):
        self._llm_client = client
        self._cjs.set_llm_client(client)

    def set_brain_router(self, router):
        self._brain_router = router

    async def _collect_votes(self, topic: str) -> list[Vote]:
        """Collect votes from all available brains."""
        if not self._brain_router or not self._llm_client:
            return []

        # Route the topic through all brains
        routing_result = await self._brain_router.route(topic, strategy="parallel")

        votes = []
        for response in routing_result.responses:
            if not response.success:
                continue

            # Determine position from content
            content_lower = response.content.lower()
            positive = sum(1 for w in ["yes", "should", "agree", "recommend", "support", "نعم", "أوافق"] if w in content_lower)
            negative = sum(1 for w in ["no", "shouldn't", "disagree", "oppose", "reject", "لا", "أرفض"] if w in content_lower)

            if positive > negative:
                position = "support"
            elif negative > positive:
                position = "oppose"
            else:
                position = "neutral"

            # Confidence from quality score
            confidence = response.quality_score

            # Get performance weight from meta-cognition
            weight = 1.0
            if self._meta_cognition:
                profile = self._meta_cognition.get_profile(f"brain_{response.brain_name}")
                if profile and profile.total_operations >= 5:
                    weight = profile.reliability_score

            votes.append(Vote(
                brain_name=response.brain_name,
                provider=response.provider,
                position=position,
                confidence=confidence * weight,  # Weight by real performance
                reasoning=response.content[:500],
                quality_score=response.quality_score,
            ))

        return votes

    def _compute_consensus(self, votes: list[Vote]) -> float:
        """Compute weighted consensus level."""
        if not votes:
            return 0.0

        total_weight = sum(v.confidence for v in votes)
        if total_weight == 0:
            return 0.0

        # Count weighted support
        support_weight = sum(v.confidence for v in votes if v.position == "support")
        oppose_weight = sum(v.confidence for v in votes if v.position == "oppose")

        # Consensus = how much the majority agrees
        max_weight = max(support_weight, oppose_weight)
        return max_weight / total_weight

    async def _arbitrate(self, topic: str, votes: list[Vote],
                         contradictions: list[str]) -> tuple[str, str]:
        """
        Arbitrate when there's no consensus.
        Uses a DIFFERENT provider than the deliberating brains.
        Returns (decision, provider_used).
        """
        # Find which providers were used in voting
        used_providers = {v.provider for v in votes}

        # Choose an ARBITRATOR from a DIFFERENT provider
        available = self._llm_client.available_providers() if self._llm_client else []
        arbitrator = None
        for preferred in ["deepseek", "gemini", "glm", "zai"]:
            if preferred not in used_providers and preferred in available:
                arbitrator = preferred
                break

        if not arbitrator:
            # All providers used — use the one with best performance
            arbitrator = available[0] if available else "deepseek"

        # Build arbitration prompt
        votes_summary = "\n".join([
            f"- {v.brain_name} ({v.provider}): {v.position} (confidence: {v.confidence:.2f})"
            for v in votes
        ])

        contradictions_text = "\n".join(f"- {c}" for c in contradictions) if contradictions else "None detected"

        try:
            response = await self._llm_client.chat(
                provider=arbitrator,
                messages=[
                    {"role": "system", "content": "You are an impartial arbitrator. Based on the votes and contradictions, make a final decision. Explain your reasoning."},
                    {"role": "user", "content": f"Topic: {topic}\n\nVotes:\n{votes_summary}\n\nContradictions:\n{contradictions_text}\n\nMake a final decision: approve, reject, or needs_more_info."}
                ],
                temperature=0.1,  # Low temperature for arbitration = more deterministic
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

        # Fallback: simple majority vote
        support = sum(1 for v in votes if v.position == "support")
        oppose = sum(1 for v in votes if v.position == "oppose")
        if support > oppose:
            return "approved", "fallback_majority"
        elif oppose > support:
            return "rejected", "fallback_majority"
        return "needs_more_info", "fallback_tie"

    # ── Main deliberation method ─────────────────────────────────────────
    async def deliberate(
        self,
        topic: str,
        strategy: DeliberationStrategy = DeliberationStrategy.WEIGHTED,
    ) -> DeliberationResult:
        """
        Deliberate on a topic through democratic brain voting.

        Args:
            topic: The topic/proposal to deliberate on
            strategy: Voting strategy

        Returns:
            DeliberationResult with votes, decision, and confidence
        """
        start = time.time()
        self._deliberation_count += 1

        # 1. Collect votes from all brains
        votes = await self._collect_votes(topic)

        if not votes:
            return DeliberationResult(
                topic=topic,
                votes=[],
                decision="needs_more_info",
                confidence=0.0,
                consensus_level=0.0,
                contradictions=["No votes collected"],
                arbitration_used=False,
                total_latency_ms=(time.time() - start) * 1000,
            )

        # 2. Detect contradictions (enhanced CJS)
        responses_for_cjs = [
            {"content": v.reasoning, "provider": v.provider}
            for v in votes
        ]

        # Quick keyword check first
        contradictions = self._cjs.detect_keyword_contradictions(responses_for_cjs)

        # Deep LLM check if there are keyword contradictions
        if contradictions and self._llm_client:
            llm_contradictions = await self._cjs.detect_llm_contradictions(responses_for_cjs)
            contradictions = contradictions + llm_contradictions

        # 3. Compute consensus
        consensus = self._compute_consensus(votes)

        # 4. Decision
        arbitration_used = False
        arbitration_provider = ""

        if consensus >= self.CONSENSUS_THRESHOLD:
            # High consensus — no arbitration needed
            support = sum(1 for v in votes if v.position == "support")
            oppose = sum(1 for v in votes if v.position == "oppose")
            decision = "approved" if support > oppose else "rejected"
        else:
            # Low consensus — need arbitration with DIFFERENT provider
            arbitration_used = True
            decision, arbitration_provider = await self._arbitrate(
                topic, votes, contradictions
            )

        # 5. Compute confidence
        confidence = consensus if not arbitration_used else consensus * 0.8

        total_latency = (time.time() - start) * 1000

        result = DeliberationResult(
            topic=topic,
            votes=votes,
            decision=decision,
            confidence=confidence,
            consensus_level=consensus,
            contradictions=contradictions,
            arbitration_used=arbitration_used,
            arbitration_provider=arbitration_provider,
            total_latency_ms=total_latency,
        )

        # 6. Record in meta-cognition
        if self._meta_cognition:
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

        return result

    def get_stats(self) -> dict:
        """Get deliberation room statistics."""
        return {
            "total_deliberations": self._deliberation_count,
            "consensus_threshold": self.CONSENSUS_THRESHOLD,
        }
