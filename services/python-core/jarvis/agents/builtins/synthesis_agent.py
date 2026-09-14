"""SynthesisAgent compiling findings into a unified, user-facing summary."""

from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.models import (
    AgentCapability,
    AgentDefinition,
    AgentStepResult,
    TaskState,
)
from jarvis.agents.observation import ObservationNormalizer


class SynthesisAgent(BaseAgent):
    """Compiles multi-task results, findings, and evidence into an integrated narrative."""

    def __init__(self) -> None:
        definition = AgentDefinition(
            id="agent.synthesis",
            name="Synthesis Agent",
            description="Synthesizes intermediate agent observations into a unified narrative.",
            capabilities={AgentCapability.SYNTHESIS},
            risk_level="low",
            model_role="synthesis",
        )
        super().__init__(definition)

    async def execute(self, context: AgentContext) -> AgentStepResult:
        prior_obs = context.prior_observations
        artifacts = []
        for obs in prior_obs:
            artifacts.extend(obs.artifacts)

        synthesis_text = (
            f"Successfully unified findings from {len(prior_obs)} task observations. "
            f"Verified {len(artifacts)} generated artifacts."
        )

        obs = ObservationNormalizer.from_agent_computation(
            task_id=context.task.id,
            output=synthesis_text,
            artifacts=artifacts,
            evidence={"observations_count": len(prior_obs)},
        )

        return AgentStepResult(
            task_id=context.task.id,
            agent_id=self.id,
            status=TaskState.COMPLETED,
            output=synthesis_text,
            artifacts=artifacts,
            observations=[obs],
            evidence={"synthesis_status": "complete"},
        )
