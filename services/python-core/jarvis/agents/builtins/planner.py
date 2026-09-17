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

        # 1. YouTube intent
        if "youtube" in lower_goal or (lower_goal.startswith("play ") and ("song" in lower_goal or "music" in lower_goal or "video" in lower_goal)):
            query = goal
            for prefix in [
                "open youtube and play",
                "open youtube and search for",
                "open youtube and search",
                "search youtube for",
                "play on youtube",
                "open youtube",
                "play",
            ]:
                if lower_goal.startswith(prefix):
                    query = goal[len(prefix):].strip()
                    break
            if " on youtube" in query.lower():
                idx = query.lower().index(" on youtube")
                query = query[:idx].strip()
            if not query or query.lower() in ("youtube", "video", "song"):
                query = "lofi hip hop beats"

            return [
                AgentTask(
                    id="task_youtube",
                    title=f"YouTube: {query}",
                    description=f"Search and open YouTube for query: {query}",
                    assigned_agent="agent.coding",
                    dependencies=[],
                    required_tools=["youtube.search_and_play"],
                    input_data={"tool_args": {"query": query}, "goal_prompt": goal},
                ),
                AgentTask(
                    id="task_verify",
                    title="Verify Browser Launch",
                    description="Verify default browser process invocation",
                    assigned_agent="agent.verifier",
                    dependencies=["task_youtube"],
                    input_data={"goal_prompt": goal},
                ),
            ]

        # 2. Web Search intent
        if any(lower_goal.startswith(p) for p in ["search the web for", "search web for", "search google for", "search for", "look up", "google"]):
            query = goal
            for prefix in ["search the web for", "search web for", "search google for", "search for", "look up", "google"]:
                if lower_goal.startswith(prefix):
                    query = goal[len(prefix):].strip()
                    break
            return [
                AgentTask(
                    id="task_search",
                    title=f"Search Web: {query}",
                    description=f"Search the web for: {query}",
                    assigned_agent="agent.coding",
                    dependencies=[],
                    required_tools=["browser.search"],
                    input_data={"tool_args": {"query": query}, "goal_prompt": goal},
                ),
                AgentTask(
                    id="task_verify",
                    title="Verify Search Launch",
                    description="Verify default browser search launch",
                    assigned_agent="agent.verifier",
                    dependencies=["task_search"],
                    input_data={"goal_prompt": goal},
                ),
            ]

        # 3. Folder / Directory Open intent
        if any(w in lower_goal for w in ["downloads", "documents", "desktop", "workspace"]) and any(w in lower_goal for w in ["open", "show", "explore", "folder", "directory"]):
            folder = "downloads"
            if "downloads" in lower_goal:
                folder = "downloads"
            elif "documents" in lower_goal:
                folder = "documents"
            elif "desktop" in lower_goal:
                folder = "desktop"
            elif "workspace" in lower_goal:
                folder = "workspace"

            return [
                AgentTask(
                    id="task_open_directory",
                    title=f"Open {folder.capitalize()} Folder",
                    description=f"Open {folder} in Windows File Explorer",
                    assigned_agent="agent.coding",
                    dependencies=[],
                    required_tools=["file.open_directory"],
                    input_data={"tool_args": {"directory_name": folder}, "goal_prompt": goal},
                ),
                AgentTask(
                    id="task_verify",
                    title="Verify Explorer Launch",
                    description=f"Verify File Explorer launched for {folder}",
                    assigned_agent="agent.verifier",
                    dependencies=["task_open_directory"],
                    input_data={"goal_prompt": goal},
                ),
            ]

        # 4. App Launch intent
        app_keywords = {
            "calculator": "Calculator",
            "calc": "Calculator",
            "notepad": "Notepad",
            "text editor": "Notepad",
            "visual studio code": "VS Code",
            "vs code": "VS Code",
            "vscode": "VS Code",
            "code": "VS Code",
            "chrome": "Chrome",
            "google chrome": "Chrome",
            "edge": "Edge",
            "settings": "Settings",
            "file explorer": "File Explorer",
            "explorer": "File Explorer",
            "paint": "Paint",
            "terminal": "PowerShell",
            "powershell": "PowerShell",
            "task manager": "Task Manager",
        }
        if any(lower_goal.startswith(p) for p in ["open ", "launch ", "start ", "run "]):
            for kw, app_name in app_keywords.items():
                if kw in lower_goal:
                    return [
                        AgentTask(
                            id="task_launch_app",
                            title=f"Launch {app_name}",
                            description=f"Launch application: {app_name}",
                            assigned_agent="agent.coding",
                            dependencies=[],
                            required_tools=["app.launch"],
                            input_data={"tool_args": {"app_name": app_name}, "goal_prompt": goal},
                        ),
                        AgentTask(
                            id="task_verify",
                            title=f"Verify {app_name} Execution",
                            description=f"Verify process state for {app_name}",
                            assigned_agent="agent.verifier",
                            dependencies=["task_launch_app"],
                            input_data={"goal_prompt": goal},
                        ),
                    ]

        # 5. Screenshot / Screen Capture intent
        if any(w in lower_goal for w in ["screenshot", "capture screen", "scan screen", "take a screenshot"]):
            return [
                AgentTask(
                    id="task_screen_capture",
                    title="Screen Capture",
                    description="Capture primary display screenshot",
                    assigned_agent="agent.coding",
                    dependencies=[],
                    required_tools=["os.screen.capture"],
                    input_data={"tool_args": {}, "goal_prompt": goal},
                ),
                AgentTask(
                    id="task_verify",
                    title="Verify Screen Capture",
                    description="Verify screen capture image artifact",
                    assigned_agent="agent.verifier",
                    dependencies=["task_screen_capture"],
                    input_data={"goal_prompt": goal},
                ),
            ]

        # 6. Window Management intent
        if "window" in lower_goal and ("list" in lower_goal or "show" in lower_goal):
            return [
                AgentTask(
                    id="task_window_list",
                    title="List Open Windows",
                    description="Enumerate visible desktop application windows",
                    assigned_agent="agent.coding",
                    dependencies=[],
                    required_tools=["os.window.list"],
                    input_data={"tool_args": {}, "goal_prompt": goal},
                ),
            ]

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
