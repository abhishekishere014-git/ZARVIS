"""JARVIS AI Layer: Model-Agnostic AI Provider Framework."""

from jarvis.ai.base import AIProvider, BaseAIProvider
from jarvis.ai.capabilities import ModelCapabilities, get_default_capabilities
from jarvis.ai.errors import (
    AICancelledError,
    AIError,
    AIStreamError,
    AITimeoutError,
    AuthenticationError,
    CapabilityNotSupportedError,
    InvalidRequestError,
    ModelNotFoundError,
    ProviderUnavailableError,
    RateLimitError,
)
from jarvis.ai.factory import build_ai_system
from jarvis.ai.models import (
    AIStreamEvent,
    ChatMessage,
    FinishReason,
    LLMRequest,
    LLMResponse,
    Role,
    StreamEventType,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)
from jarvis.ai.providers import (
    AnthropicProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
)
from jarvis.ai.registry import AIProviderRegistry
from jarvis.ai.retry import RetryPolicy
from jarvis.ai.router import AIRouter

__all__ = [
    "AIProvider",
    "BaseAIProvider",
    "AIProviderRegistry",
    "AIRouter",
    "RetryPolicy",
    "ModelCapabilities",
    "get_default_capabilities",
    "build_ai_system",
    # Models
    "ChatMessage",
    "Role",
    "ToolCall",
    "ToolDefinition",
    "TokenUsage",
    "FinishReason",
    "LLMRequest",
    "LLMResponse",
    "AIStreamEvent",
    "StreamEventType",
    # Errors
    "AIError",
    "AuthenticationError",
    "InvalidRequestError",
    "ModelNotFoundError",
    "RateLimitError",
    "ProviderUnavailableError",
    "AITimeoutError",
    "AIStreamError",
    "AICancelledError",
    "CapabilityNotSupportedError",
    # Providers
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "OllamaProvider",
]
