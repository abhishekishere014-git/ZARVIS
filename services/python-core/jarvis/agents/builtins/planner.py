"""PlannerAgent responsible for goal decomposition, dependency graphing, and plan generation."""

import json
from typing import Any, Dict, List
from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.models import (
    AgentCapability,
    AgentDefinition,
    AgentPlan,
    AgentStepResult,
    AgentTask,
    TaskState,
)
from jarvis.ai.models import ChatMessage, LLMRequest


class PlannerAgent(BaseAgent):
    """Decomposes complex user goals into dependency-ordered DAG execution plans."""

    def __init__(self) -> None:
        definition = AgentDefinition(
            id="agent.planner",
            name="Planner Agent",
            description="Decomposes user objectives into structured, dependency-ordered tasks.",
            capabilities={AgentCapability.PLANNING},
            risk_level="low",
            model_role="reasoning",
        )
        super().__init__(definition)

    async def execute(self, context: AgentContext) -> AgentStepResult:
        goal_prompt = context.task.input_data.get("goal_prompt", context.task.description)
        run_id = context.run_id

        # If an LLM router is available, attempt intelligent model-driven decomposition
        if context.router:
            try:
                system_prompt = (
                    "You are the JARVIS Chief Planner. Break down the user's goal into a logical list of 2 to 5 tasks. "
                    "Available agents: 'agent.research', 'agent.reasoning', 'agent.coding', 'agent.security', "
                    "'agent.testing', 'agent.review', 'agent.verifier', 'agent.synthesis'.\n"
                    "Available office tools: 'office.create_docx', 'office.create_xlsx', 'office.create_pptx', 'office.create_pdf'.\n"
                    "Respond with a JSON object strictly conforming to:\n"
                    "{\n"
                    '  "rationale": "short explanation",\n'
                    '  "tasks": [\n'
                    '    {"id": "task_1", "title": "...", "description": "...", "assigned_agent": "agent.research", "dependencies": [], "required_tools": []},\n'
                    '    {"id": "task_2", "title": "...", "description": "...", "assigned_agent": "agent.coding", "dependencies": ["task_1"], "required_tools": ["office.create_docx"]}\n'
                    "  ]\n"
                    "}"
                )
                req = LLMRequest(
                    messages=[
                        ChatMessage.system(system_prompt),
                        ChatMessage.user(f"Goal: {goal_prompt}"),
                    ],
                    temperature=0.2,
                    response_format="json_object",
                )
                llm_res = await context.router.generate(req)
                if llm_res.content:
                    parsed = json.loads(llm_res.content)
                    raw_tasks = parsed.get("tasks", [])
                    tasks: List[AgentTask] = []
                    for t in raw_tasks:
                        tasks.append(
                            AgentTask(
                                id=t["id"],
                                title=t["title"],
                                description=t["description"],
                                assigned_agent=t.get("assigned_agent", "agent.reasoning"),
                                dependencies=t.get("dependencies", []),
                                required_tools=t.get("required_tools", []),
                                input_data={"goal_prompt": goal_prompt},
                            )
                        )
                    if tasks:
                        plan = AgentPlan(
                            goal_id=context.task.id,
                            tasks=tasks,
                            rationale=parsed.get("rationale", "AI generated plan"),
                            estimated_steps=len(tasks),
                        )
                        return AgentStepResult(
                            task_id=context.task.id,
                            agent_id=self.id,
                            status=TaskState.COMPLETED,
                            output={"plan": plan.model_dump()},
                        )
            except Exception:
                pass  # Fallback to deterministic decomposition below

        # Deterministic default decomposition when LLM is unavailable or unconfigured
        tasks = self._deterministic_decompose(goal_prompt)
        plan = AgentPlan(
            goal_id=context.task.id,
            tasks=tasks,
            rationale="Deterministic workflow decomposition",
            estimated_steps=len(tasks),
        )
        return AgentStepResult(
            task_id=context.task.id,
            agent_id=self.id,
            status=TaskState.COMPLETED,
            output={"plan": plan.model_dump()},
        )

    def _deterministic_decompose(self, goal: str) -> List[AgentTask]:
        """Produces a deterministic, verified multi-stage plan based on goal keywords."""
        lower_goal = goal.lower()

        # Check for Office generation goals
        if "presentation" in lower_goal or "pptx" in lower_goal or "slide" in lower_goal:
            return [
                AgentTask(
                    id="task_research",
                    title="Topic Research & Outline",
                    description=f"Gather outline and structured points for: {goal}",
                    assigned_agent="agent.research",
                    dependencies=[],
                ),
                AgentTask(
                    id="task_generate_pptx",
                    title="Generate PowerPoint Presentation",
                    description="Create presentation deck using office.create_pptx",
                    assigned_agent="agent.coding",
                    dependencies=["task_research"],
                    required_tools=["office.create_pptx"],
                ),
                AgentTask(
                    id="task_verify",
                    title="Verify Presentation Artifact",
                    description="Confirm physical existence and slide integrity",
                    assigned_agent="agent.verifier",
                    dependencies=["task_generate_pptx"],
                ),
            ]

        if "spreadsheet" in lower_goal or "excel" in lower_goal or "xlsx" in lower_goal:
            return [
                AgentTask(
                    id="task_research",
                    title="Gather Data & Dimensions",
                    description=f"Formulate data schema for: {goal}",
                    assigned_agent="agent.research",
                    dependencies=[],
                ),
                AgentTask(
                    id="task_generate_xlsx",
                    title="Generate Excel Workbook",
                    description="Create workbook using office.create_xlsx",
                    assigned_agent="agent.coding",
                    dependencies=["task_research"],
                    required_tools=["office.create_xlsx"],
                ),
                AgentTask(
                    id="task_verify",
                    title="Verify Workbook Artifact",
                    description="Confirm worksheet integrity",
                    assigned_agent="agent.verifier",
                    dependencies=["task_generate_xlsx"],
                ),
            ]

        if "document" in lower_goal or "docx" in lower_goal or "word" in lower_goal:
            return [
                AgentTask(
                    id="task_research",
                    title="Draft Document Content",
                    description=f"Draft sections and narrative for: {goal}",
                    assigned_agent="agent.research",
                    dependencies=[],
                ),
                AgentTask(
                    id="task_generate_docx",
                    title="Generate Word Document",
                    description="Create formatted document using office.create_docx",
                    assigned_agent="agent.coding",
                    dependencies=["task_research"],
                    required_tools=["office.create_docx"],
                ),
                AgentTask(
                    id="task_verify",
                    title="Verify Document Artifact",
                    description="Confirm paragraphs and table structure",
                    assigned_agent="agent.verifier",
                    dependencies=["task_generate_docx"],
                ),
            ]

        if "pdf" in lower_goal:
            return [
                AgentTask(
                    id="task_research",
                    title="Draft PDF Sections",
                    description=f"Draft report structure for: {goal}",
                    assigned_agent="agent.research",
                    dependencies=[],
                ),
                AgentTask(
                    id="task_generate_pdf",
                    title="Generate PDF Document",
                    description="Create PDF document using office.create_pdf",
                    assigned_agent="agent.coding",
                    dependencies=["task_research"],
                    required_tools=["office.create_pdf"],
                ),
                AgentTask(
                    id="task_verify",
                    title="Verify PDF Artifact",
                    description="Confirm binary header and page integrity",
                    assigned_agent="agent.verifier",
                    dependencies=["task_generate_pdf"],
                ),
            ]

        # General reasoning & synthesis workflow
        return [
            AgentTask(
                id="task_analyze",
                title="Goal Analysis",
                description=f"Analyze requirements and implications of: {goal}",
                assigned_agent="agent.reasoning",
                dependencies=[],
            ),
            AgentTask(
                id="task_review",
                title="Security & Consistency Review",
                description="Review findings for security and logical consistency",
                assigned_agent="agent.review",
                dependencies=["task_analyze"],
            ),
        ]
