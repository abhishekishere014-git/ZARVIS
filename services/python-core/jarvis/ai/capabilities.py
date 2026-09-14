"""Model capability metadata and profile registry."""

from typing import Dict
from pydantic import BaseModel, Field


class ModelCapabilities(BaseModel):
    """Explicit capability matrix for a specific model."""

    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    supports_json: bool = True
    supports_reasoning: bool = False
    is_local: bool = False
    context_window: int = 128_000
    max_output_tokens: int = 4096


# Default well-known capability profiles
KNOWN_MODEL_CAPABILITIES: Dict[str, ModelCapabilities] = {
    # OpenAI
    "gpt-4o": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        supports_json=True,
        context_window=128_000,
        max_output_tokens=4096,
    ),
    "gpt-4o-mini": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        supports_json=True,
        context_window=128_000,
        max_output_tokens=4096,
    ),
    "o3-mini": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=False,
        supports_json=True,
        supports_reasoning=True,
        context_window=200_000,
        max_output_tokens=100_000,
    ),
    # Anthropic
    "claude-3-5-sonnet-20241022": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        supports_json=True,
        context_window=200_000,
        max_output_tokens=8192,
    ),
    "claude-3-7-sonnet-20250219": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        supports_json=True,
        supports_reasoning=True,
        context_window=200_000,
        max_output_tokens=64_000,
    ),
    "claude-3-5-haiku-20241022": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        supports_json=True,
        context_window=200_000,
        max_output_tokens=8192,
    ),
    # Google Gemini
    "gemini-1.5-pro": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        supports_json=True,
        context_window=2_000_000,
        max_output_tokens=8192,
    ),
    "gemini-2.0-flash": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        supports_json=True,
        context_window=1_000_000,
        max_output_tokens=8192,
    ),
    "gemini-2.5-flash": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        supports_json=True,
        context_window=1_000_000,
        max_output_tokens=8192,
    ),
    # Local Ollama defaults
    "llama3": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=False,
        supports_json=True,
        is_local=True,
        context_window=8192,
        max_output_tokens=2048,
    ),
    "llama3.1": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=False,
        supports_json=True,
        is_local=True,
        context_window=128_000,
        max_output_tokens=4096,
    ),
    "qwen2.5": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=False,
        supports_json=True,
        is_local=True,
        context_window=32_768,
        max_output_tokens=4096,
    ),
    "mistral": ModelCapabilities(
        supports_streaming=True,
        supports_tools=True,
        supports_vision=False,
        supports_json=True,
        is_local=True,
        context_window=32_768,
        max_output_tokens=4096,
    ),
}


def get_default_capabilities(model_name: str, is_local: bool = False) -> ModelCapabilities:
    """Retrieve capabilities from known matrix, or produce sensible defaults."""
    for known_key, caps in KNOWN_MODEL_CAPABILITIES.items():
        if known_key in model_name.lower():
            return caps
    return ModelCapabilities(is_local=is_local)
