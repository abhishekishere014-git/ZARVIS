"""Normalized core contracts for AI requests, responses, messages, and streaming."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    """Normalized representation of a function / tool invocation."""

    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Provider-agnostic tool / function definition."""

    name: str
    description: str
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema describing expected tool parameters",
    )


class ChatMessage(BaseModel):
    """Normalized conversation message supporting text, tools, and future multimodal expansion."""

    role: Role
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def system(cls, content: str) -> "ChatMessage":
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> "ChatMessage":
        return cls(role=Role.USER, content=content)

    @classmethod
    def assistant(cls, content: str, tool_calls: Optional[List[ToolCall]] = None) -> "ChatMessage":
        return cls(role=Role.ASSISTANT, content=content, tool_calls=tool_calls)

    @classmethod
    def tool(cls, content: str, tool_call_id: str, name: Optional[str] = None) -> "ChatMessage":
        return cls(role=Role.TOOL, content=content, tool_call_id=tool_call_id, name=name)


class TokenUsage(BaseModel):
    """Token consumption accounting across generation."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class FinishReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"
    OTHER = "other"


class LLMRequest(BaseModel):
    """Standardized generation request dispatched to AI providers."""

    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[str] = None  # "auto", "none", "required", or tool name
    response_format: Optional[Literal["text", "json_object"]] = None
    timeout: float = 60.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Normalized, vendor-neutral response returned to JARVIS Core."""

    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    finish_reason: FinishReason = FinishReason.STOP
    model: str
    provider: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StreamEventType(str, Enum):
    TEXT_DELTA = "text_delta"
    TOOL_CALL_DELTA = "tool_call_delta"
    REASONING_DELTA = "reasoning_delta"
    USAGE = "usage"
    COMPLETED = "completed"
    ERROR = "error"


class AIStreamEvent(BaseModel):
    """Normalized incremental event yielded during response streaming."""

    type: StreamEventType
    text: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    usage: Optional[TokenUsage] = None
    error: Optional[str] = None
    finish_reason: Optional[FinishReason] = None
