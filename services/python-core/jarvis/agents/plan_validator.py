"""DAG-based PlanValidator enforcing acyclicity, dependencies, bounds, and tool validity."""

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set
from jarvis.agents.models import AgentPlan, AgentTask
from jarvis.agents.registry import AgentRegistry
from jarvis.tools.registry import ToolRegistry


class PlanValidationError(Exception):
    """Raised when an AgentPlan fails structural, dependency, or agent constraints."""
    pass


class PlanValidator:
    """Validates execution plans and produces topologically sorted execution waves."""

    def __init__(
        self,
        max_steps: int = 20,
        agent_registry: Optional[AgentRegistry] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        self.max_steps = max_steps
        self.agent_registry = agent_registry
        self.tool_registry = tool_registry

    def validate_and_sort(self, plan: AgentPlan) -> List[List[AgentTask]]:
        """Validates the execution plan DAG and returns tasks partitioned into concurrent execution waves.

        Raises:
            PlanValidationError: if bounds are exceeded, cycles are detected, or dependencies are missing.
        """
        if not plan.tasks:
            raise PlanValidationError("Plan must contain at least one task.")

        if len(plan.tasks) > self.max_steps:
            raise PlanValidationError(
                f"Plan step count ({len(plan.tasks)}) exceeds maximum permitted ({self.max_steps})."
            )

        # 1. Unique task IDs
        task_map: Dict[str, AgentTask] = {}
        for task in plan.tasks:
            if not task.id or not isinstance(task.id, str):
                raise PlanValidationError("Every task must have a non-empty string ID.")
            if task.id in task_map:
                raise PlanValidationError(f"Duplicate task ID detected in plan: '{task.id}'")
            task_map[task.id] = task

        # 2. Dependency validation & Agent/Tool checks
        for task in plan.tasks:
            for dep in task.dependencies:
                if dep == task.id:
                    raise PlanValidationError(f"Task '{task.id}' cannot depend on itself.")
                if dep not in task_map:
                    raise PlanValidationError(
                        f"Task '{task.id}' specifies nonexistent dependency: '{dep}'"
                    )

            if self.agent_registry:
                if not self.agent_registry.has(task.assigned_agent):
                    raise PlanValidationError(
                        f"Task '{task.id}' assigned to unregistered agent: '{task.assigned_agent}'"
                    )
                agent = self.agent_registry.get(task.assigned_agent)
                if not agent.definition.enabled:
                    raise PlanValidationError(
                        f"Task '{task.id}' assigned to disabled agent: '{task.assigned_agent}'"
                    )

            if self.tool_registry:
                for tool_id in task.required_tools:
                    if not self.tool_registry.has(tool_id):
                        raise PlanValidationError(
                            f"Task '{task.id}' requires unregistered tool: '{tool_id}'"
                        )
                    tool_def = self.tool_registry.get(tool_id)
                    if not tool_def.enabled:
                        raise PlanValidationError(
                            f"Task '{task.id}' requires disabled tool: '{tool_id}'"
                        )

        # 3. Cycle Detection & Wave Generation via Kahn's Algorithm
        # Edge: dependency -> task (dependency must finish before task can start)
        in_degree: Dict[str, int] = {t_id: len(t.dependencies) for t_id, t in task_map.items()}
        dependents: Dict[str, List[str]] = defaultdict(list)
        for t_id, task in task_map.items():
            for dep in task.dependencies:
                dependents[dep].append(t_id)

        waves: List[List[AgentTask]] = []
        current_wave = [task_map[t_id] for t_id, deg in in_degree.items() if deg == 0]
        processed_count = 0

        while current_wave:
            waves.append(current_wave)
            processed_count += len(current_wave)
            next_wave: List[AgentTask] = []

            for task in current_wave:
                for dep_target in dependents[task.id]:
                    in_degree[dep_target] -= 1
                    if in_degree[dep_target] == 0:
                        next_wave.append(task_map[dep_target])

            current_wave = next_wave

        if processed_count < len(task_map):
            cycle_tasks = [t_id for t_id, deg in in_degree.items() if deg > 0]
            raise PlanValidationError(
                f"Circular dependency detected in plan involving tasks: {cycle_tasks}"
            )

        return waves
