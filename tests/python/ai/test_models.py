import pytest
from jarvis.ai.capabilities import ModelCapabilities, get_default_capabilities
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


def test_chat_message_helpers():
    sys_msg = ChatMessage.system("You are JARVIS.")
    assert sys_msg.role == Role.SYSTEM
    assert sys_msg.content == "You are JARVIS."

    user_msg = ChatMessage.user("Hello JARVIS.")
    assert user_msg.role == Role.USER

    tool_call = ToolCall(id="tc-1", name="search", arguments={"q": "weather"})
    asst_msg = ChatMessage.assistant("Searching...", tool_calls=[tool_call])
    assert asst_msg.role == Role.ASSISTANT
    assert len(asst_msg.tool_calls) == 1
    assert asst_msg.tool_calls[0].name == "search"

    tool_msg = ChatMessage.tool("Sunny, 24C", tool_call_id="tc-1", name="search")
    assert tool_msg.role == Role.TOOL
    assert tool_msg.tool_call_id == "tc-1"


def test_tool_definition_and_request_validation():
    tool = ToolDefinition(
        name="calculator",
        description="Calculates math expressions",
        parameters={
            "type": "object",
            "properties": {"expr": {"type": "string"}},
            "required": ["expr"],
        },
    )

    req = LLMRequest(
        messages=[ChatMessage.user("What is 2+2?")],
        tools=[tool],
        temperature=0.2,
    )
    assert len(req.tools) == 1
    assert req.tools[0].name == "calculator"
    assert req.temperature == 0.2


def test_response_and_usage_accounting():
    usage = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    res = LLMResponse(
        content="4",
        model="gpt-4o",
        provider="openai",
        finish_reason=FinishReason.STOP,
        usage=usage,
    )
    assert res.content == "4"
    assert res.usage.total_tokens == 15
    assert res.finish_reason == FinishReason.STOP


def test_stream_events():
    event = AIStreamEvent(type=StreamEventType.TEXT_DELTA, text="Hel")
    assert event.type == StreamEventType.TEXT_DELTA
    assert event.text == "Hel"


def test_model_capabilities_defaults():
    gpt4_caps = get_default_capabilities("gpt-4o")
    assert gpt4_caps.supports_tools is True
    assert gpt4_caps.supports_vision is True

    unknown_caps = get_default_capabilities("unknown-model-xyz")
    assert unknown_caps.supports_streaming is True
    assert unknown_caps.is_local is False
