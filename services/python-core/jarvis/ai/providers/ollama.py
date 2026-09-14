"""Local Ollama provider adapter implementing normalized chat and NDJSON streaming."""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from jarvis.ai.base import BaseAIProvider
from jarvis.ai.errors import (
    AITimeoutError,
    InvalidRequestError,
    ModelNotFoundError,
    ProviderUnavailableError,
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
from jarvis.core.health import ComponentHealth, HealthStatus

logger = logging.getLogger("jarvis.ai.providers.ollama")


class OllamaProvider(BaseAIProvider):
    """Normalized local Ollama provider adapter."""

    def __init__(
        self,
        default_model: str = "llama3",
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 90.0,
    ) -> None:
        super().__init__(
            provider_id="ollama",
            default_model=default_model,
            base_url=base_url,
            api_key=None,  # No API key required for local Ollama
            timeout=timeout,
        )

    def _build_headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        formatted = []
        for msg in messages:
            item: Dict[str, Any] = {"role": msg.role.value, "content": msg.content}
            if msg.role == Role.ASSISTANT and msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                    }
                    for tc in msg.tool_calls
                ]
            formatted.append(item)
        return formatted

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

    async def health(self) -> ComponentHealth:
        """Probe local Ollama daemon connectivity and installed models."""
        client = self._get_client()
        try:
            res = await client.get(f"{self.base_url}/api/tags", timeout=3.0)
            if res.is_success:
                models = [m.get("name") for m in res.json().get("models", [])]
                return ComponentHealth(
                    name=f"ai_provider.{self.provider_id}",
                    status=HealthStatus.HEALTHY,
                    details={
                        "provider": self.provider_id,
                        "base_url": self.base_url,
                        "installed_models": models,
                    },
                )
            return ComponentHealth(
                name=f"ai_provider.{self.provider_id}",
                status=HealthStatus.DEGRADED,
                message=f"Ollama returned HTTP {res.status_code}",
            )
        except Exception as e:
            return ComponentHealth(
                name=f"ai_provider.{self.provider_id}",
                status=HealthStatus.DEGRADED,
                message=f"Local Ollama daemon not running at {self.base_url}: {e}",
            )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = self._get_client()
        target_model = request.model or self.default_model

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": self._convert_messages(request.messages),
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }
        if request.top_p:
            payload["options"]["top_p"] = request.top_p
        if request.tools:
            payload["tools"] = self._convert_tools(request.tools)

        try:
            res = await client.post(f"{self.base_url}/api/chat", json=payload, timeout=request.timeout)
            if res.is_error:
                if res.status_code == 404:
                    raise ModelNotFoundError(f"Model '{target_model}' not found in Ollama", provider=self.provider_id, model=target_model)
                raise ProviderUnavailableError(f"Ollama error: {res.text}", provider=self.provider_id, status_code=res.status_code)

            data = res.json()
            msg = data.get("message", {})

            tool_calls: Optional[List[ToolCall]] = None
            if "tool_calls" in msg and msg["tool_calls"]:
                tool_calls = []
                for idx, tc in enumerate(msg["tool_calls"]):
                    fn = tc.get("function", {})
                    tool_calls.append(
                        ToolCall(
                            id=f"ollama_{fn.get('name')}_{idx}",
                            name=fn.get("name", ""),
                            arguments=fn.get("arguments", {}),
                        )
                    )

            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)

            return LLMResponse(
                content=msg.get("content"),
                tool_calls=tool_calls,
                finish_reason=FinishReason.STOP if data.get("done") else FinishReason.OTHER,
                model=data.get("model", target_model),
                provider=self.provider_id,
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
            )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(f"Could not connect to local Ollama at {self.base_url}: {exc}", provider=self.provider_id) from exc
        except httpx.TimeoutException as exc:
            raise AITimeoutError(f"Ollama request timed out: {exc}", provider=self.provider_id) from exc

    async def stream(self, request: LLMRequest) -> AsyncIterator[AIStreamEvent]:
        client = self._get_client()
        target_model = request.model or self.default_model

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": self._convert_messages(request.messages),
            "stream": True,
            "options": {
                "temperature": request.temperature,
            },
        }
        if request.tools:
            payload["tools"] = self._convert_tools(request.tools)

        try:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload, timeout=request.timeout) as response:
                if response.is_error:
                    await response.aread()
                    raise ProviderUnavailableError(f"Ollama streaming error: {response.text}", provider=self.provider_id)

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg = chunk.get("message", {})
                    if "content" in msg and msg["content"]:
                        yield AIStreamEvent(type=StreamEventType.TEXT_DELTA, text=msg["content"])

                    if chunk.get("done"):
                        yield AIStreamEvent(
                            type=StreamEventType.COMPLETED,
                            finish_reason=FinishReason.STOP,
                            usage=TokenUsage(
                                prompt_tokens=chunk.get("prompt_eval_count", 0),
                                completion_tokens=chunk.get("eval_count", 0),
                                total_tokens=chunk.get("prompt_eval_count", 0) + chunk.get("eval_count", 0),
                            ),
                        )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(f"Could not connect to local Ollama stream at {self.base_url}: {exc}", provider=self.provider_id) from exc
        except httpx.TimeoutException as exc:
            raise AITimeoutError(f"Ollama stream timed out: {exc}", provider=self.provider_id) from exc
