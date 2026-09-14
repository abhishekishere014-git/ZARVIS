"""Normalized contracts and data models for the JARVIS Tool Subsystem."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class ToolPermission(str, Enum):
    """Explicit capability permissions required by tools."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    SYSTEM = "system"


class RiskLevel(str, Enum):
    """Standardized risk tier for tools."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalMode(str, Enum):
    """Human-in-the-loop authorization policy."""

    AUTO_APPROVE = "auto_approve"
    USER_APPROVAL = "user_approval"
    ALWAYS_DENY = "always_deny"


class ToolExecutionStatus(str, Enum):
    """Terminal state of a tool execution attempt."""

    SUCCESS = "success"
    FAILED = "failed"
    DENIED = "denied"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ToolDefinition(BaseModel):
    """Immutable specification of a registered tool."""

    id: str = Field(description="Unique tool identifier, e.g. 'office.create_docx'")
    name: str = Field(description="Human-readable tool name")
    version: str = Field(default="1.0.0", description="SemVer string")
    description: str = Field(description="Functional description for AI model guidance")
    category: str = Field(default="general", description="Categorical classification, e.g. 'office', 'filesystem'")
    input_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema specifying acceptable input arguments",
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional JSON Schema specifying expected output structure",
    )
    permissions: Set[ToolPermission] = Field(
        default_factory=set,
        description="Set of required permissions",
    )
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Inherent risk classification")
    approval_mode: ApprovalMode = Field(
        default=ApprovalMode.AUTO_APPROVE,
        description="Approval workflow requirement",
    )
    timeout_seconds: float = Field(default=30.0, ge=0.1, le=600.0, description="Max execution duration in seconds")
    enabled: bool = Field(default=True, description="Whether tool is active in registry")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolRequest(BaseModel):
    """Invocation request directed to a tool."""

    execution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique execution identifier",
    )
    tool_id: str = Field(description="Target tool ID to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Input arguments matching input_schema")
    correlation_id: Optional[str] = None
    caller: str = Field(default="agent", description="Request originator, e.g. 'agent', 'user', 'scheduler'")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Normalized output returned from tool execution."""

    execution_id: str
    tool_id: str
    status: ToolExecutionStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = Field(default=0.0, ge=0.0)
    artifacts: List[str] = Field(
        default_factory=list,
        description="Paths or URIs of generated files / artifacts",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == ToolExecutionStatus.SUCCESS


class ToolPolicyDecision(BaseModel):
    """Outcome of policy engine evaluation for a tool request."""

    allowed: bool
    approval_required: bool = False
    reason: str
    risk_level: RiskLevel = RiskLevel.LOW
    permissions_required: Set[ToolPermission] = Field(default_factory=set)


class ToolExecutionContext(BaseModel):
    """Execution sandbox context passed into tool implementation functions."""

    model_config = {"arbitrary_types_allowed": True}

    execution_id: str
    tool_id: str
    correlation_id: Optional[str] = None
    caller: str = "agent"
    workspace_dir: Path
    sandbox: Any = None  # Reference to FileSystemSandbox
    timeout_seconds: float = 30.0
    extra: Dict[str, Any] = Field(default_factory=dict)


class ToolAuditEvent(BaseModel):
    """Structured, secret-scrubbed audit record for tool operations."""

    execution_id: str
    tool_id: str
    tool_version: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    correlation_id: Optional[str] = None
    actor: str = "agent"
    policy_decision: str
    duration_ms: float = 0.0
    status: ToolExecutionStatus
    error_code: Optional[str] = None
    arguments_summary: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
