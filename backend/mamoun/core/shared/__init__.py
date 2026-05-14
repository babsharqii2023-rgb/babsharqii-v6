"""
Shared infrastructure package — components used by both old and new paths.

These are the CANONICAL implementations for:
- NeuralBus: Event bus for inter-component communication
- MultiProviderLLMClient: Multi-provider LLM client with true diversity
- Registry: Tool and agent registries
- ZaiSdkWrapper: Bridge to Node.js z-ai-web-dev-sdk
"""

from .multi_provider_llm import (
    MultiProviderLLMClient,
    ProviderName,
    ProviderConfig,
    LLMResponse,
    DEFAULT_PROVIDERS,
)

from .neural_bus import (
    Event,
    EventType,
    NeuralBus,
    get_neural_bus,
)

from .registry import (
    get_tool_registry,
    get_agent_registry,
)

__all__ = [
    # LLM
    "MultiProviderLLMClient",
    "ProviderName",
    "ProviderConfig",
    "LLMResponse",
    "DEFAULT_PROVIDERS",
    # NeuralBus
    "Event",
    "EventType",
    "NeuralBus",
    "get_neural_bus",
    # Registry
    "get_tool_registry",
    "get_agent_registry",
]
