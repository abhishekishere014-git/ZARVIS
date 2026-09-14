"""Google Gemini provider adapter implementing normalized generateContent and streamGenerateContent."""

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

logger = logging.getLogger("jarvis.ai.providers.gemini")


class GeminiProvider(BaseAIProvider):
    """Normalized Google Gemini provider adapter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "gemini-2.0-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 60.0,
    ) -> None:
        super().__init__(
            provider_id="gemini",
            default_model=default_model,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["x-goog-api-key"] = self._api_key
        return headers

    def _convert_messages(self, messages: List[ChatMessage]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        system_instruction: Optional[Dict[str, Any]] = None
        contents: List[Dict[str, Any]] = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system_instruction = {"parts": [{"text": msg.content}]}
            elif msg.role == Role.TOOL:
                contents.append({
                    "role": "function",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": msg.name or "tool",
                                "response": {"content": msg.content},
                            }
                        }
                    ],
                })
            elif msg.role == Role.ASSISTANT and msg.tool_calls:
                parts: List[Dict[str, Any]] = []
                if msg.content:
                    parts.append({"text": msg.content})
                for tc in msg.tool_calls:
                    parts.append({"functionCall": {"name": tc.name, "args": tc.arguments}})
                contents.append({"role": "model", "parts": parts})
            else:
                role = "model" if msg.role == Role.ASSISTANT else "user"
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        return system_instruction, contents

    def _convert_tools(self, tools: Optional[List[ToolDefinition]]) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        return [
            {
                "function_declarations": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    }
                    for t in tools
                ]
            }
        ]

    def _map_finish_reason(self, reason: Optional[str]) -> FinishReason:
        mapping = {
            "STOP": FinishReason.STOP,
            "MAX_TOKENS": FinishReason.LENGTH,
            "SAFETY": FinishReason.CONTENT_FILTER,
            "RECITATION": FinishReason.CONTENT_FILTER,
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
        system_instruction, contents = self._convert_messages(request.messages)

        payload: Dict[str, Any] = {"contents": contents}
        if system_instruction:
            payload["system_instruction"] = system_instruction
        if request.tools:
            payload["tools"] = self._convert_tools(request.tools)

        gen_config: Dict[str, Any] = {"temperature": request.temperature}
        if request.max_tokens:
            gen_config["maxOutputTokens"] = request.max_tokens
        if request.top_p:
            gen_config["topP"] = request.top_p
        payload["generationConfig"] = gen_config

        url = f"{self.base_url}/models/{target_model}:generateContent"

        try:
            res = await client.post(url, json=payload, timeout=request.timeout)
            if res.is_error:
                self._handle_error_response(res)

            data = res.json()
            candidate = data.get("candidates", [{}])[0]
            parts = candidate.get("content", {}).get("parts", [])

            text_parts: List[str] = []
            tool_calls: Optional[List[ToolCall]] = None

            for i, part in enumerate(parts):
                if "text" in part:
                    text_parts.append(part["text"])
                elif "functionCall" in part:
                    if tool_calls is None:
                        tool_calls = []
                    fc = part["functionCall"]
                    tool_calls.append(
                        ToolCall(
                            id=f"call_{fc.get('name', 'fn')}_{i}",
                            name=fc.get("name", ""),
                            arguments=fc.get("args", {}),
                        )
                    )

            usage_data = data.get("usageMetadata", {})
            prompt_tokens = usage_data.get("promptTokenCount", 0)
            completion_tokens = usage_data.get("candidatesTokenCount", 0)

            return LLMResponse(
                content="".join(text_parts) if text_parts else None,
                tool_calls=tool_calls,
                finish_reason=self._map_finish_reason(candidate.get("finishReason")),
                model=target_model,
                provider=self.provider_id,
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
            )
        except httpx.TimeoutException as exc:
            raise AITimeoutError(f"Gemini request timed out: {exc}", provider=self.provider_id) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Network error connecting to Gemini: {exc}", provider=self.provider_id) from exc

    async def stream(self, request: LLMRequest) -> AsyncIterator[AIStreamEvent]:
        client = self._get_client()
        target_model = request.model or self.default_model
        system_instruction, contents = self._convert_messages(request.messages)

        payload: Dict[str, Any] = {"contents": contents}
        if system_instruction:
            payload["system_instruction"] = system_instruction
        if request.tools:
            payload["tools"] = self._convert_tools(request.tools)

        gen_config: Dict[str, Any] = {"temperature": request.temperature}
        if request.max_tokens:
            gen_config["maxOutputTokens"] = request.max_tokens
        payload["generationConfig"] = gen_config

        url = f"{self.base_url}/models/{target_model}:streamGenerateContent?alt=sse"

        try:
            async with client.stream("POST", url, json=payload, timeout=request.timeout) as response:
                if response.is_error:
                    await response.aread()
                    self._handle_error_response(response)

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    candidate = chunk.get("candidates", [{}])[0]
                    parts = candidate.get("content", {}).get("parts", [])
                    for part in parts:
                        if "text" in part:
                            yield AIStreamEvent(type=StreamEventType.TEXT_DELTA, text=part["text"])
                        elif "functionCall" in part:
                            fc = part["functionCall"]
                            yield AIStreamEvent(
                                type=StreamEventType.TOOL_CALL_DELTA,
                                tool_call=ToolCall(
                                    id=f"call_{fc.get('name')}",
                                    name=fc.get("name", ""),
                                    arguments=fc.get("args", {}),
                                ),
                            )

                    if candidate.get("finishReason"):
                        yield AIStreamEvent(
                            type=StreamEventType.COMPLETED,
                            finish_reason=self._map_finish_reason(candidate.get("finishReason")),
                        )
        except httpx.TimeoutException as exc:
            raise AITimeoutError(f"Gemini stream timed out: {exc}", provider=self.provider_id) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Network error during Gemini stream: {exc}", provider=self.provider_id) from exc
