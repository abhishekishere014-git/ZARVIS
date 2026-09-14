"""Centralized in-memory registry for JARVIS tool discovery and management."""

import logging
from typing import Any, Callable, Dict, List, Optional
from jarvis.ai.models import ToolDefinition as AIToolDefinition
from jarvis.tools.errors import DuplicateToolError, ToolNotFoundError
from jarvis.tools.models import (
    RiskLevel,
    ToolDefinition,
    ToolPermission,
)

logger = logging.getLogger("jarvis.tools.registry")


class ToolRegistry:
    """Centralized tool repository supporting registration, lifecycle control, and discovery."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable[..., Any]] = {}

    def register(self, tool_def: ToolDefinition, handler: Callable[..., Any]) -> None:
        """Registers a tool definition and its execution handler.

        Raises:
            DuplicateToolError: if a tool with the same ID is already registered.
            ValueError: if tool definition is invalid or handler is not callable.
        """
        if not tool_def.id or not isinstance(tool_def.id, str):
            raise ValueError("Tool ID must be a non-empty string.")

        if tool_def.id in self._tools:
            raise DuplicateToolError(f"Tool with ID '{tool_def.id}' is already registered.")

        if not callable(handler):
            raise ValueError(f"Handler for tool '{tool_def.id}' must be callable.")

        self._tools[tool_def.id] = tool_def
        self._handlers[tool_def.id] = handler
        logger.debug("Registered tool: id='%s' category='%s' risk='%s'", tool_def.id, tool_def.category, tool_def.risk_level.value)

    def register_tool(self, func: Callable[..., Any]) -> ToolDefinition:
        """Convenience method to register a function decorated with @tool."""
        tool_def = getattr(func, "tool_definition", None)
        if tool_def is None or not isinstance(tool_def, ToolDefinition):
            raise ValueError(f"Function {getattr(func, '__name__', str(func))} is not decorated with @tool.")

        self.register(tool_def, func)
        return tool_def

    def unregister(self, tool_id: str) -> bool:
        """Removes a tool from registry. Returns True if removed, False if not found."""
        if tool_id in self._tools:
            del self._tools[tool_id]
            self._handlers.pop(tool_id, None)
            logger.debug("Unregistered tool '%s'", tool_id)
            return True
        return False

    def get(self, tool_id: str) -> ToolDefinition:
        """Retrieves a tool definition by ID. Raises ToolNotFoundError if missing."""
        if tool_id not in self._tools:
            raise ToolNotFoundError(f"Tool '{tool_id}' is not registered.")
        return self._tools[tool_id]

    def get_handler(self, tool_id: str) -> Callable[..., Any]:
        """Retrieves the executable handler for a tool ID."""
        if tool_id not in self._handlers:
            raise ToolNotFoundError(f"No executable handler registered for tool '{tool_id}'.")
        return self._handlers[tool_id]

    def has(self, tool_id: str) -> bool:
        """Checks if a tool is registered."""
        return tool_id in self._tools

    def enable(self, tool_id: str) -> None:
        """Enables a registered tool."""
        tool_def = self.get(tool_id)
        tool_def.enabled = True

    def disable(self, tool_id: str) -> None:
        """Disables a registered tool."""
        tool_def = self.get(tool_id)
        tool_def.enabled = False

    def list(self, category: Optional[str] = None, enabled_only: bool = True) -> List[ToolDefinition]:
        """Lists registered tools with optional category and enabled filtering."""
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        if category is not None:
            tools = [t for t in tools if t.category.lower() == category.lower()]
        return tools

    def discover(
        self,
        category: Optional[str] = None,
        max_risk_level: Optional[RiskLevel] = None,
        required_permission: Optional[ToolPermission] = None,
        enabled_only: bool = True,
    ) -> List[ToolDefinition]:
        """Discovers tools meeting specific capability, risk, and category constraints."""
        tools = self.list(category=category, enabled_only=enabled_only)

        if max_risk_level is not None:
            risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
            max_idx = risk_order.index(max_risk_level)
            tools = [t for t in tools if risk_order.index(t.risk_level) <= max_idx]

        if required_permission is not None:
            tools = [t for t in tools if required_permission in t.permissions]

        return tools

    def export_ai_tool_definitions(
        self,
        category: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[AIToolDefinition]:
        """Converts registered tools into Phase 03 AIProvider ToolDefinition schemas."""
        tools = self.list(category=category, enabled_only=enabled_only)
        return [
            AIToolDefinition(
                name=t.id,
                description=t.description,
                parameters=t.input_schema,
            )
            for t in tools
        ]
