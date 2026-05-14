"""
BABSHARQII v61 — Unified LLM Client (BACKWARD-COMPATIBLE ADAPTER)

This file now serves as a thin compatibility layer that redirects
all imports to the new shared/multi_provider_llm.py while preserving
the old LLMClient API for backward compatibility.

Migration: core/llm_client.py → core/shared/multi_provider_llm.py
Status: ADAPTER — all calls forwarded to MultiProviderLLMClient
"""

import warnings
import asyncio
import json
import re
import logging
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator

import httpx

logger = logging.getLogger("mamoun.core.llm_client")

# ── Re-export new types from shared ─────────────────────────────────────
from mamoun.core.shared.multi_provider_llm import (
    MultiProviderLLMClient,
    ProviderName,
    ProviderConfig,
    DEFAULT_PROVIDERS,
)

# ── Backward-compatible data structures ─────────────────────────────────

@dataclass
class LLMResponse:
    """Unified response from any LLM (backward-compatible)."""
    text: str = ""
    model: str = ""
    provider: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    confidence: float = 0.5
    finish_reason: str = ""
    raw: dict = field(default_factory=dict)

    def extract_json(self) -> Optional[dict]:
        """Extract JSON object from LLM response text."""
        if not self.text:
            return None
        try:
            return json.loads(self.text)
        except json.JSONDecodeError:
            pass
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'(\{[\s\S]*\})',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return None

    def extract_list(self) -> Optional[list]:
        """Extract JSON list from LLM response text."""
        if not self.text:
            return None
        try:
            return json.loads(self.text)
        except json.JSONDecodeError:
            pass
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'(\[[\s\S]*\])',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return None


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str
    content: str


@dataclass
class ModelConfig:
    """Configuration for a specific LLM model."""
    name: str
    provider: str
    api_url: str
    api_key: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


@dataclass
class LLMUsageStats:
    """Track LLM usage across all calls."""
    total_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    calls_by_model: dict = field(default_factory=dict)
    errors: int = 0
    fallbacks: int = 0


def _convert_response(new_resp) -> LLMResponse:
    """Convert new MultiProviderLLMClient.LLMResponse to old LLMResponse."""
    return LLMResponse(
        text=new_resp.content if hasattr(new_resp, 'content') else str(new_resp),
        model=getattr(new_resp, 'model', ''),
        provider=getattr(new_resp, 'provider', ''),
        tokens_used=getattr(new_resp, 'tokens_used', 0),
        latency_ms=getattr(new_resp, 'latency_ms', 0.0),
        finish_reason="" if getattr(new_resp, 'success', True) else "error",
        raw=getattr(new_resp, 'raw_response', {}) or {},
    )


class LLMClient:
    """
    Backward-compatible LLM Client that delegates to MultiProviderLLMClient.
    
    All actual LLM calls are now handled by MultiProviderLLMClient.
    This wrapper preserves the old API (chat, think, think_json, etc.)
    while using the new provider infrastructure underneath.
    """

    BRAIN_MODELS = {
        "neural":      "glm-5.1",
        "causal":      "deepseek-reasoner",
        "symbolic":    "glm-4-plus",
        "bayesian":    "gemini-2.0-flash",
        "world_model": "deepseek-chat",
    }

    FALLBACK_CHAINS = {
        "glm-5.1":          ["glm-5.1", "deepseek-chat", "glm-4-plus"],
        "deepseek-chat":    ["deepseek-chat", "glm-5.1", "glm-4-plus"],
        "deepseek-reasoner":["deepseek-reasoner", "glm-5.1", "deepseek-chat"],
        "gemini-2.0-flash": ["gemini-2.0-flash", "glm-5.1", "deepseek-chat"],
        "glm-4-plus":       ["glm-4-plus", "glm-5.1", "deepseek-chat"],
        "glm-4":            ["glm-4", "glm-4-plus", "deepseek-chat"],
        "gpt-4o":           ["gpt-4o", "glm-5.1", "deepseek-chat"],
        "gpt-4o-mini":      ["gpt-4o-mini", "gpt-4o", "glm-5.1"],
        "claude-3.5-sonnet":["claude-3.5-sonnet", "glm-5.1", "deepseek-chat"],
        "qwen-plus":        ["qwen-plus", "glm-5.1", "deepseek-chat"],
        "qwen-turbo":       ["qwen-turbo", "qwen-plus", "glm-5.1"],
        "openai-compat":    ["openai-compat", "glm-5.1", "deepseek-chat"],
    }

    # Map old model names to new provider names
    _MODEL_TO_PROVIDER = {
        "deepseek-chat": "deepseek",
        "deepseek-reasoner": "deepseek",
        "glm-5.1": "glm",
        "glm-4-plus": "glm",
        "glm-4": "glm",
        "gemini-2.0-flash": "gemini",
        "qwen-plus": "deepseek",
        "qwen-turbo": "deepseek",
        "gpt-4o": "deepseek",
        "gpt-4o-mini": "deepseek",
        "claude-3.5-sonnet": "deepseek",
    }

    def __init__(self, config_override: dict = None):
        self._multi = MultiProviderLLMClient()
        self.stats = LLMUsageStats()
        self._config_override = config_override or {}

    async def chat(
        self,
        messages: list[LLMMessage],
        model: str = "glm-5.1",
        temperature: float = None,
        max_tokens: int = None,
        json_mode: bool = False,
        stream: bool = False,
        max_retries: int = 2,
    ) -> LLMResponse:
        """Send a chat completion request with fallback chain support."""
        # Convert LLMMessage to dict format
        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
        
        # Determine provider from model name
        provider = self._MODEL_TO_PROVIDER.get(model, "glm")
        
        # Try the primary provider first
        new_resp = await self._multi.chat(
            provider=provider,
            messages=msg_dicts,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        if new_resp.success:
            self.stats.total_calls += 1
            self.stats.calls_by_model[model] = self.stats.calls_by_model.get(model, 0) + 1
            self.stats.total_tokens += new_resp.tokens_used
            return _convert_response(new_resp)
        
        # Try fallback chain
        chain = self.FALLBACK_CHAINS.get(model, [model])
        for fallback_model in chain[1:]:
            fallback_provider = self._MODEL_TO_PROVIDER.get(fallback_model, "glm")
            new_resp = await self._multi.chat(
                provider=fallback_provider,
                messages=msg_dicts,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if new_resp.success:
                self.stats.total_calls += 1
                self.stats.fallbacks += 1
                self.stats.calls_by_model[fallback_model] = self.stats.calls_by_model.get(fallback_model, 0) + 1
                self.stats.total_tokens += new_resp.tokens_used
                result = _convert_response(new_resp)
                result.model = fallback_model
                logger.info("Fallback: %s → %s", model, fallback_model)
                return result
        
        self.stats.errors += 1
        return LLMResponse(text="", model="none", provider="none", finish_reason="error")

    async def think(
        self,
        prompt: str,
        system: str = "",
        model: str = "glm-5.1",
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Quick think — single prompt, single response."""
        messages = []
        if system:
            messages.append(LLMMessage(role="system", content=system))
        messages.append(LLMMessage(role="user", content=prompt))
        return await self.chat(messages=messages, model=model, temperature=temperature, json_mode=json_mode)

    async def think_json(
        self,
        prompt: str,
        system: str = "",
        model: str = "glm-5.1",
        temperature: float = 0.7,
        **kwargs,
    ) -> Optional[dict]:
        """Think and return parsed JSON."""
        response = await self.think(prompt=prompt, system=system, model=model, temperature=temperature, json_mode=True)
        return response.extract_json()

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str = "glm-5.1",
        temperature: float = None,
        max_tokens: int = None,
    ) -> AsyncIterator[str]:
        """Stream a chat completion (yields text chunks)."""
        # Fallback: use non-streaming chat
        response = await self.chat(messages=messages, model=model, temperature=temperature, max_tokens=max_tokens)
        yield response.text

    def get_health_report(self) -> dict:
        """Get LLM client health report."""
        return self._multi.get_health_report()

    def available_providers(self) -> list[str]:
        """List available providers."""
        return self._multi.available_providers()

    def reload_keys(self):
        """Reload API keys from environment."""
        # Re-create MultiProviderLLMClient to pick up new keys
        self._multi = MultiProviderLLMClient()
        logger.info("LLM client keys reloaded")


# ── Singleton ───────────────────────────────────────────────────────────
_llm_client_instance: Optional[LLMClient] = None

def get_llm_client(config_override: dict = None) -> LLMClient:
    """Get the singleton LLM client instance."""
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = LLMClient(config_override=config_override)
    return _llm_client_instance


def reload_llm_client_keys():
    """Reload API keys from environment (backward-compatible — called by api_keys.py, security.py)."""
    global _llm_client_instance
    if _llm_client_instance is not None:
        _llm_client_instance.reload_keys()
    else:
        # Create a new instance to pick up new keys
        _llm_client_instance = LLMClient()
    logger.info("LLM client keys reloaded (via reload_llm_client_keys)")


async def close():
    """Close LLM client connections (backward-compatible)."""
    global _llm_client_instance
    if _llm_client_instance is not None:
        try:
            await _llm_client_instance.close()
        except Exception:
            pass
