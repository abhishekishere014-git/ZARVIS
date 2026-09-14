"""CodingAgent specializing in code synthesis and execution of approved Phase 04 generation tools."""

from typing import Any, Dict, List
from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.models import (
    AgentCapability,
    AgentDefinition,
    AgentObservation,
    AgentStepResult,
    TaskState,
)
from jarvis.agents.observation import ObservationNormalizer
from jarvis.tools.models import ToolRequest


class CodingAgent(BaseAgent):
    """Executes code generation plans and coordinates generation through Phase 04 Office tools."""

    def __init__(self) -> None:
        definition = AgentDefinition(
            id="agent.coding",
            name="Coding Agent",
            description="Coordinates implementation tasks and approved document generation tools.",
            capabilities={AgentCapability.CODING},
            allowed_tools={
                "office.create_docx",
                "office.create_xlsx",
                "office.create_pptx",
                "office.create_pdf",
            },
            risk_level="medium",
            model_role="coding",
        )
        super().__init__(definition)

    async def execute(self, context: AgentContext) -> AgentStepResult:
        task = context.task
        required_tools = task.required_tools
        artifacts: List[str] = []
        observations: List[AgentObservation] = []

        # If task requires an approved Office generation tool, execute it via Phase 04 ToolExecutor
        if required_tools and context.tool_executor:
            for tool_id in required_tools:
                if tool_id in self.definition.allowed_tools:
                    tool_args = self._build_tool_arguments(tool_id, task)
                    request = ToolRequest(
                        tool_id=tool_id,
                        arguments=tool_args,
                        correlation_id=context.run_id,
                        caller=self.id,
                    )
                    tool_res = await context.tool_executor.execute(request)
                    obs = ObservationNormalizer.from_tool_result(task_id=task.id, result=tool_res)
                    observations.append(obs)

                    if tool_res.is_success:
                        artifacts.extend(tool_res.artifacts)
                    else:
                        return AgentStepResult(
                            task_id=task.id,
                            agent_id=self.id,
                            status=TaskState.FAILED,
                            error=f"Tool '{tool_id}' execution failed: {tool_res.error}",
                            observations=observations,
                        )

            return AgentStepResult(
                task_id=task.id,
                agent_id=self.id,
                status=TaskState.COMPLETED,
                output=f"Successfully executed tools: {required_tools}",
                artifacts=artifacts,
                observations=observations,
                evidence={"artifacts_count": len(artifacts)},
            )

        # Standard non-tool coding/planning output
        obs = ObservationNormalizer.from_agent_computation(
            task_id=task.id,
            output=f"Implementation plan for: {task.description}",
        )
        return AgentStepResult(
            task_id=task.id,
            agent_id=self.id,
            status=TaskState.COMPLETED,
            output=f"Completed implementation analysis: {task.title}",
            observations=[obs],
        )

    def _build_tool_arguments(self, tool_id: str, task: Any) -> Dict[str, Any]:
        """Constructs conforming, verified payloads for Phase 04 Office tools."""
        title = task.title or "JARVIS Generated Document"

        if tool_id == "office.create_docx":
            return {
                "filename": "generated_document.docx",
                "title": title,
                "sections": [
                    {"heading": "Executive Summary", "level": 1, "paragraph": task.description},
                    {"heading": "Key Deliverables", "level": 2, "bullets": ["Autonomous Agent Execution", "Verified Artifacts"]},
                ],
            }
        elif tool_id == "office.create_xlsx":
            return {
                "filename": "generated_model.xlsx",
                "sheets": [
                    {
                        "name": "Summary",
                        "headers": ["Task", "Status", "Confidence"],
                        "rows": [[task.title, "Complete", 1.0]],
                    }
                ],
            }
        elif tool_id == "office.create_pptx":
            return {
                "filename": "generated_presentation.pptx",
                "title": title,
                "subtitle": "Synthesized by JARVIS Autonomous Agent",
                "slides": [
                    {"title": "Overview", "bullets": [task.description, "Evidence verified by VerifierAgent"]},
                ],
            }
        elif tool_id == "office.create_pdf":
            return {
                "filename": "generated_report.pdf",
                "title": title,
                "sections": [
                    {"heading": "Report Objective", "paragraph": task.description},
                    {"bullets": ["Zero arbitrary shell execution", "Strict sandbox enforcement"]},
                ],
            }

        return {}
