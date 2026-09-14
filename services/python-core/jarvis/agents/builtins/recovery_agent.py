"""RecoveryAgent providing replanning and alternate approach recommendations on failure."""

from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.models import (
    AgentCapability,
    AgentDefinition,
    AgentStepResult,
    TaskState,
)
from jarvis.agents.observation import ObservationNormalizer


class RecoveryAgent(BaseAgent):
    """Diagnoses failures and suggests replanning strategies, alternative agents, or alternative tools."""

    def __init__(self) -> None:
        definition = AgentDefinition(
            id="agent.recovery",
            name="Recovery Agent",
            description="Analyzes task failures and recommends bounded recovery or replanning strategies.",
            capabilities={AgentCapability.RECOVERY},
            risk_level="low",
            model_role="reasoning",
        )
        super().__init__(definition)

    async def execute(self, context: AgentContext) -> AgentStepResult:
        task_desc = context.task.description
        error_context = context.task.error or "Unknown failure"

        recommendation = {
            "failure_diagnosis": error_context,
            "recommended_strategy": "replan_with_alternative_tool",
            "alternative_agent": "agent.coding",
        }

        obs = ObservationNormalizer.from_agent_computation(
            task_id=context.task.id,
            output=recommendation,
            evidence={"task": task_desc},
        )

        return AgentStepResult(
            task_id=context.task.id,
            agent_id=self.id,
            status=TaskState.COMPLETED,
            output=f"Recovery strategy formulated: {recommendation['recommended_strategy']}",
            observations=[obs],
            evidence=recommendation,
        )
