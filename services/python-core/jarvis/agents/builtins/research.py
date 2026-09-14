"""ResearchAgent specializing in information gathering and structured evidence formulation."""

from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.models import (
    AgentCapability,
    AgentDefinition,
    AgentStepResult,
    TaskState,
)
from jarvis.agents.observation import ObservationNormalizer
from jarvis.ai.models import ChatMessage, LLMRequest


class ResearchAgent(BaseAgent):
    """Gathers information, summarizes findings, and organizes evidence for downstream tasks."""

    def __init__(self) -> None:
        definition = AgentDefinition(
            id="agent.research",
            name="Research Agent",
            description="Performs structured information synthesis and evidence gathering.",
            capabilities={AgentCapability.RESEARCH},
            risk_level="low",
            model_role="research",
        )
        super().__init__(definition)

    async def execute(self, context: AgentContext) -> AgentStepResult:
        task_desc = context.task.description
        findings = f"Research findings for: {task_desc}"

        if context.router:
            try:
                system_prompt = (
                    "You are the JARVIS Research Specialist. Provide structured, accurate, "
                    "evidence-based notes and key facts to assist downstream coding and document generation."
                )
                req = LLMRequest(
                    messages=[
                        ChatMessage.system(system_prompt),
                        ChatMessage.user(task_desc),
                    ],
                    temperature=0.3,
                )
                llm_res = await context.router.generate(req)
                if llm_res.content:
                    findings = llm_res.content.strip()
            except Exception:
                pass

        obs = ObservationNormalizer.from_agent_computation(
            task_id=context.task.id,
            output=findings,
            evidence={"topic": task_desc},
        )

        return AgentStepResult(
            task_id=context.task.id,
            agent_id=self.id,
            status=TaskState.COMPLETED,
            output=findings,
            observations=[obs],
            evidence={"findings_length": len(findings)},
        )
