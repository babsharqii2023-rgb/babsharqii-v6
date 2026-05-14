"""
Multi-Provider LLM Client — TRUE diversity across GLM, Gemini, DeepSeek, Z-AI
Each provider has different model, temperature, and personality.
No more fake diversity — every brain genuinely thinks differently.

v57 — Super Mind العقل الخارق مامون
"""

import os
import time
import json
import asyncio
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class ProviderName(str, Enum):
    GLM = "glm"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    ZAI = "zai"
    CRITIC = "critic"


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    provider: str
    model: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    raw_response: Optional[dict] = None


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""
    name: str
    base_url: str = ""
    model: str = ""
    api_key_env: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    personality: str = "neutral"
    system_prompt: str = ""


# ── Default provider configs ──────────────────────────────────────────────

DEFAULT_PROVIDERS = {
    ProviderName.GLM: ProviderConfig(
        name="GLM (ZhipuAI)",
        base_url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
        model="glm-4-plus",
        api_key_env="GLM_API_KEY",
        max_tokens=4096,
        temperature=0.7,
        personality="synthesizer",
        system_prompt="أنت المُركّب — مهمتك تجميع الآراء المختلفة وإيجاد نقاط الاتفاق والخلاف.",
    ),
    ProviderName.GEMINI: ProviderConfig(
        name="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/models/",
        model="gemini-2.0-flash",
        api_key_env="GEMINI_API_KEY",
        max_tokens=4096,
        temperature=0.9,
        personality="creative",
        system_prompt="أنت المبدع — فكر خارج الصندوق، ابحث عن حلول غير تقليدية.",
    ),
    ProviderName.DEEPSEEK: ProviderConfig(
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1/chat/completions",
        model="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
        max_tokens=4096,
        temperature=0.2,
        personality="analyst",
        system_prompt="أنت المحلل — ركز على الأدلة والبيانات والمنطق الصارم.",
    ),
    ProviderName.ZAI: ProviderConfig(
        name="Z-AI",
        base_url="",
        model="default",
        api_key_env="ZAI_API_KEY",
        max_tokens=4096,
        temperature=0.5,
        personality="pragmatist",
        system_prompt="أنت العملي — ركز على التكلفة والجدوى والتطبيق.",
    ),
    ProviderName.CRITIC: ProviderConfig(
        name="Critic (DeepSeek Low-Temp)",
        base_url="https://api.deepseek.com/v1/chat/completions",
        model="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
        max_tokens=4096,
        temperature=0.0,
        personality="critic",
        system_prompt="أنت الناقد — مهمتك إيجاد الثغرات والأخطاء والمخاطر. كن صارماً.",
    ),
}


class MultiProviderLLMClient:
    """
    Unified LLM client that routes to DIFFERENT providers for TRUE diversity.

    Key principle: Each brain in BrainRouter uses a DIFFERENT provider
    with a DIFFERENT personality and temperature. This ensures genuine
    cognitive diversity — not fake diversity from the same API key.

    Usage:
        client = MultiProviderLLMClient()
        response = await client.chat(
            provider="deepseek",
            messages=[{"role": "user", "content": "Hello"}]
        )
    """

    def __init__(self, custom_providers: Optional[dict] = None):
        self.providers: dict[str, ProviderConfig] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        self._call_history: list[dict] = []
        self._provider_health: dict[str, dict] = {}

        # Load providers
        merged = {**DEFAULT_PROVIDERS}
        if custom_providers:
            merged.update(custom_providers)

        for key, config in merged.items():
            self.providers[key] = config
            self._provider_health[key] = {
                "total_calls": 0,
                "successes": 0,
                "failures": 0,
                "avg_latency_ms": 0.0,
                "last_error": None,
                "last_success_time": None,
            }

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get API key from environment for the given provider."""
        config = self.providers.get(provider)
        if not config:
            return None
        return os.environ.get(config.api_key_env)

    def available_providers(self) -> list[str]:
        """List providers that have valid API keys configured."""
        available = []
        for key, config in self.providers.items():
            api_key = os.environ.get(config.api_key_env)
            if api_key and api_key.strip():
                available.append(key)
        return available

    # ── GLM (ZhipuAI) ────────────────────────────────────────────────────
    async def _call_glm(self, messages: list[dict], config: ProviderConfig,
                        max_tokens: int = None, temperature: float = None) -> LLMResponse:
        """Call GLM (ZhipuAI) API — OpenAI-compatible endpoint."""
        api_key = self._get_api_key("glm")
        if not api_key:
            return LLMResponse(content="", provider="glm", model=config.model,
                               success=False, error="No GLM_API_KEY configured")

        client = await self._get_http_client()
        start = time.time()

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": config.model,
                "messages": messages,
                "max_tokens": max_tokens or config.max_tokens,
                "temperature": temperature if temperature is not None else config.temperature,
            }

            resp = await client.post(config.base_url, json=payload, headers=headers)
            latency = (time.time() - start) * 1000

            if resp.status_code != 200:
                return LLMResponse(
                    content="", provider="glm", model=config.model,
                    success=False, error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    latency_ms=latency
                )

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens = data.get("usage", {}).get("total_tokens", 0)

            return LLMResponse(
                content=content, provider="glm", model=config.model,
                tokens_used=tokens, latency_ms=latency, success=True,
                raw_response=data
            )

        except Exception as e:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                content="", provider="glm", model=config.model,
                success=False, error=str(e), latency_ms=latency
            )

    # ── Gemini ────────────────────────────────────────────────────────────
    async def _call_gemini(self, messages: list[dict], config: ProviderConfig,
                           max_tokens: int = None, temperature: float = None) -> LLMResponse:
        """Call Google Gemini API."""
        api_key = self._get_api_key("gemini")
        if not api_key:
            return LLMResponse(content="", provider="gemini", model=config.model,
                               success=False, error="No GEMINI_API_KEY configured")

        client = await self._get_http_client()
        start = time.time()

        try:
            # Convert OpenAI-style messages to Gemini format
            contents = []
            for msg in messages:
                role = "user" if msg["role"] in ("user", "system") else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

            url = f"{config.base_url}{config.model}:generateContent?key={api_key}"
            payload = {
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": max_tokens or config.max_tokens,
                    "temperature": temperature if temperature is not None else config.temperature,
                }
            }

            resp = await client.post(url, json=payload)
            latency = (time.time() - start) * 1000

            if resp.status_code != 200:
                return LLMResponse(
                    content="", provider="gemini", model=config.model,
                    success=False, error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    latency_ms=latency
                )

            data = resp.json()
            candidates = data.get("candidates", [{}])
            content = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                content = "".join(p.get("text", "") for p in parts)

            tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)

            return LLMResponse(
                content=content, provider="gemini", model=config.model,
                tokens_used=tokens, latency_ms=latency, success=True,
                raw_response=data
            )

        except Exception as e:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                content="", provider="gemini", model=config.model,
                success=False, error=str(e), latency_ms=latency
            )

    # ── DeepSeek ──────────────────────────────────────────────────────────
    async def _call_deepseek(self, messages: list[dict], config: ProviderConfig,
                             max_tokens: int = None, temperature: float = None) -> LLMResponse:
        """Call DeepSeek API — OpenAI-compatible endpoint."""
        # Determine which key to use based on personality
        key_env = config.api_key_env
        api_key = os.environ.get(key_env)
        if not api_key:
            return LLMResponse(content="", provider="deepseek", model=config.model,
                               success=False, error=f"No {key_env} configured")

        client = await self._get_http_client()
        start = time.time()

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": config.model,
                "messages": messages,
                "max_tokens": max_tokens or config.max_tokens,
                "temperature": temperature if temperature is not None else config.temperature,
            }

            resp = await client.post(config.base_url, json=payload, headers=headers)
            latency = (time.time() - start) * 1000

            if resp.status_code != 200:
                return LLMResponse(
                    content="", provider="deepseek", model=config.model,
                    success=False, error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    latency_ms=latency
                )

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens = data.get("usage", {}).get("total_tokens", 0)

            provider_tag = "critic" if config.personality == "critic" else "deepseek"
            return LLMResponse(
                content=content, provider=provider_tag, model=config.model,
                tokens_used=tokens, latency_ms=latency, success=True,
                raw_response=data
            )

        except Exception as e:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                content="", provider="deepseek", model=config.model,
                success=False, error=str(e), latency_ms=latency
            )

    # ── Z-AI SDK ─────────────────────────────────────────────────────────
    async def _call_zai(self, messages: list[dict], config: ProviderConfig,
                        max_tokens: int = None, temperature: float = None) -> LLMResponse:
        """Call Z-AI via the web-dev-sdk (bundled with the environment)."""
        start = time.time()

        try:
            import importlib
            zai_module = importlib.import_module("z-ai-web-dev-sdk")
            ZAI = zai_module.default if hasattr(zai_module, 'default') else zai_module.ZAI
            zai = await ZAI.create()

            completion = await zai.chat.completions.create(
                messages=messages,
                max_tokens=max_tokens or config.max_tokens,
                temperature=temperature if temperature is not None else config.temperature,
            )

            latency = (time.time() - start) * 1000
            content = completion.choices[0].message.content if completion.choices else ""
            tokens = getattr(completion, 'usage', {}).get('total_tokens', 0) if hasattr(completion, 'usage') else 0

            return LLMResponse(
                content=content, provider="zai", model="zai-default",
                tokens_used=tokens, latency_ms=latency, success=True
            )

        except ImportError:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                content="", provider="zai", model="zai-default",
                success=False, error="z-ai-web-dev-sdk not installed",
                latency_ms=latency
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return LLMResponse(
                content="", provider="zai", model="zai-default",
                success=False, error=str(e), latency_ms=latency
            )

    # ── Unified chat interface ───────────────────────────────────────────
    async def chat(
        self,
        provider: str,
        messages: list[dict],
        max_tokens: int = None,
        temperature: float = None,
        system_prompt_override: str = None,
    ) -> LLMResponse:
        """
        Send a chat completion request to the specified provider.

        Args:
            provider: One of "glm", "gemini", "deepseek", "zai", "critic"
            messages: List of message dicts with "role" and "content"
            max_tokens: Override max tokens
            temperature: Override temperature
            system_prompt_override: Override the provider's default system prompt

        Returns:
            LLMResponse with standardized fields
        """
        provider = provider.lower().strip()
        config = self.providers.get(provider)

        if not config:
            return LLMResponse(
                content="", provider=provider, model="unknown",
                success=False, error=f"Unknown provider: {provider}"
            )

        # Inject system prompt if not already present
        if system_prompt_override or config.system_prompt:
            system_msg = {"role": "system", "content": system_prompt_override or config.system_prompt}
            if messages and messages[0].get("role") == "system":
                messages[0] = system_msg
            else:
                messages = [system_msg] + messages

        # Route to correct provider
        dispatch = {
            "glm": self._call_glm,
            "gemini": self._call_gemini,
            "deepseek": self._call_deepseek,
            "zai": self._call_zai,
            "critic": self._call_deepseek,  # Critic uses DeepSeek API
        }

        handler = dispatch.get(provider)
        if not handler:
            return LLMResponse(
                content="", provider=provider, model="unknown",
                success=False, error=f"No handler for provider: {provider}"
            )

        response = await handler(messages, config, max_tokens, temperature)

        # Record in history
        self._call_history.append({
            "provider": provider,
            "success": response.success,
            "latency_ms": response.latency_ms,
            "tokens_used": response.tokens_used,
            "timestamp": time.time(),
        })

        # Update health
        health = self._provider_health.get(provider, {})
        health["total_calls"] = health.get("total_calls", 0) + 1
        if response.success:
            health["successes"] = health.get("successes", 0) + 1
            health["last_success_time"] = time.time()
        else:
            health["failures"] = health.get("failures", 0) + 1
            health["last_error"] = response.error
        self._provider_health[provider] = health

        return response

    async def chat_with_fallback(
        self,
        messages: list[dict],
        preferred_order: list[str] = None,
        max_tokens: int = None,
        temperature: float = None,
    ) -> LLMResponse:
        """
        Try providers in order, falling back on failure.
        Default order: deepseek → gemini → glm → zai
        """
        order = preferred_order or ["deepseek", "gemini", "glm", "zai"]
        available = self.available_providers()

        # Filter to available providers
        order = [p for p in order if p in available]

        if not order:
            # Try all providers
            order = list(self.providers.keys())

        last_error = None
        for provider in order:
            response = await self.chat(provider, messages, max_tokens, temperature)
            if response.success:
                return response
            last_error = response.error
            logger.warning(f"Provider {provider} failed: {response.error}, trying next...")

        return LLMResponse(
            content="", provider="fallback", model="none",
            success=False, error=f"All providers failed. Last error: {last_error}"
        )

    def get_health_report(self) -> dict:
        """Get health status for all providers."""
        report = {}
        for provider, health in self._provider_health.items():
            total = health.get("total_calls", 0)
            successes = health.get("successes", 0)
            report[provider] = {
                "total_calls": total,
                "success_rate": successes / total if total > 0 else 0.0,
                "avg_latency_ms": health.get("avg_latency_ms", 0.0),
                "last_error": health.get("last_error"),
                "is_available": provider in self.available_providers(),
            }
        return report

    async def close(self):
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
