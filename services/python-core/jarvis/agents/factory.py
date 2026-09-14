"""Factory for assembling and dependency-injecting the JARVIS Agent Runtime."""

from pathlib import Path
from typing import Any, Optional
from jarvis.agents.approval import ApprovalManager
from jarvis.agents.builtins import register_builtin_agents
from jarvis.agents.checkpoint import CheckpointStore
from jarvis.agents.executor import AgentTaskExecutor
from jarvis.agents.orchestrator import AgentOrchestrator
from jarvis.agents.plan_validator import PlanValidator
from jarvis.agents.recovery import RecoveryEngine
from jarvis.agents.registry import AgentRegistry
from jarvis.agents.synthesizer import FinalSynthesizer
from jarvis.agents.verifier import AgentVerifier
from jarvis.ai.router import AIRouter
from jarvis.config.settings import JarvisSettings
from jarvis.core.bus import AsyncEventBus
from jarvis.tools.factory import ToolSystem


class AgentSystem:
    """Consolidated container holding initialized agent runtime components."""

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        registry: AgentRegistry,
        plan_validator: PlanValidator,
        executor: AgentTaskExecutor,
        verifier: AgentVerifier,
        recovery_engine: RecoveryEngine,
        approval_manager: ApprovalManager,
        checkpoint_store: CheckpointStore,
        synthesizer: FinalSynthesizer,
        memory: Optional[Any] = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.registry = registry
        self.plan_validator = plan_validator
        self.executor = executor
        self.verifier = verifier
        self.recovery_engine = recovery_engine
        self.approval_manager = approval_manager
        self.checkpoint_store = checkpoint_store
        self.synthesizer = synthesizer
        self.memory = memory


def build_agent_system(
    router: Optional[AIRouter] = None,
    tool_system: Optional[ToolSystem] = None,
    event_bus: Optional[AsyncEventBus] = None,
    settings: Optional[JarvisSettings] = None,
    checkpoint_dir: Optional[Path] = None,
    memory: Optional[Any] = None,
    register_builtins: bool = True,
) -> AgentSystem:
    """Wires the complete autonomous multi-agent orchestration architecture."""
    effective_settings = settings or JarvisSettings()
    target_checkpoint_dir = (
        checkpoint_dir
        or (effective_settings.data_dir / "checkpoints")
    )

    registry = AgentRegistry()
    if register_builtins:
        register_builtin_agents(registry)

    plan_validator = PlanValidator(
        agent_registry=registry,
        tool_registry=tool_system.registry if tool_system else None,
    )
    executor = AgentTaskExecutor(
        agent_registry=registry,
        tool_executor=tool_system.executor if tool_system else None,
        router=router,
        memory=memory,
    )
    verifier = AgentVerifier(
        sandbox=tool_system.sandbox if tool_system else None,
    )
    recovery_engine = RecoveryEngine()
    approval_manager = ApprovalManager()
    checkpoint_store = CheckpointStore(checkpoint_dir=target_checkpoint_dir)
    synthesizer = FinalSynthesizer(router=router)

    orchestrator = AgentOrchestrator(
        registry=registry,
        plan_validator=plan_validator,
        executor=executor,
        verifier=verifier,
        recovery_engine=recovery_engine,
        approval_manager=approval_manager,
        checkpoint_store=checkpoint_store,
        synthesizer=synthesizer,
        event_bus=event_bus,
        memory=memory,
    )

    return AgentSystem(
        orchestrator=orchestrator,
        registry=registry,
        plan_validator=plan_validator,
        executor=executor,
        verifier=verifier,
        recovery_engine=recovery_engine,
        approval_manager=approval_manager,
        checkpoint_store=checkpoint_store,
        synthesizer=synthesizer,
        memory=memory,
    )
