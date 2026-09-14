"""OpenAI provider adapter implementing normalized text and streaming generation."""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
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

logger = logging.getLogger("jarvis.ai.providers.openai")


class OpenAIProvider(BaseAIProvider):
    """Normalized OpenAI provider adapter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0,
    ) -> None:
        super().__init__(
            provider_id="openai",
            default_model=default_model,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        result = []
        for msg in messages:
            item: Dict[str, Any] = {"role": msg.role.value, "content": msg.content}
            if msg.role == Role.ASSISTANT and msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else str(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            elif msg.role == Role.TOOL:
                item["tool_call_id"] = msg.tool_call_id
                if msg.name:
                    item["name"] = msg.name
            result.append(item)
        return result

    def _convert_tools(self, tools: Optional[List[ToolDefinition]]) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    def _map_finish_reason(self, reason: Optional[str]) -> FinishReason:
        mapping = {
            "stop": FinishReason.STOP,
            "length": FinishReason.LENGTH,
            "tool_calls": FinishReason.TOOL_CALLS,
            "content_filter": FinishReason.CONTENT_FILTER,
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
            retry_after = None
            if "retry-after" in response.headers:
                try:
                    retry_after = float(response.headers["retry-after"])
                except ValueError:
                    pass
            raise RateLimitError(message, provider=self.provider_id, retry_after=retry_after)
        elif status >= 500:
            raise ProviderUnavailableError(message, provider=self.provider_id, status_code=status)
        else:
            response.raise_for_status()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = self._get_client()
        target_model = request.model or self.default_model

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": self._convert_messages(request.messages),
            "temperature": request.temperature,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.top_p:
            payload["top_p"] = request.top_p
        if request.tools:
            payload["tools"] = self._convert_tools(request.tools)
            if request.tool_choice:
                payload["tool_choice"] = request.tool_choice

        try:
            res = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=request.timeout,
            )
            if res.is_error:
                self._handle_error_response(res)

            data = res.json()
            choice = data["choices"][0]
            msg = choice["message"]

            # Parse normalized tool calls
            tool_calls = None
            if "tool_calls" in msg and msg["tool_calls"]:
                tool_calls = []
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    args = {}
                    try:
                        args = json.loads(fn.get("arguments", "{}"))
                    except Exception:
                        pass
                    tool_calls.append(ToolCall(id=tc["id"], name=fn.get("name", ""), arguments=args))

            usage_data = data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            return LLMResponse(
                content=msg.get("content"),
                tool_calls=tool_calls,
                finish_reason=self._map_finish_reason(choice.get("finish_reason")),
                model=data.get("model", target_model),
                provider=self.provider_id,
                usage=usage,
                request_id=data.get("id"),
            )
        except httpx.TimeoutException as exc:
            raise AITimeoutError(f"OpenAI request timed out: {exc}", provider=self.provider_id) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Network error connecting to OpenAI: {exc}", provider=self.provider_id) from exc

    async def stream(self, request: LLMRequest) -> AsyncIterator[AIStreamEvent]:
        client = self._get_client()
        target_model = request.model or self.default_model

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": self._convert_messages(request.messages),
            "temperature": request.temperature,
            "stream": True,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.tools:
            payload["tools"] = self._convert_tools(request.tools)

        try:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=request.timeout,
            ) as response:
                if response.is_error:
                    await response.aread()
                    self._handle_error_response(response)

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choice = chunk.get("choices", [{}])[0]
                    delta = choice.get("delta", {})

                    if "content" in delta and delta["content"]:
                        yield AIStreamEvent(type=StreamEventType.TEXT_DELTA, text=delta["content"])

                    if "tool_calls" in delta and delta["tool_calls"]:
                        for tc in delta["tool_calls"]:
                            fn = tc.get("function", {})
                            yield AIStreamEvent(
                                type=StreamEventType.TOOL_CALL_DELTA,
                                tool_call=ToolCall(
                                    id=tc.get("id", ""),
                                    name=fn.get("name", ""),
                                    arguments={"delta": fn.get("arguments", "")},
                                ),
                            )

                    if choice.get("finish_reason"):
                        yield AIStreamEvent(
                            type=StreamEventType.COMPLETED,
                            finish_reason=self._map_finish_reason(choice.get("finish_reason")),
                        )
        except httpx.TimeoutException as exc:
            raise AITimeoutError(f"OpenAI stream timed out: {exc}", provider=self.provider_id) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Network error during OpenAI streaming: {exc}", provider=self.provider_id) from exc
