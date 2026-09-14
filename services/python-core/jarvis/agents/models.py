"""Normalized domain models, contracts, and enums for the JARVIS Autonomous Multi-Agent Runtime."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Lifecycle state of an autonomous agent run."""

    IDLE = "idle"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    VERIFYING = "verifying"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskState(str, Enum):
    """State of an individual task in an execution plan."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class VerificationState(str, Enum):
    """Outcome of evidence-based verification."""

    UNVERIFIED = "unverified"
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"


class RecoveryState(str, Enum):
    """Status of recovery mechanisms upon task failure."""

    NOT_REQUIRED = "not_required"
    RETRYING = "retrying"
    REPLANNING = "replanning"
    ABORTED = "aborted"
    RECOVERED = "recovered"


class AgentMessageType(str, Enum):
    """Structured message types for inter-agent communication."""

    REQUEST = "request"
    RESULT = "result"
    OBSERVATION = "observation"
    QUESTION = "question"
    WARNING = "warning"
    VERIFICATION = "verification"
    RECOVERY = "recovery"


class AgentCapability(str, Enum):
    """Explicit capability tags for specialized agents."""

    PLANNING = "planning"
    RESEARCH = "research"
    REASONING = "reasoning"
    CODING = "coding"
    SECURITY = "security"
    TESTING = "testing"
    REVIEW = "review"
    VERIFICATION = "verification"
    RECOVERY = "recovery"
    SYNTHESIS = "synthesis"


class AgentDefinition(BaseModel):
    """Metadata specification for a registered agent."""

    id: str = Field(description="Unique agent identifier, e.g. 'agent.planner'")
    name: str = Field(description="Human-readable agent name")
    description: str = Field(description="Functional purpose and specialization of the agent")
    capabilities: Set[AgentCapability] = Field(default_factory=set)
    allowed_tools: Set[str] = Field(default_factory=set, description="Set of tool IDs this agent may request")
    risk_level: str = Field(default="low", description="Maximum risk tier agent is permitted to initiate")
    enabled: bool = Field(default=True)
    system_instructions: Optional[str] = None
    model_role: str = Field(default="default", description="Model configuration role, e.g. 'reasoning', 'coding'")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentGoal(BaseModel):
    """High-level objective submitted to the JARVIS Orchestrator."""

    id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:12]}")
    user_prompt: str = Field(description="The original user goal or instruction")
    constraints: List[str] = Field(default_factory=list)
    expected_output: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    """Discrete, actionable task inside an execution plan."""

    id: str = Field(description="Unique task ID, e.g. 'task_1'")
    title: str
    description: str
    assigned_agent: str = Field(description="ID of the specialized agent assigned to execute this task")
    dependencies: List[str] = Field(
        default_factory=list,
        description="IDs of prerequisite tasks that must complete before this task executes",
    )
    required_tools: List[str] = Field(default_factory=list)
    state: TaskState = TaskState.PENDING
    timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    artifacts: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentPlan(BaseModel):
    """Structured, DAG-based plan decomposed from an AgentGoal."""

    goal_id: str
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    tasks: List[AgentTask] = Field(default_factory=list)
    rationale: str = ""
    estimated_steps: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentObservation(BaseModel):
    """Structured observation captured after executing a tool or subtask."""

    task_id: str
    tool_id: Optional[str] = None
    status: str
    output: Optional[Any] = None
    artifacts: List[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    evidence: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentStepResult(BaseModel):
    """Output produced by a specialized agent upon executing a task."""

    task_id: str
    agent_id: str
    status: TaskState
    output: Optional[Any] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list)
    observations: List[AgentObservation] = Field(default_factory=list)
    error: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)


class AgentVerification(BaseModel):
    """Verification outcome evaluating whether task output conforms to requirements."""

    task_id: str
    state: VerificationState
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    verified_artifacts: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    notes: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentApprovalRequest(BaseModel):
    """Human-in-the-loop authorization request for high-risk operations."""

    approval_id: str = Field(default_factory=lambda: f"appr_{uuid.uuid4().hex[:12]}")
    run_id: str
    task_id: str
    agent_id: str
    tool_id: str
    reason: str
    risk_level: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    approved: Optional[bool] = None
    resolved_by: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentRecoveryAttempt(BaseModel):
    """Record of a failure mitigation or replanning attempt."""

    attempt_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:12]}")
    task_id: str
    failure_reason: str
    recovery_action: str
    state: RecoveryState
    attempt_number: int
    duration_ms: float = 0.0


class AgentRun(BaseModel):
    """Complete execution record for a goal submitted to the orchestrator."""

    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    goal: AgentGoal
    plan: Optional[AgentPlan] = None
    state: AgentState = AgentState.IDLE
    current_task_id: Optional[str] = None
    completed_tasks: List[str] = Field(default_factory=list)
    failed_tasks: List[str] = Field(default_factory=list)
    task_results: Dict[str, AgentStepResult] = Field(default_factory=dict)
    verifications: Dict[str, AgentVerification] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    recovery_attempts: List[AgentRecoveryAttempt] = Field(default_factory=list)
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    duration_ms: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentFinalResponse(BaseModel):
    """Coherent, synthesized final response delivered to the user."""

    run_id: str
    goal_id: str
    status: AgentState
    summary: str
    verified_artifacts: List[str] = Field(default_factory=list)
    task_statistics: Dict[str, int] = Field(default_factory=dict)
    execution_time_ms: float = 0.0
    error: Optional[str] = None


class AgentMessage(BaseModel):
    """Structured communication payload exchanged between agents."""

    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    run_id: str
    sender_agent: str
    recipient_agent: str
    task_id: Optional[str] = None
    message_type: AgentMessageType
    payload: Dict[str, Any] = Field(default_factory=dict)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentCheckpoint(BaseModel):
    """Serialized state representation allowing an interrupted run to resume."""

    checkpoint_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:12]}")
    run: AgentRun
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
