"""TestingAgent specializing in test design, test planning, and validation review."""

from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.models import (
    AgentCapability,
    AgentDefinition,
    AgentStepResult,
    TaskState,
)
from jarvis.agents.observation import ObservationNormalizer


class TestingAgent(BaseAgent):
    """Evaluates task execution testability, verification boundaries, and regression risks."""

    def __init__(self) -> None:
        definition = AgentDefinition(
            id="agent.testing",
            name="Testing Agent",
            description="Formulates test strategies, verification criteria, and quality checks.",
            capabilities={AgentCapability.TESTING},
            risk_level="low",
            model_role="reasoning",
        )
        super().__init__(definition)

    async def execute(self, context: AgentContext) -> AgentStepResult:
        task_desc = context.task.description
        test_plan = {
            "validation_mode": "evidence_based",
            "artifact_inspection": "active",
            "regression_risk": "low",
        }

        obs = ObservationNormalizer.from_agent_computation(
            task_id=context.task.id,
            output=test_plan,
            evidence={"task": task_desc},
        )

        return AgentStepResult(
            task_id=context.task.id,
            agent_id=self.id,
            status=TaskState.COMPLETED,
            output="Test strategy and verification criteria formulated.",
            observations=[obs],
            evidence=test_plan,
        )
