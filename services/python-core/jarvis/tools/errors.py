"""Structured exception taxonomy for the JARVIS Tool Subsystem."""

from typing import Any, Dict, Optional


class ToolError(Exception):
    """Base exception for all tool execution and registry failures."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ToolNotFoundError(ToolError):
    """Raised when an execution target is not registered in the ToolRegistry."""
    pass


class DuplicateToolError(ToolError):
    """Raised when attempting to register a tool with an existing tool ID."""
    pass


class ToolDisabledError(ToolError):
    """Raised when attempting to execute a tool that is marked disabled."""
    pass


class ToolValidationError(ToolError):
    """Raised when tool arguments or definitions fail schema validation."""
    pass


class PermissionDeniedError(ToolError):
    """Raised when the execution environment lacks required tool permissions."""
    pass


class RiskCheckFailedError(ToolError):
    """Raised when a tool request is rejected based on risk policy or approval mode."""
    pass


class SandboxViolationError(ToolError):
    """Raised when a tool attempts path traversal or accesses unauthorized resources."""
    pass


class ToolExecutionTimeoutError(ToolError):
    """Raised when tool execution exceeds its configured timeout deadline."""
    pass


class ResourceLimitExceededError(ToolError):
    """Raised when document payload exceeds configured size, row, or page boundaries."""
    pass


class ArtifactVerificationError(ToolError):
    """Raised when a generated artifact fails post-creation structural verification."""
    pass
