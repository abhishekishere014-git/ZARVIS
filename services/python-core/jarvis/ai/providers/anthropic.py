"""Anthropic provider adapter implementing normalized Messages API and streaming."""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
import httpx
from jarvis.ai.base import BaseAIProvider
from jarvis.ai.errors import (
    AITimeoutError,
    AuthenticationError,
    InvalidRequestError,
    ModelNotFoundError,
    ProviderUnavailableError,
    RateLimitError,
)
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

logger = logging.getLogger("jarvis.ai.providers.anthropic")


class AnthropicProvider(BaseAIProvider):
    """Normalized Anthropic provider adapter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "claude-3-5-sonnet-20241022",
        base_url: str = "https://api.anthropic.com/v1",
        timeout: float = 60.0,
    ) -> None:
        super().__init__(
            provider_id="anthropic",
            default_model=default_model,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    def _convert_messages(self, messages: List[ChatMessage]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        system_prompt: Optional[str] = None
        formatted_messages: List[Dict[str, Any]] = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system_prompt = (system_prompt + "\n" + msg.content) if system_prompt else msg.content
            elif msg.role == Role.TOOL:
                formatted_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id or "",
                            "content": msg.content,
                        }
                    ],
                })
            elif msg.role == Role.ASSISTANT and msg.tool_calls:
                content_blocks: List[Dict[str, Any]] = []
                if msg.content:
                    content_blocks.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                formatted_messages.append({"role": "assistant", "content": content_blocks})
            else:
                formatted_messages.append({"role": msg.role.value, "content": msg.content})

        return system_prompt, formatted_messages

    def _convert_tools(self, tools: Optional[List[ToolDefinition]]) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    def _map_stop_reason(self, reason: Optional[str]) -> FinishReason:
        mapping = {
            "end_turn": FinishReason.STOP,
            "stop_sequence": FinishReason.STOP,
            "max_tokens": FinishReason.LENGTH,
            "tool_use": FinishReason.TOOL_CALLS,
        }
        return mapping.get(reason or "", FinishReason.OTHER)

    def _handle_error_response(self, response: httpx.Response) -> None:
        status = response.status_code
        try:
            body = response.json()
            message = body.get("error", {}).get("message", response.text)
        except Exception:
            message = response.text or f"HTTP {status}"

        if status in (401, 403):
            raise AuthenticationError(message, provider=self.provider_id)
        elif status == 404:
            raise ModelNotFoundError(message, provider=self.provider_id)
        elif status == 400:
            raise InvalidRequestError(message, provider=self.provider_id)
        elif status == 429:
            raise RateLimitError(message, provider=self.provider_id)
        elif status >= 500:
            raise ProviderUnavailableError(message, provider=self.provider_id, status_code=status)
        else:
            response.raise_for_status()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = self._get_client()
        target_model = request.model or self.default_model
        system_prompt, messages = self._convert_messages(request.messages)

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if request.top_p:
            payload["top_p"] = request.top_p
        if request.tools:
            payload["tools"] = self._convert_tools(request.tools)

        try:
            res = await client.post(f"{self.base_url}/messages", json=payload, timeout=request.timeout)
            if res.is_error:
                self._handle_error_response(res)

            data = res.json()
            text_chunks: List[str] = []
            tool_calls: Optional[List[ToolCall]] = None

            for block in data.get("content", []):
                if block.get("type") == "text":
                    text_chunks.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append(
                        ToolCall(
                            id=block.get("id", ""),
                            name=block.get("name", ""),
                            arguments=block.get("input", {}),
                        )
                    )

            usage_info = data.get("usage", {})
            prompt_tokens = usage_info.get("input_tokens", 0)
            completion_tokens = usage_info.get("output_tokens", 0)

            return LLMResponse(
                content="".join(text_chunks) if text_chunks else None,
                tool_calls=tool_calls,
                finish_reason=self._map_stop_reason(data.get("stop_reason")),
                model=data.get("model", target_model),
                provider=self.provider_id,
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
                request_id=data.get("id"),
            )
        except httpx.TimeoutException as exc:
            raise AITimeoutError(f"Anthropic request timed out: {exc}", provider=self.provider_id) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Network error connecting to Anthropic: {exc}", provider=self.provider_id) from exc

    async def stream(self, request: LLMRequest) -> AsyncIterator[AIStreamEvent]:
        client = self._get_client()
        target_model = request.model or self.default_model
        system_prompt, messages = self._convert_messages(request.messages)

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if request.tools:
            payload["tools"] = self._convert_tools(request.tools)

        try:
            async with client.stream("POST", f"{self.base_url}/messages", json=payload, timeout=request.timeout) as response:
                if response.is_error:
                    await response.aread()
                    self._handle_error_response(response)

                current_tool_id = ""
                current_tool_name = ""

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    event_type = chunk.get("type")
                    if event_type == "content_block_start":
                        block = chunk.get("content_block", {})
                        if block.get("type") == "tool_use":
                            current_tool_id = block.get("id", "")
                            current_tool_name = block.get("name", "")
                    elif event_type == "content_block_delta":
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield AIStreamEvent(type=StreamEventType.TEXT_DELTA, text=delta.get("text", ""))
                        elif delta.get("type") == "input_json_delta":
                            yield AIStreamEvent(
                                type=StreamEventType.TOOL_CALL_DELTA,
                                tool_call=ToolCall(
                                    id=current_tool_id,
                                    name=current_tool_name,
                                    arguments={"delta": delta.get("partial_json", "")},
                                ),
                            )
                    elif event_type == "message_delta":
                        delta = chunk.get("delta", {})
                        if delta.get("stop_reason"):
                            yield AIStreamEvent(
                                type=StreamEventType.COMPLETED,
                                finish_reason=self._map_stop_reason(delta.get("stop_reason")),
                            )
        except httpx.TimeoutException as exc:
            raise AITimeoutError(f"Anthropic stream timed out: {exc}", provider=self.provider_id) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Network error during Anthropic stream: {exc}", provider=self.provider_id) from exc
