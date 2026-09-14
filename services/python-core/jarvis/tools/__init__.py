"""JARVIS Sandboxed Tool Execution Subsystem."""

from jarvis.tools.audit import AuditLogger, scrub_secrets
from jarvis.tools.bridge import AIToolBridge
from jarvis.tools.decorator import generate_tool_schema, tool
from jarvis.tools.errors import (
    ArtifactVerificationError,
    DuplicateToolError,
    PermissionDeniedError,
    ResourceLimitExceededError,
    RiskCheckFailedError,
    SandboxViolationError,
    ToolDisabledError,
    ToolError,
    ToolExecutionTimeoutError,
    ToolNotFoundError,
    ToolValidationError,
)
from jarvis.tools.executor import ToolExecutor
from jarvis.tools.factory import ToolSystem, build_tool_system
from jarvis.tools.models import (
    ApprovalMode,
    RiskLevel,
    ToolAuditEvent,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolPermission,
    ToolPolicyDecision,
    ToolRequest,
    ToolResult,
)
from jarvis.tools.permissions import SecurityProfile
from jarvis.tools.policy import ToolPolicyEngine
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.sandbox import FileSystemSandbox

__all__ = [
    # Models & Enums
    "ToolPermission",
    "RiskLevel",
    "ApprovalMode",
    "ToolExecutionStatus",
    "ToolDefinition",
    "ToolRequest",
    "ToolResult",
    "ToolExecutionContext",
    "ToolPolicyDecision",
    "ToolAuditEvent",
    # Permissions & Policy
    "SecurityProfile",
    "ToolPolicyEngine",
    # Sandbox
    "FileSystemSandbox",
    # Errors
    "ToolError",
    "ToolNotFoundError",
    "DuplicateToolError",
    "ToolDisabledError",
    "ToolValidationError",
    "PermissionDeniedError",
    "RiskCheckFailedError",
    "SandboxViolationError",
    "ToolExecutionTimeoutError",
    "ResourceLimitExceededError",
    "ArtifactVerificationError",
    # Registry & Decorator
    "ToolRegistry",
    "tool",
    "generate_tool_schema",
    # Executor & Audit
    "ToolExecutor",
    "AuditLogger",
    "scrub_secrets",
    # Bridge & Factory
    "AIToolBridge",
    "ToolSystem",
    "build_tool_system",
]
