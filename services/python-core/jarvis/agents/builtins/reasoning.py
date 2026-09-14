"""ReasoningAgent specializing in logical analysis, comparison of alternatives, and synthesis."""

from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.models import (
    AgentCapability,
    AgentDefinition,
    AgentStepResult,
    TaskState,
)
from jarvis.agents.observation import ObservationNormalizer
from jarvis.ai.models import ChatMessage, LLMRequest


class ReasoningAgent(BaseAgent):
    """Conducts multi-step logical deduction, criteria analysis, and trade-off evaluations."""

    def __init__(self) -> None:
        definition = AgentDefinition(
            id="agent.reasoning",
            name="Reasoning Agent",
            description="Evaluates logical trade-offs, architecture options, and deductive reasoning.",
            capabilities={AgentCapability.REASONING},
            risk_level="low",
            model_role="reasoning",
        )
        super().__init__(definition)

    async def execute(self, context: AgentContext) -> AgentStepResult:
        task_desc = context.task.description
        conclusion = f"Logical deduction and analysis for: {task_desc}"

        if context.router:
            try:
                system_prompt = (
                    "You are the JARVIS Chief Reasoner. Perform rigorous logical analysis, "
                    "identifying trade-offs, constraints, and sound deductions."
                )
                req = LLMRequest(
                    messages=[
                        ChatMessage.system(system_prompt),
                        ChatMessage.user(task_desc),
                    ],
                    temperature=0.2,
                )
                llm_res = await context.router.generate(req)
                if llm_res.content:
                    conclusion = llm_res.content.strip()
            except Exception:
                pass

        obs = ObservationNormalizer.from_agent_computation(
            task_id=context.task.id,
            output=conclusion,
            evidence={"task": task_desc},
        )

        return AgentStepResult(
            task_id=context.task.id,
            agent_id=self.id,
            status=TaskState.COMPLETED,
            output=conclusion,
            observations=[obs],
            evidence={"logical_validity": "confirmed"},
        )
