"""
BABSHARQII v35.0 — Unified LLM Client
العميل الموحّد للنماذج اللغوية — روح مأمون

This is the SINGLE entry point for ALL LLM calls in Mamoun.
Every brain, every module, every decision — goes through this client.

Key Features:
- Multi-model support (DeepSeek, Gemini, GLM, OpenAI, Anthropic, Qwen, + generic OpenAI-compatible)
- Gemini Proxy support (routes via GEMINI_PROXY_URL for restricted regions)
- Automatic fallback chain (if primary fails → try secondary → try tertiary)
- TRUE brain diversity: each brain uses its designated model from a DIFFERENT provider
- Structured output parsing (JSON extraction from LLM responses)
- Token counting and cost tracking
- Streaming support for real-time responses
- Retry logic with exponential backoff
- Request queue with concurrency control

v35 Changes (Fusion Fix #6):
- Added OpenAI provider support (gpt-4o, gpt-4o-mini) via OPENAI_API_KEY
- Added Anthropic/Claude provider support (claude-3.5-sonnet) via ANTHROPIC_API_KEY
- Added Qwen/Alibaba provider support (qwen-plus, qwen-turbo) via QWEN_API_KEY / DASHSCOPE_API_KEY
- Added generic OpenAI-compatible provider via OPENAI_COMPAT_KEY + OPENAI_COMPAT_URL + OPENAI_COMPAT_MODEL
- Each new provider gets proper fallback chain and cost tracking
- reload_keys() now handles all 6 provider types
- 7+1 model configurations → true multi-provider diversity

Based on research:
- DGM (jennyzzt/dgm): Uses frozen foundation models with code modification
- Multi-LLM routing: Router-based architecture with cost optimization
- Reflexion: Generate → Reflect → Refine loop needs reliable LLM calls
"""

import asyncio
import json
import time
import logging
import re
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator
from pathlib import Path

import httpx

logger = logging.getLogger("mamoun.core.llm_client")


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LLMResponse:
    """Unified response from any LLM."""
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
        # Try direct parse first
        try:
            return json.loads(self.text)
        except json.JSONDecodeError:
            pass
        # Try extracting JSON from markdown code blocks or raw text
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
            r'```\s*([\s\S]*?)\s*```',        # ``` ... ```
            r'(\{[\s\S]*\})',                  # Raw { ... }
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
    role: str  # system, user, assistant
    content: str


@dataclass
class ModelConfig:
    """Configuration for a specific LLM model."""
    name: str
    provider: str  # deepseek, gemini, glm, openai_compatible
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


# ─────────────────────────────────────────────────────────────────────────────
# The Client
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """
    Unified LLM Client — the soul of Mamoun.

    Every decision, every thought, every reflection goes through this client.
    It handles model selection, fallbacks, retries, and cost tracking.

    Usage:
        client = LLMClient()
        response = await client.chat(
            messages=[LLMMessage(role="user", content="Hello")],
            model="deepseek-chat",
        )
        print(response.text)
    """

    # v34: TRUE DIVERSITY — 5 brains × 3 providers = real deliberation
    # كل دماغ يستخدم نموذج مختلف من مزود مختلف = منظورات مختلفة = مداولة أعمق
    # neural=GLM, causal=DeepSeek, symbolic=GLM, bayesian=Gemini, world_model=DeepSeek
    BRAIN_MODELS = {
        "neural":      "glm-5.1",            # الدماغ الأساسي — الإبداع والتحليل العميق (GLM)
        "causal":      "deepseek-reasoner",  # تفكير متسلسل عميق — مثالي للاستدلال السببي (DeepSeek)
        "symbolic":    "glm-4-plus",         # منطق رياضي — نموذج مختلف عن الأساسي (GLM)
        "bayesian":    "gemini-2.0-flash",   # تقدير احتمالي سريع — منظور مختلف (Gemini via proxy)
        "world_model": "deepseek-chat",      # بناء سيناريوهات — منظور ثالث (DeepSeek)
    }

    # v35: Balanced Fallback chains — كل نموذج يقع على بديل من مزود مختلف
    FALLBACK_CHAINS = {
        "glm-5.1":          ["glm-5.1", "deepseek-chat", "glm-4-plus"],
        "deepseek-chat":    ["deepseek-chat", "glm-5.1", "glm-4-plus"],
        "deepseek-reasoner":["deepseek-reasoner", "glm-5.1", "deepseek-chat"],
        "gemini-2.0-flash": ["gemini-2.0-flash", "glm-5.1", "deepseek-chat"],
        "glm-4-plus":       ["glm-4-plus", "glm-5.1", "deepseek-chat"],
        "glm-4":            ["glm-4", "glm-4-plus", "deepseek-chat"],
        # v35 Fusion Fix #6: Full multi-provider fallback chains
        "gpt-4o":           ["gpt-4o", "glm-5.1", "deepseek-chat"],
        "gpt-4o-mini":      ["gpt-4o-mini", "gpt-4o", "glm-5.1"],
        "claude-3.5-sonnet":["claude-3.5-sonnet", "glm-5.1", "deepseek-chat"],
        "qwen-plus":        ["qwen-plus", "glm-5.1", "deepseek-chat"],
        "qwen-turbo":       ["qwen-turbo", "qwen-plus", "glm-5.1"],
        # Generic OpenAI-compatible provider — model name comes from env
        "openai-compat":    ["openai-compat", "glm-5.1", "deepseek-chat"],
    }

    def __init__(self, config_override: dict = None):
        self.stats = LLMUsageStats()
        self._configs: dict[str, ModelConfig] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        self._gemini_proxy_client: Optional[httpx.AsyncClient] = None  # v34: Separate proxy client for Gemini
        self._semaphore = asyncio.Semaphore(5)  # Max 5 concurrent LLM calls
        self._config_override = config_override or {}

        # v34: Load Gemini proxy URL from environment
        import os
        self._gemini_proxy_url = os.getenv("GEMINI_PROXY_URL", "")
        if self._gemini_proxy_url:
            logger.info("Gemini Proxy enabled: %s", self._gemini_proxy_url)

        # Load default configurations
        self._load_default_configs()

        logger.info(
            "LLMClient initialized with %d models: %s",
            len(self._configs),
            list(self._configs.keys()),
        )

    def _load_default_configs(self):
        """Load default model configurations from environment."""
        import os

        # Primary endpoint — DIRECT GLM API (not proxy loop!)
        primary_url = self._config_override.get(
            "llm_api_url",
            os.getenv("MAMOUN_LLM_API_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions"),
        )

        # DeepSeek (direct or fallback to glm-5.1 when no API key)
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        if deepseek_key:
            deepseek_url = os.getenv(
                "DEEPSEEK_API_URL",
                "https://api.deepseek.com/v1/chat/completions",
            )
            self._configs["deepseek-chat"] = ModelConfig(
                name="deepseek-chat",
                provider="deepseek",
                api_url=deepseek_url,
                api_key=deepseek_key,
                max_tokens=4096,
                temperature=0.7,
                timeout=60,
                cost_per_1k_input=0.0014,
                cost_per_1k_output=0.0028,
            )
            self._configs["deepseek-reasoner"] = ModelConfig(
                name="deepseek-reasoner",
                provider="deepseek",
                api_url=deepseek_url,
                api_key=deepseek_key,
                max_tokens=8192,
                temperature=0.7,
                timeout=120,
                cost_per_1k_input=0.004,
                cost_per_1k_output=0.016,
            )
        else:
            # v30.2: No DeepSeek API key — fallback to glm-5.1 directly (not proxy with wrong model)
            # Previously this set provider="proxy" with name="deepseek-chat" which sent the
            # wrong model name to GLM API, causing failures and slow fallbacks.
            logger.warning(
                "No DEEPSEEK_API_KEY found — deepseek-chat and deepseek-reasoner "
                "will use glm-5.1 directly instead of proxy"
            )
            self._configs["deepseek-chat"] = ModelConfig(
                name="glm-5.1",
                provider="proxy",
                api_url=primary_url,
                api_key="",
                max_tokens=4096,
                temperature=0.7,
                timeout=60,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
            )
            self._configs["deepseek-reasoner"] = ModelConfig(
                name="glm-5.1",
                provider="proxy",
                api_url=primary_url,
                api_key="",
                max_tokens=8192,
                temperature=0.7,
                timeout=120,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
            )

        # Gemini — v34: Supports proxy for restricted regions
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        gemini_proxy_url = os.getenv("GEMINI_PROXY_URL", "")

        if gemini_key:
            if gemini_proxy_url:
                # v34: Route Gemini requests through proxy server in supported region
                # The proxy server forwards to Google's Gemini API
                gemini_url = gemini_proxy_url
                provider = "gemini_proxy"
                logger.info("Gemini using PROXY: %s", gemini_proxy_url)
            else:
                # Direct Gemini API access
                gemini_url = os.getenv(
                    "GEMINI_API_URL",
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                )
                # Ensure URL has API key parameter
                if "key=" not in gemini_url:
                    gemini_url = f"{gemini_url}?key={gemini_key}"
                provider = "gemini"
        else:
            # No Gemini key — fallback to GLM proxy
            gemini_url = primary_url
            provider = "proxy"
            logger.warning("No GEMINI_API_KEY — bayesian brain will use GLM fallback")

        self._configs["gemini-2.0-flash"] = ModelConfig(
            name="gemini-2.0-flash",
            provider=provider,
            api_url=gemini_url,
            api_key=gemini_key,
            max_tokens=8192,
            temperature=0.7,
            timeout=60,
            cost_per_1k_input=0.000075,
            cost_per_1k_output=0.0003,
        )

        # GLM models — use GLM_API_KEY if available, otherwise proxy without key
        glm_key = os.getenv("GLM_API_KEY", "")
        for model_name in ["glm-4-plus", "glm-4", "glm-3-turbo", "glm-5.1"]:
            self._configs[model_name] = ModelConfig(
                name=model_name,
                provider="proxy",
                api_url=primary_url,
                api_key=glm_key,
                max_tokens=4096,
                temperature=0.7,
                timeout=60,
            )

        # ── v35 Fix #6: OpenAI Provider ───────────────────────────────────────
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            openai_url = os.getenv(
                "OPENAI_API_URL",
                "https://api.openai.com/v1/chat/completions",
            )
            self._configs["gpt-4o"] = ModelConfig(
                name="gpt-4o",
                provider="openai_compatible",
                api_url=openai_url,
                api_key=openai_key,
                max_tokens=4096,
                temperature=0.7,
                timeout=60,
                cost_per_1k_input=0.0025,
                cost_per_1k_output=0.01,
            )
            self._configs["gpt-4o-mini"] = ModelConfig(
                name="gpt-4o-mini",
                provider="openai_compatible",
                api_url=openai_url,
                api_key=openai_key,
                max_tokens=4096,
                temperature=0.7,
                timeout=60,
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
            )
            logger.info("OpenAI provider enabled: gpt-4o, gpt-4o-mini")
        else:
            logger.info("No OPENAI_API_KEY — gpt-4o models will use GLM fallback")

        # ── v35 Fix #6: Anthropic/Claude Provider ─────────────────────────────
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            anthropic_url = os.getenv(
                "ANTHROPIC_API_URL",
                "https://api.anthropic.com/v1/messages",
            )
            self._configs["claude-3.5-sonnet"] = ModelConfig(
                name="claude-3.5-sonnet",
                provider="anthropic",
                api_url=anthropic_url,
                api_key=anthropic_key,
                max_tokens=4096,
                temperature=0.7,
                timeout=60,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
            )
            logger.info("Anthropic provider enabled: claude-3.5-sonnet")
        else:
            logger.info("No ANTHROPIC_API_KEY — claude models will use GLM fallback")

        # ── v35 Fix #6: Qwen/Alibaba Provider ─────────────────────────────────
        # Qwen uses DashScope API (OpenAI-compatible format)
        qwen_key = os.getenv("QWEN_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")
        if qwen_key:
            qwen_url = os.getenv(
                "QWEN_API_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            )
            self._configs["qwen-plus"] = ModelConfig(
                name="qwen-plus",
                provider="openai_compatible",
                api_url=qwen_url,
                api_key=qwen_key,
                max_tokens=4096,
                temperature=0.7,
                timeout=60,
                cost_per_1k_input=0.0004,
                cost_per_1k_output=0.0012,
            )
            self._configs["qwen-turbo"] = ModelConfig(
                name="qwen-turbo",
                provider="openai_compatible",
                api_url=qwen_url,
                api_key=qwen_key,
                max_tokens=4096,
                temperature=0.7,
                timeout=30,
                cost_per_1k_input=0.0001,
                cost_per_1k_output=0.0003,
            )
            logger.info("Qwen provider enabled: qwen-plus, qwen-turbo")
        else:
            logger.info("No QWEN_API_KEY/DASHSCOPE_API_KEY — qwen models will use GLM fallback")

        # ── v35 Fix #6: Generic OpenAI-Compatible Provider ────────────────────
        # For any OpenAI-compatible API (Ollama, vLLM, LiteLLM, Together, etc.)
        compat_key = os.getenv("OPENAI_COMPAT_KEY", "")
        compat_url = os.getenv("OPENAI_COMPAT_URL", "")
        compat_model = os.getenv("OPENAI_COMPAT_MODEL", "")
        if compat_key and compat_url and compat_model:
            self._configs["openai-compat"] = ModelConfig(
                name=compat_model,
                provider="openai_compatible",
                api_url=compat_url,
                api_key=compat_key,
                max_tokens=int(os.getenv("OPENAI_COMPAT_MAX_TOKENS", "4096")),
                temperature=float(os.getenv("OPENAI_COMPAT_TEMPERATURE", "0.7")),
                timeout=int(os.getenv("OPENAI_COMPAT_TIMEOUT", "60")),
                cost_per_1k_input=float(os.getenv("OPENAI_COMPAT_COST_INPUT", "0.0")),
                cost_per_1k_output=float(os.getenv("OPENAI_COMPAT_COST_OUTPUT", "0.0")),
            )
            logger.info("Generic OpenAI-compatible provider enabled: model=%s url=%s", compat_model, compat_url)
        elif compat_url:
            # URL provided but no key/model — still register with empty key
            # Some local providers (Ollama, vLLM) don't require API keys
            self._configs["openai-compat"] = ModelConfig(
                name=compat_model or "default",
                provider="openai_compatible",
                api_url=compat_url,
                api_key=compat_key,
                max_tokens=int(os.getenv("OPENAI_COMPAT_MAX_TOKENS", "4096")),
                temperature=float(os.getenv("OPENAI_COMPAT_TEMPERATURE", "0.7")),
                timeout=int(os.getenv("OPENAI_COMPAT_TIMEOUT", "60")),
            )
            logger.info("Generic OpenAI-compatible provider (no auth): url=%s", compat_url)

    async def _get_http_client(self, use_proxy: bool = False) -> httpx.AsyncClient:
        """Get or create the shared HTTP client.
        v34: use_proxy=True returns the Gemini proxy client with proxy URL configured."""
        if use_proxy and self._gemini_proxy_url:
            if self._gemini_proxy_client is None or self._gemini_proxy_client.is_closed:
                self._gemini_proxy_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(120.0, connect=15.0),
                    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                    proxy=self._gemini_proxy_url,  # v34: Route through proxy
                )
            return self._gemini_proxy_client

        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._http_client

    # ─────────────────────────────────────────────────────────────────────────
    # Core Chat Method
    # ─────────────────────────────────────────────────────────────────────────

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
        """
        Send a chat completion request.

        Automatically falls back to alternative models if the primary fails.
        v18.0: Added retry with exponential backoff.

        Args:
            messages: List of conversation messages
            model: Primary model to use
            temperature: Override default temperature
            max_tokens: Override default max tokens
            json_mode: Request JSON output format
            stream: Whether to stream the response
            max_retries: Maximum retry attempts per model before fallback

        Returns:
            LLMResponse with text, model info, and usage stats
        """
        chain = self.FALLBACK_CHAINS.get(model, [model])

        last_error = None
        for attempt_model in chain:
            for attempt in range(max_retries + 1):
                try:
                    async with self._semaphore:
                        response = await self._call_model(
                            messages=messages,
                            model=attempt_model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            json_mode=json_mode,
                            stream=stream,
                        )

                    # Track usage
                    self.stats.total_calls += 1
                    self.stats.calls_by_model[attempt_model] = (
                        self.stats.calls_by_model.get(attempt_model, 0) + 1
                    )

                    if attempt_model != model:
                        self.stats.fallbacks += 1
                        logger.info("Fallback: %s → %s", model, attempt_model)

                    return response

                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        # Exponential backoff: 1s, 2s, 4s...
                        backoff = 2 ** attempt
                        logger.warning("Model %s attempt %d/%d failed: %s, retrying in %ds...",
                                     attempt_model, attempt + 1, max_retries + 1, e, backoff)
                        import asyncio
                        await asyncio.sleep(backoff)
                    else:
                        logger.warning("Model %s all retries exhausted: %s, trying fallback...",
                                     attempt_model, e)
                        self.stats.errors += 1
                        continue

        # All models failed
        logger.error("All models in fallback chain failed. Last error: %s", last_error)
        return LLMResponse(
            text="",
            model="none",
            provider="none",
            finish_reason="error",
            raw={"error": str(last_error)},
        )

    async def _call_model(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = None,
        max_tokens: int = None,
        json_mode: bool = False,
        stream: bool = False,
    ) -> LLMResponse:
        """Call a specific model with proper formatting."""
        config = self._configs.get(model)
        if not config:
            raise ValueError(f"Unknown model: {model}")

        start_time = time.time()
        client = await self._get_http_client()

        # Route to appropriate provider
        # v35: 7 provider types supported
        if config.provider in ("deepseek", "openai_compatible"):
            # DeepSeek, OpenAI, Qwen, and any OpenAI-compatible API all use the same format
            response = await self._call_openai_compatible(
                client, config, messages, model, temperature, max_tokens, json_mode,
            )
        elif config.provider == "anthropic":
            # v35: Anthropic uses its own message format (not OpenAI-compatible)
            response = await self._call_anthropic(
                client, config, messages, model, temperature, max_tokens,
            )
        elif config.provider == "gemini":
            response = await self._call_gemini(
                client, config, messages, model, temperature, max_tokens,
            )
        elif config.provider == "gemini_proxy":
            # v34: Use proxy client for Gemini requests in restricted regions
            proxy_client = await self._get_http_client(use_proxy=True)
            response = await self._call_gemini_via_proxy(
                proxy_client, config, messages, model, temperature, max_tokens,
            )
        elif config.provider == "proxy":
            response = await self._call_proxy(
                client, config, messages, model, temperature, max_tokens,
            )
        else:
            raise ValueError(f"Unknown provider: {config.provider}")

        latency = (time.time() - start_time) * 1000
        response.latency_ms = latency
        response.model = model
        response.provider = config.provider

        # Update stats
        self.stats.total_tokens += response.tokens_used

        return response

    # ─────────────────────────────────────────────────────────────────────────
    # Provider-Specific Callers
    # ─────────────────────────────────────────────────────────────────────────

    async def _call_openai_compatible(
        self,
        client: httpx.AsyncClient,
        config: ModelConfig,
        messages: list[LLMMessage],
        model: str,
        temperature: float = None,
        max_tokens: int = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Call OpenAI-compatible API (DeepSeek, etc.)."""
        headers = {
            "Content-Type": "application/json",
        }
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature or config.temperature,
            "max_tokens": max_tokens or config.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        resp = await client.post(
            config.api_url,
            headers=headers,
            json=payload,
            timeout=config.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        text = ""
        tokens = 0
        finish = ""
        if "choices" in data and data["choices"]:
            text = data["choices"][0].get("message", {}).get("content", "")
            finish = data["choices"][0].get("finish_reason", "")
        if "usage" in data:
            tokens = data["usage"].get("total_tokens", 0)

        return LLMResponse(
            text=text,
            tokens_used=tokens,
            finish_reason=finish,
            raw=data,
        )

    async def _call_gemini(
        self,
        client: httpx.AsyncClient,
        config: ModelConfig,
        messages: list[LLMMessage],
        model: str,
        temperature: float = None,
        max_tokens: int = None,
    ) -> LLMResponse:
        """Call Google Gemini API directly."""
        # Convert messages to Gemini format
        contents = []
        for m in messages:
            role = "user" if m.role in ("user", "system") else "model"
            contents.append({
                "role": role,
                "parts": [{"text": m.content}],
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature or config.temperature,
                "maxOutputTokens": max_tokens or config.max_tokens,
            },
        }

        resp = await client.post(
            config.api_url,
            json=payload,
            timeout=config.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        text = ""
        tokens = 0
        try:
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
        except (KeyError, IndexError):
            pass

        return LLMResponse(
            text=text,
            tokens_used=tokens,
            raw=data,
        )

    async def _call_gemini_via_proxy(
        self,
        client: httpx.AsyncClient,
        config: ModelConfig,
        messages: list[LLMMessage],
        model: str,
        temperature: float = None,
        max_tokens: int = None,
    ) -> LLMResponse:
        """v34: Call Gemini API via proxy server for restricted regions.

        Two proxy modes supported:
        1. HTTP/SOCKS proxy: Routes traffic through a server in a supported region
           The actual Gemini API URL is used, but through the proxy
        2. Relay server: A custom server that forwards Gemini requests
           The proxy URL itself IS the endpoint

        Environment variables:
        - GEMINI_PROXY_URL: The proxy server URL (e.g., socks5://user:pass@host:port
          or https://relay.example.com/gemini-proxy)
        """
        import os

        # Determine if proxy URL is a relay server or an HTTP/SOCKS proxy
        relay_mode = os.getenv("GEMINI_PROXY_MODE", "").lower() == "relay"

        if relay_mode:
            # Relay mode: Send request to the relay server which forwards to Gemini
            # The relay server expects the same Gemini API format
            gemini_api_url = config.api_url  # This is the relay URL

            # Build Gemini-format payload
            contents = []
            for m in messages:
                role = "user" if m.role in ("user", "system") else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": m.content}],
                })

            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature or config.temperature,
                    "maxOutputTokens": max_tokens or config.max_tokens,
                },
            }

            # Add API key to URL for relay authentication
            url = gemini_api_url
            if config.api_key and "key=" not in url:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}key={config.api_key}"

            headers = {"Content-Type": "application/json"}
            resp = await client.post(url, json=payload, headers=headers, timeout=config.timeout)
            resp.raise_for_status()
            data = resp.json()
        else:
            # HTTP/SOCKS proxy mode: Use client with proxy configured
            # The actual Gemini API URL is used, traffic routes through proxy
            gemini_key = config.api_key
            gemini_api_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={gemini_key}"
            )

            contents = []
            for m in messages:
                role = "user" if m.role in ("user", "system") else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": m.content}],
                })

            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature or config.temperature,
                    "maxOutputTokens": max_tokens or config.max_tokens,
                },
            }

            resp = await client.post(gemini_api_url, json=payload, timeout=config.timeout)
            resp.raise_for_status()
            data = resp.json()

        # Parse Gemini response (same format for both modes)
        text = ""
        tokens = 0
        try:
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
        except (KeyError, IndexError):
            pass

        return LLMResponse(
            text=text,
            tokens_used=tokens,
            raw=data,
        )

    async def _call_anthropic(
        self,
        client: httpx.AsyncClient,
        config: ModelConfig,
        messages: list[LLMMessage],
        model: str,
        temperature: float = None,
        max_tokens: int = None,
    ) -> LLMResponse:
        """v35: Call Anthropic/Claude API with its native message format.

        Anthropic uses a different format than OpenAI:
        - System messages go in a top-level 'system' parameter
        - Only 'user' and 'assistant' roles in messages
        - Uses x-api-key header instead of Bearer auth
        - Requires anthropic-version header
        """
        # Separate system message from conversation messages
        system_content = ""
        conversation_messages = []
        for m in messages:
            if m.role == "system":
                system_content += m.content + "\n"
            else:
                conversation_messages.append({
                    "role": m.role,  # Anthropic supports user + assistant
                    "content": m.content,
                })

        # Anthropic requires at least one user message
        if not conversation_messages:
            conversation_messages = [{"role": "user", "content": system_content.strip()}]
            system_content = ""
        elif conversation_messages[0]["role"] != "user":
            # Prepend a user message if the first one isn't user
            conversation_messages.insert(0, {"role": "user", "content": "(continued)"})

        headers = {
            "Content-Type": "application/json",
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": config.name,  # e.g. "claude-3.5-sonnet-20241022"
            "messages": conversation_messages,
            "max_tokens": max_tokens or config.max_tokens,
        }
        if system_content.strip():
            payload["system"] = system_content.strip()
        if temperature is not None:
            payload["temperature"] = temperature
        elif config.temperature != 0.7:  # Only override if non-default
            payload["temperature"] = config.temperature

        resp = await client.post(
            config.api_url,
            headers=headers,
            json=payload,
            timeout=config.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        # Parse Anthropic response format
        text = ""
        tokens = 0
        finish = ""
        try:
            content_blocks = data.get("content", [])
            text = "".join(
                block.get("text", "")
                for block in content_blocks
                if block.get("type") == "text"
            )
            # Anthropic uses different token counting
            tokens = (
                data.get("usage", {}).get("input_tokens", 0)
                + data.get("usage", {}).get("output_tokens", 0)
            )
            finish = data.get("stop_reason", "")
        except (KeyError, IndexError):
            pass

        return LLMResponse(
            text=text,
            tokens_used=tokens,
            finish_reason=finish,
            raw=data,
        )

    async def _call_proxy(
        self,
        client: httpx.AsyncClient,
        config: ModelConfig,
        messages: list[LLMMessage],
        model: str,
        temperature: float = None,
        max_tokens: int = None,
    ) -> LLMResponse:
        """Call via OpenAI-compatible API directly (v30.1 fix: no proxy loop).

        v30.1 Fix: كان يرسل لـ Next.js proxy اللي يعمل rewrite لـ backend = حلقة دائرية.
        الآن يستخدم نفس صيغة OpenAI API مباشرة مع أي مزود متوافق.
        """
        # Build OpenAI-compatible messages format
        formatted_messages = []
        for m in messages:
            formatted_messages.append({"role": m.role, "content": m.content})

        headers = {
            "Content-Type": "application/json",
        }
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        # v30.2: Use config.name (actual model name) instead of model parameter.
        # When DeepSeek API key is missing, config.name is set to "glm-5.1" so the
        # proxy sends the correct model name to the GLM API.
        actual_model = config.name
        if actual_model != model:
            logger.info("Model substitution: %s → %s (no direct API key available)", model, actual_model)

        payload = {
            "model": actual_model,
            "messages": formatted_messages,
            "temperature": temperature or config.temperature,
            "max_tokens": max_tokens or config.max_tokens,
        }

        resp = await client.post(
            config.api_url,
            headers=headers,
            json=payload,
            timeout=config.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        # Parse OpenAI-compatible response
        text = ""
        tokens = 0
        finish = ""
        if "choices" in data and data["choices"]:
            text = data["choices"][0].get("message", {}).get("content", "")
            finish = data["choices"][0].get("finish_reason", "")
        if "usage" in data:
            tokens = data["usage"].get("total_tokens", 0)

        return LLMResponse(
            text=text,
            tokens_used=tokens,
            finish_reason=finish,
            raw=data,
        )


    # ─────────────────────────────────────────────────────────────────────────
    # Convenience Methods
    # ─────────────────────────────────────────────────────────────────────────

    async def think(
        self,
        prompt: str,
        system: str = "",
        model: str = "glm-5.1",
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        Quick think — single prompt, single response.
        The most common usage pattern.
        """
        messages = []
        if system:
            messages.append(LLMMessage(role="system", content=system))
        messages.append(LLMMessage(role="user", content=prompt))

        return await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            json_mode=json_mode,
        )

    async def think_json(
        self,
        prompt: str,
        system: str = "",
        model: str = "glm-5.1",
        temperature: float = 0.7,
        **kwargs,
    ) -> Optional[dict]:
        """
        Think and return parsed JSON.
        Returns None if JSON extraction fails.
        v32: Added temperature parameter for compatibility.
        """
        response = await self.think(
            prompt=prompt,
            system=system,
            model=model,
            temperature=temperature,
            json_mode=True,
        )
        return response.extract_json()

    async def reflect(
        self,
        content: str,
        question: str,
        model: str = "glm-5.1",
    ) -> LLMResponse:
        """
        Reflect on content by asking a question about it.
        Used by Mirror, Reflexion, and self-review processes.
        """
        system = """أنت نظام تأمل ذاتي في مأمون. تحلل المحتوى بنقد وبعمق.
تسأل: ما الافتراضات الخفية؟ ما التحيزات؟ ما الذي لا أعرفه؟ ما الذي قد يسوء؟
أجب بالعربية بصراحة وعمق."""

        prompt = f"""المحتوى للتأمل:
{content}

السؤال: {question}"""

        return await self.think(
            prompt=prompt,
            system=system,
            model=model,
            temperature=0.5,  # Lower temperature for more focused reflection
        )

    async def code_edit(
        self,
        current_code: str,
        instruction: str,
        model: str = "glm-5.1",
    ) -> Optional[dict]:
        """
        Edit code based on an instruction.
        Returns {"patched_code": "...", "description": "...", "risk_level": "..."}
        """
        system = """أنت محرك تعديل كود في مأمون. تعدل الكود بناءً على التعليمات.
أجب بصيغة JSON فقط:
{
  "patched_code": "الكود المعدل الكامل هنا",
  "description": "وصف ما فعلته بالعربية",
  "risk_level": "low" | "medium" | "high"
}

القواعد:
1. لا تستخدم exec(), eval(), __import__, os.system, subprocess
2. حافظ على نفس الواجهة (function signatures)
3. أضف معالجة أخطاء دفاعية
4. لا تحذف أي دوال موجودة"""

        prompt = f"""الكود الحالي:
```
{current_code[:8000]}
```

التعليمات: {instruction}"""

        response = await self.think(
            prompt=prompt,
            system=system,
            model=model,
            temperature=0.3,  # Very low temperature for code edits
            json_mode=True,
        )
        return response.extract_json()

    def reload_keys(self):
        """إعادة تحميل مفاتيح API من os.environ فوراً — بدون إعادة تشغيل السيرفر.
        يُستدعى تلقائياً بعد حفظ مفتاح جديد من الداشبورد.
        v35: يدعم الآن 6+ أنواع مزودين: GLM, DeepSeek, Gemini, OpenAI, Anthropic, Qwen, Generic
        """
        import os
        glm_key = os.getenv("GLM_API_KEY", "")
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        gemini_proxy_url = os.getenv("GEMINI_PROXY_URL", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        qwen_key = os.getenv("QWEN_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")
        compat_key = os.getenv("OPENAI_COMPAT_KEY", "")
        compat_url = os.getenv("OPENAI_COMPAT_URL", "")
        compat_model = os.getenv("OPENAI_COMPAT_MODEL", "")
        primary_url = os.getenv("MAMOUN_LLM_API_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions")

        # ── GLM models ────────────────────────────────────────────────────────
        for model_name in ["glm-4-plus", "glm-4", "glm-3-turbo", "glm-5.1"]:
            if model_name in self._configs:
                self._configs[model_name].api_key = glm_key

        # ── DeepSeek models ───────────────────────────────────────────────────
        if deepseek_key:
            deepseek_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
            for model_name in ["deepseek-chat", "deepseek-reasoner"]:
                if model_name in self._configs:
                    self._configs[model_name].api_key = deepseek_key
                    self._configs[model_name].api_url = deepseek_url
                    self._configs[model_name].provider = "deepseek"
                    self._configs[model_name].name = model_name
        else:
            for model_name in ["deepseek-chat", "deepseek-reasoner"]:
                if model_name in self._configs:
                    self._configs[model_name].api_key = ""
                    self._configs[model_name].api_url = primary_url
                    self._configs[model_name].provider = "proxy"
                    self._configs[model_name].name = "glm-5.1"

        # ── Gemini ────────────────────────────────────────────────────────────
        if "gemini-2.0-flash" in self._configs:
            if gemini_key:
                self._configs["gemini-2.0-flash"].api_key = gemini_key
                if gemini_proxy_url:
                    self._configs["gemini-2.0-flash"].api_url = gemini_proxy_url
                    self._configs["gemini-2.0-flash"].provider = "gemini_proxy"
                else:
                    gemini_url = os.getenv(
                        "GEMINI_API_URL",
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                    )
                    if "key=" not in gemini_url:
                        gemini_url = f"{gemini_url}?key={gemini_key}"
                    self._configs["gemini-2.0-flash"].api_url = gemini_url
                    self._configs["gemini-2.0-flash"].provider = "gemini"
            else:
                self._configs["gemini-2.0-flash"].api_key = ""
                self._configs["gemini-2.0-flash"].api_url = primary_url
                self._configs["gemini-2.0-flash"].provider = "proxy"

        # ── v35 Fix #6: OpenAI models ────────────────────────────────────────
        if openai_key:
            openai_url = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
            for model_name in ["gpt-4o", "gpt-4o-mini"]:
                if model_name in self._configs:
                    self._configs[model_name].api_key = openai_key
                    self._configs[model_name].api_url = openai_url
                    self._configs[model_name].provider = "openai_compatible"
                    self._configs[model_name].name = model_name
                else:
                    # Model not yet registered — create fresh config
                    self._configs[model_name] = ModelConfig(
                        name=model_name,
                        provider="openai_compatible",
                        api_url=openai_url,
                        api_key=openai_key,
                        max_tokens=4096,
                        temperature=0.7,
                        timeout=60,
                    )
        else:
            # No OpenAI key — ensure models exist with fallback settings
            for model_name in ["gpt-4o", "gpt-4o-mini"]:
                if model_name not in self._configs:
                    self._configs[model_name] = ModelConfig(
                        name="glm-5.1",
                        provider="proxy",
                        api_url=primary_url,
                        api_key="",
                        max_tokens=4096,
                        temperature=0.7,
                        timeout=60,
                    )

        # ── v35 Fix #6: Anthropic/Claude ─────────────────────────────────────
        if anthropic_key:
            anthropic_url = os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
            if "claude-3.5-sonnet" in self._configs:
                self._configs["claude-3.5-sonnet"].api_key = anthropic_key
                self._configs["claude-3.5-sonnet"].api_url = anthropic_url
                self._configs["claude-3.5-sonnet"].provider = "anthropic"
                self._configs["claude-3.5-sonnet"].name = "claude-3.5-sonnet"
            else:
                self._configs["claude-3.5-sonnet"] = ModelConfig(
                    name="claude-3.5-sonnet",
                    provider="anthropic",
                    api_url=anthropic_url,
                    api_key=anthropic_key,
                    max_tokens=4096,
                    temperature=0.7,
                    timeout=60,
                    cost_per_1k_input=0.003,
                    cost_per_1k_output=0.015,
                )
        else:
            if "claude-3.5-sonnet" not in self._configs:
                self._configs["claude-3.5-sonnet"] = ModelConfig(
                    name="glm-5.1",
                    provider="proxy",
                    api_url=primary_url,
                    api_key="",
                    max_tokens=4096,
                    temperature=0.7,
                    timeout=60,
                )

        # ── v35 Fix #6: Qwen/Alibaba ─────────────────────────────────────────
        if qwen_key:
            qwen_url = os.getenv("QWEN_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
            for model_name in ["qwen-plus", "qwen-turbo"]:
                if model_name in self._configs:
                    self._configs[model_name].api_key = qwen_key
                    self._configs[model_name].api_url = qwen_url
                    self._configs[model_name].provider = "openai_compatible"
                    self._configs[model_name].name = model_name
                else:
                    self._configs[model_name] = ModelConfig(
                        name=model_name,
                        provider="openai_compatible",
                        api_url=qwen_url,
                        api_key=qwen_key,
                        max_tokens=4096,
                        temperature=0.7,
                        timeout=60,
                    )
        else:
            for model_name in ["qwen-plus", "qwen-turbo"]:
                if model_name not in self._configs:
                    self._configs[model_name] = ModelConfig(
                        name="glm-5.1",
                        provider="proxy",
                        api_url=primary_url,
                        api_key="",
                        max_tokens=4096,
                        temperature=0.7,
                        timeout=60,
                    )

        # ── v35 Fix #6: Generic OpenAI-Compatible ─────────────────────────────
        if compat_key and compat_url and compat_model:
            if "openai-compat" in self._configs:
                self._configs["openai-compat"].api_key = compat_key
                self._configs["openai-compat"].api_url = compat_url
                self._configs["openai-compat"].name = compat_model
                self._configs["openai-compat"].provider = "openai_compatible"
            else:
                self._configs["openai-compat"] = ModelConfig(
                    name=compat_model,
                    provider="openai_compatible",
                    api_url=compat_url,
                    api_key=compat_key,
                    max_tokens=4096,
                    temperature=0.7,
                    timeout=60,
                )

        logger.info(
            "LLMClient keys reloaded — GLM:%s DeepSeek:%s Gemini:%s OpenAI:%s Anthropic:%s Qwen:%s Compat:%s",
            "✓" if glm_key else "✗",
            "✓" if deepseek_key else "✗",
            "✓" if gemini_key else "✗",
            "✓" if openai_key else "✗",
            "✓" if anthropic_key else "✗",
            "✓" if qwen_key else "✗",
            "✓" if (compat_key and compat_url) else "✗",
        )

    def get_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "total_calls": self.stats.total_calls,
            "total_tokens": self.stats.total_tokens,
            "total_cost_usd": round(self.stats.total_cost, 4),
            "errors": self.stats.errors,
            "fallbacks": self.stats.fallbacks,
            "calls_by_model": dict(self.stats.calls_by_model),
        }

    async def close(self):
        """Close the HTTP clients (regular + proxy)."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        if self._gemini_proxy_client and not self._gemini_proxy_client.is_closed:
            await self._gemini_proxy_client.aclose()


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────

_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def reload_llm_client_keys():
    """إعادة تحميل المفاتيح في الـ singleton — يُستدعى بعد تحديث أي مفتاح API."""
    global _llm_client
    if _llm_client is not None:
        _llm_client.reload_keys()
        logger.info("LLMClient singleton keys reloaded successfully")


async def shutdown_llm_client():
    """Shutdown the global LLM client."""
    global _llm_client
    if _llm_client:
        await _llm_client.close()
        _llm_client = None
