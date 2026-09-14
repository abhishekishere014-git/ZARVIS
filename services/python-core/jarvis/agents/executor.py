"""Execution coordinator dispatching tasks to specialized agents and mediating Phase 04 tools."""

import logging
import time
from typing import Any, Dict, List, Optional
from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.models import (
    AgentObservation,
    AgentStepResult,
    AgentTask,
    TaskState,
)
from jarvis.agents.observation import ObservationNormalizer
from jarvis.agents.registry import AgentRegistry
from jarvis.ai.router import AIRouter
from jarvis.tools.executor import ToolExecutor
from jarvis.tools.models import ToolRequest

logger = logging.getLogger("jarvis.agents.executor")


class AgentTaskExecutor:
    """Supervises task execution by specialized agents and coordinates tool execution via Phase 04 ToolExecutor."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        tool_executor: Optional[ToolExecutor] = None,
        router: Optional[AIRouter] = None,
        memory: Optional[Any] = None,
    ) -> None:
        self.agent_registry = agent_registry
        self.tool_executor = tool_executor
        self.router = router
        self.memory = memory

    async def execute_task(
        self,
        run_id: str,
        task: AgentTask,
        prior_observations: Optional[List[AgentObservation]] = None,
    ) -> AgentStepResult:
        """Executes a single task by invoking its assigned specialized agent."""
        start_time = time.perf_counter()
        agent_id = task.assigned_agent

        try:
            agent = self.agent_registry.get(agent_id)
        except KeyError:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = f"Assigned agent '{agent_id}' is not registered."
            logger.error(error_msg)
            return AgentStepResult(
                task_id=task.id,
                agent_id=agent_id,
                status=TaskState.FAILED,
                error=error_msg,
            )

        if not agent.definition.enabled:
            error_msg = f"Assigned agent '{agent_id}' is currently disabled."
            logger.error(error_msg)
            return AgentStepResult(
                task_id=task.id,
                agent_id=agent_id,
                status=TaskState.FAILED,
                error=error_msg,
            )

        # Build context
        context = AgentContext(
            run_id=run_id,
            task=task,
            agent_definition=agent.definition,
            router=self.router,
            tool_executor=self.tool_executor,
            memory=self.memory,
            prior_observations=prior_observations or [],
        )

        try:
            logger.info("Executing task '%s' via agent '%s'...", task.id, agent_id)
            step_result = await agent.execute(context)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.info(
                "Task '%s' completed with status '%s' in %.2f ms",
                task.id,
                step_result.status.value,
                duration_ms,
            )
            return step_result
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("Agent '%s' failed on task '%s': %s", agent_id, task.id, exc, exc_info=True)
            return AgentStepResult(
                task_id=task.id,
                agent_id=agent_id,
                status=TaskState.FAILED,
                error=str(exc),
            )

    async def execute_tool_for_agent(
        self,
        agent: BaseAgent,
        tool_id: str,
        arguments: Dict[str, any],
        correlation_id: Optional[str] = None,
        task_id: str = "unknown",
    ) -> AgentObservation:
        """Executes a Phase 04 tool on behalf of an agent, verifying tool authorization."""
        if not self.tool_executor:
            raise RuntimeError("Cannot execute tool: No ToolExecutor configured.")

        # Verify tool is authorized for this agent
        if agent.definition.allowed_tools and tool_id not in agent.definition.allowed_tools:
            error_msg = f"Agent '{agent.id}' is not authorized to invoke tool '{tool_id}'."
            logger.warning(error_msg)
            return ObservationNormalizer.from_agent_computation(
                task_id=task_id,
                output=None,
                status="denied",
                error=error_msg,
            )

        # Delegate directly to Phase 04 ToolExecutor
        request = ToolRequest(
            tool_id=tool_id,
            arguments=arguments,
            correlation_id=correlation_id,
            caller=agent.id,
        )
        tool_res = await self.tool_executor.execute(request)
        return ObservationNormalizer.from_tool_result(task_id=task_id, result=tool_res)
