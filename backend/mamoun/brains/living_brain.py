"""
BABSHARQII v16.0 — Living Brain Base
الدماغ الحي — قاعدة كل الأدمغة مع LLM حقيقي

Every brain now ACTUALLY THINKS by calling an LLM with a specialized prompt.
Each brain has a different model, different system prompt, and different specialty.

This is the difference between a corpse (if/else returning empty strings)
and a living system (LLM-powered reasoning).
"""

import time
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from mamoun.core.llm_client import LLMClient, get_llm_client, LLMResponse, LLMMessage

logger = logging.getLogger("mamoun.brains.base_brain")


@dataclass
class BrainState:
    """Current state of a living brain."""
    id: str = ""
    name: str = ""
    name_ar: str = ""
    status: str = "idle"  # idle, active, thinking, error
    confidence: float = 0.5
    latency_ms: float = 0.0
    weight: float = 0.2
    model: str = "glm-5.1"
    temperature: float = 0.7
    total_interactions: int = 0
    successful_interactions: int = 0
    error_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_ar": self.name_ar,
            "status": self.status,
            "confidence": round(self.confidence, 3),
            "latency_ms": round(self.latency_ms, 1),
            "weight": self.weight,
            "model": self.model,
            "temperature": self.temperature,
            "total_interactions": self.total_interactions,
            "successful_interactions": self.successful_interactions,
            "error_count": self.error_count,
        }


@dataclass
class BrainResponse:
    """Response from a living brain — contains actual LLM reasoning."""
    brain_id: str = ""
    response: str = ""
    confidence: float = 0.5
    reasoning: str = ""       # Chain of thought
    relevance: float = 0.5    # How relevant to the query
    stance: str = "support"   # support, oppose, neutral
    model_used: str = ""
    latency_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "brain_id": self.brain_id,
            "response": self.response,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning[:500],
            "relevance": round(self.relevance, 3),
            "stance": self.stance,
            "model_used": self.model_used,
            "latency_ms": round(self.latency_ms, 1),
        }


class LivingBrain:
    """
    Base class for all living brains.

    Each brain:
    1. Receives a query
    2. Builds a specialized prompt
    3. Calls its designated LLM model
    4. Returns a structured BrainResponse with actual reasoning
    """

    def __init__(
        self,
        brain_id: str,
        name: str,
        name_ar: str,
        weight: float = 0.2,
        model: str = "glm-5.1",
        temperature: float = 0.7,
        llm_client: LLMClient = None,
    ):
        self.state = BrainState(
            id=brain_id,
            name=name,
            name_ar=name_ar,
            weight=weight,
            model=model,
            temperature=temperature,
        )
        self._system_prompt = ""
        self.llm = llm_client or get_llm_client()

    @abstractmethod
    def get_specialty(self) -> str:
        """Return this brain's specialty description."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the brain's system prompt for LLM calls."""
        pass

    async def think(self, input_text: str, context: dict = None) -> dict:
        """
        Think about the input and return a structured response.

        This is the CORE method — it ACTUALLY calls the LLM.
        """
        context = context or {}
        start_time = time.time()

        self.state.status = "thinking"

        try:
            # Build the prompt
            system_prompt = self.get_system_prompt()
            user_prompt = self._build_user_prompt(input_text, context)

            # Call the LLM
            response = await self.llm.chat(
                messages=[
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_prompt),
                ],
                model=self.state.model,
                temperature=self.state.temperature,
            )

            latency = (time.time() - start_time) * 1000

            # Parse the LLM response
            brain_response = self._parse_response(response, latency)

            # Update state
            self.state.status = "active"
            self.state.latency_ms = latency
            self._update_confidence(brain_response.confidence)
            self.state.total_interactions += 1
            self.state.successful_interactions += 1

            logger.info(
                "Brain '%s' responded (confidence: %.2f, latency: %.0fms)",
                self.state.id, brain_response.confidence, latency,
            )

            return brain_response.to_dict()

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self.state.status = "error"
            self.state.error_count += 1
            self.state.total_interactions += 1
            self._update_confidence(0.0)

            logger.error("Brain '%s' error: %s", self.state.id, e)

            return BrainResponse(
                brain_id=self.state.id,
                response="",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                model_used=self.state.model,
                latency_ms=latency,
            ).to_dict()

    def _build_user_prompt(self, input_text: str, context: dict) -> str:
        """Build the user prompt with context."""
        parts = [input_text]

        if context.get("conversation_history"):
            history = context["conversation_history"][-5:]  # Last 5 messages
            history_text = "\n".join(
                f"{'مستخدم' if m.get('role') == 'user' else 'مأمون'}: {m.get('content', '')[:200]}"
                for m in history
            )
            parts.append(f"\nسياق المحادثة:\n{history_text}")

        if context.get("brain_weights"):
            weights = context["brain_weights"]
            my_weight = weights.get(self.state.id, 0.2)
            parts.append(f"\nوزن دماغي الحالي: {my_weight:.0%}")

        return "\n".join(parts)

    def _parse_response(self, llm_response: LLMResponse, latency_ms: float) -> BrainResponse:
        """
        Parse the LLM response into a structured BrainResponse.
        Tries JSON extraction first, falls back to plain text.
        """
        # Try JSON response
        json_data = llm_response.extract_json()

        if json_data:
            return BrainResponse(
                brain_id=self.state.id,
                response=json_data.get("response", json_data.get("answer", "")),
                confidence=float(json_data.get("confidence", 0.5)),
                reasoning=json_data.get("reasoning", json_data.get("chain_of_thought", "")),
                relevance=float(json_data.get("relevance", 0.5)),
                stance=json_data.get("stance", "support"),
                model_used=llm_response.model,
                latency_ms=latency_ms,
                metadata=json_data,
            )

        # Fallback: plain text response
        text = llm_response.text or ""

        # Try to extract confidence from text
        confidence = 0.6  # Default for plain text
        if "ثقتي عالية" in text or "أنا واثق" in text:
            confidence = 0.85
        elif "لست متأكداً" in text or "قد يكون" in text:
            confidence = 0.4

        return BrainResponse(
            brain_id=self.state.id,
            response=text,
            confidence=confidence,
            relevance=0.5,
            stance="support",
            model_used=llm_response.model,
            latency_ms=latency_ms,
        )

    def _update_confidence(self, new_confidence: float):
        """Update confidence using Exponential Moving Average."""
        alpha = 0.1
        self.state.confidence = (1 - alpha) * self.state.confidence + alpha * new_confidence

    def set_system_prompt(self, prompt: str):
        self._system_prompt = prompt

    def activate(self):
        self.state.status = "active"

    def deactivate(self):
        self.state.status = "idle"

    def record_success(self, latency_ms: float = 0):
        self.state.total_interactions += 1
        self.state.successful_interactions += 1
        self.state.latency_ms = latency_ms
        self._update_confidence(1.0)

    def record_error(self, latency_ms: float = 0):
        self.state.total_interactions += 1
        self.state.error_count += 1
        self.state.latency_ms = latency_ms
        self._update_confidence(0.0)
