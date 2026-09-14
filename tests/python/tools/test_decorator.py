"""Tests for @tool decorator and automatic function introspection."""

from typing import List, Optional
import pytest
from jarvis.tools.decorator import generate_tool_schema, tool
from jarvis.tools.models import (
    ApprovalMode,
    RiskLevel,
    ToolDefinition,
    ToolExecutionContext,
    ToolPermission,
)


def test_automatic_schema_generation_from_function() -> None:
    def sample_func(
        query: str,
        limit: int = 10,
        tags: Optional[List[str]] = None,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        """Searches documents.

        :param query: The search query text
        :param limit: Maximum items to return
        :param tags: Optional list of filtering tags
        """
        return f"results for {query}"

    schema = generate_tool_schema(sample_func)

    assert schema["type"] == "object"
    assert "context" not in schema["properties"]  # Injected context skipped
    assert "query" in schema["properties"]
    assert schema["properties"]["query"]["type"] == "string"
    assert schema["properties"]["query"]["description"] == "The search query text"

    assert "limit" in schema["properties"]
    assert schema["properties"]["limit"]["type"] == "integer"
    assert schema["properties"]["limit"]["default"] == 10

    assert "tags" in schema["properties"]
    assert schema["properties"]["tags"]["type"] == "array"

    assert "query" in schema["required"]
    assert "limit" not in schema["required"]
    assert "tags" not in schema["required"]


@pytest.mark.asyncio
async def test_tool_decorator_metadata_attachment() -> None:
    @tool(
        tool_id="math.multiply",
        name="Multiply Numbers",
        description="Multiplies two numbers",
        category="math",
        permissions={ToolPermission.READ},
        risk_level=RiskLevel.LOW,
        approval_mode=ApprovalMode.AUTO_APPROVE,
        timeout_seconds=5.0,
    )
    async def multiply(a: float, b: float) -> float:
        """Multiply two floating point values.

        :param a: First operand
        :param b: Second operand
        """
        return a * b

    assert hasattr(multiply, "tool_definition")
    tool_def: ToolDefinition = getattr(multiply, "tool_definition")
    assert tool_def.id == "math.multiply"
    assert tool_def.name == "Multiply Numbers"
    assert tool_def.category == "math"
    assert ToolPermission.READ in tool_def.permissions
    assert tool_def.timeout_seconds == 5.0
    assert "a" in tool_def.input_schema["properties"]
    assert "b" in tool_def.input_schema["properties"]

    # Test direct execution still functions
    result = await multiply(3.0, 4.0)
    assert result == 12.0
