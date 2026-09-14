"""Tests for Agent Runtime integration with Phase 03 AIRouter."""

import json
from pathlib import Path
from typing import AsyncIterator, Optional
import pytest
from jarvis.agents.base import AgentContext
from jarvis.agents.builtins.planner import PlannerAgent
from jarvis.agents.builtins.research import ResearchAgent
from jarvis.agents.models import AgentTask, TaskState
from jarvis.ai.base import AIProvider
from jarvis.ai.capabilities import ModelCapabilities
from jarvis.ai.models import (
    AIStreamEvent,
    ChatMessage,
    FinishReason,
    LLMRequest,
    LLMResponse,
    TokenUsage,
)
from jarvis.ai.registry import AIProviderRegistry
from jarvis.ai.router import AIRouter


class MockAIProvider(AIProvider):
    @property
    def provider_id(self) -> str:
        return "mock_ai"

    @property
    def default_model(self) -> str:
        return "mock-model"

    async def capabilities(self, model: Optional[str] = None) -> ModelCapabilities:
        return ModelCapabilities(
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            context_window=10000,
            default_model="mock-model",
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        last_msg = request.messages[-1].content
        if "JSON" in request.messages[0].content or "Chief Planner" in request.messages[0].content:
            mock_payload = {
                "rationale": "AI Generated decomposition",
                "tasks": [
                    {
                        "id": "task_ai_1",
                        "title": "Topic Analysis",
                        "description": "Analyze topic requirements",
                        "assigned_agent": "agent.research",
                        "dependencies": [],
                    },
                    {
                        "id": "task_ai_2",
                        "title": "Logical Synthesis",
                        "description": "Synthesize key arguments",
                        "assigned_agent": "agent.reasoning",
                        "dependencies": ["task_ai_1"],
                    },
                ],
            }
            content = json.dumps(mock_payload)
        else:
            content = f"Synthesized analysis for: {last_msg}"

        return LLMResponse(
            content=content,
            model="mock-model",
            provider="mock_ai",
            finish_reason=FinishReason.STOP,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[AIStreamEvent]:
        yield AIStreamEvent(type="text_delta", text="mock stream")

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_planner_integrates_with_ai_router() -> None:
    ai_reg = AIProviderRegistry()
    ai_reg.register(MockAIProvider())
    router = AIRouter(registry=ai_reg, default_provider="mock_ai", fallback_providers=[])

    planner = PlannerAgent()
    task = AgentTask(
        id="t_plan",
        title="Plan",
        description="Plan",
        assigned_agent=planner.id,
        input_data={"goal_prompt": "Evaluate quantum computing roadmap"},
    )
    ctx = AgentContext(run_id="run_ai", task=task, agent_definition=planner.definition, router=router)

    res = await planner.execute(ctx)
    assert res.status == TaskState.COMPLETED
    plan = res.output["plan"]
    assert len(plan["tasks"]) == 2
    assert plan["tasks"][0]["id"] == "task_ai_1"
    assert plan["tasks"][1]["id"] == "task_ai_2"
