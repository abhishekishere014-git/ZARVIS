"""JARVIS Autonomous Multi-Agent Runtime & Orchestration."""

from jarvis.agents.approval import ApprovalManager
from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.checkpoint import CheckpointStore
from jarvis.agents.executor import AgentTaskExecutor
from jarvis.agents.factory import AgentSystem, build_agent_system
from jarvis.agents.models import (
    AgentApprovalRequest,
    AgentCapability,
    AgentCheckpoint,
    AgentDefinition,
    AgentFinalResponse,
    AgentGoal,
    AgentMessage,
    AgentMessageType,
    AgentObservation,
    AgentPlan,
    AgentRecoveryAttempt,
    AgentRun,
    AgentState,
    AgentStepResult,
    AgentTask,
    AgentVerification,
    RecoveryState,
    TaskState,
    VerificationState,
)
from jarvis.agents.observation import ObservationNormalizer
from jarvis.agents.orchestrator import AgentOrchestrator
from jarvis.agents.plan_validator import PlanValidationError, PlanValidator
from jarvis.agents.recovery import RecoveryEngine
from jarvis.agents.registry import AgentRegistry
from jarvis.agents.synthesizer import FinalSynthesizer
from jarvis.agents.verifier import AgentVerifier

__all__ = [
    # Models & Enums
    "AgentState",
    "TaskState",
    "VerificationState",
    "RecoveryState",
    "AgentMessageType",
    "AgentCapability",
    "AgentDefinition",
    "AgentGoal",
    "AgentTask",
    "AgentPlan",
    "AgentObservation",
    "AgentStepResult",
    "AgentVerification",
    "AgentApprovalRequest",
    "AgentRecoveryAttempt",
    "AgentRun",
    "AgentFinalResponse",
    "AgentMessage",
    "AgentCheckpoint",
    # Base Contracts
    "BaseAgent",
    "AgentContext",
    # Core Components
    "AgentRegistry",
    "PlanValidator",
    "PlanValidationError",
    "ObservationNormalizer",
    "AgentVerifier",
    "RecoveryEngine",
    "ApprovalManager",
    "CheckpointStore",
    "FinalSynthesizer",
    "AgentTaskExecutor",
    "AgentOrchestrator",
    # Factory
    "AgentSystem",
    "build_agent_system",
]
