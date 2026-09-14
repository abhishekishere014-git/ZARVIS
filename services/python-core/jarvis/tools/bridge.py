"""Bridge connecting Phase 03 AI provider ToolCalls with Phase 04 ToolExecutor."""

import json
from typing import Optional, Tuple
from jarvis.ai.models import ChatMessage, ToolCall
from jarvis.tools.executor import ToolExecutor
from jarvis.tools.models import ToolRequest, ToolResult


class AIToolBridge:
    """Translates normalized AI ToolCalls into sandboxed ToolRequests and returns ChatMessages."""

    def __init__(self, executor: ToolExecutor) -> None:
        self.executor = executor

    async def execute_tool_call(
        self,
        tool_call: ToolCall,
        correlation_id: Optional[str] = None,
        caller: str = "agent",
    ) -> Tuple[ToolResult, ChatMessage]:
        """Dispatches an AI ToolCall through the supervised tool executor and formats the return ChatMessage."""
        request = ToolRequest(
            execution_id=tool_call.id,
            tool_id=tool_call.name,
            arguments=tool_call.arguments,
            correlation_id=correlation_id,
            caller=caller,
        )

        result = await self.executor.execute(request)

        if result.is_success:
            payload = {
                "status": result.status.value,
                "output": result.output,
                "artifacts": result.artifacts,
            }
        else:
            payload = {
                "status": result.status.value,
                "error": result.error,
            }

        message = ChatMessage.tool(
            content=json.dumps(payload, default=str),
            tool_call_id=tool_call.id,
            name=tool_call.name,
        )

        return result, message
