"""Factory for assembling the complete JARVIS tool subsystem."""

from pathlib import Path
from typing import Optional
from jarvis.config.settings import JarvisSettings
from jarvis.core.bus import AsyncEventBus
from jarvis.tools.audit import AuditLogger
from jarvis.tools.bridge import AIToolBridge
from jarvis.tools.builtins import register_builtin_tools
from jarvis.tools.executor import ToolExecutor
from jarvis.tools.permissions import SecurityProfile
from jarvis.tools.policy import ToolPolicyEngine
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.sandbox import FileSystemSandbox


class ToolSystem:
    """Consolidated container holding the initialized tool subsystem components."""

    def __init__(
        self,
        registry: ToolRegistry,
        sandbox: FileSystemSandbox,
        policy_engine: ToolPolicyEngine,
        executor: ToolExecutor,
        audit_logger: AuditLogger,
        bridge: AIToolBridge,
    ) -> None:
        self.registry = registry
        self.sandbox = sandbox
        self.policy_engine = policy_engine
        self.executor = executor
        self.audit_logger = audit_logger
        self.bridge = bridge


def build_tool_system(
    settings: Optional[JarvisSettings] = None,
    event_bus: Optional[AsyncEventBus] = None,
    workspace_dir: Optional[Path] = None,
    security_profile: Optional[SecurityProfile] = None,
    register_builtins: bool = True,
) -> ToolSystem:
    """Assembles and wires the full tool execution engine."""
    effective_settings = settings or JarvisSettings()
    target_workspace = (
        workspace_dir
        or getattr(effective_settings, "workspace_dir", None)
        or (effective_settings.data_dir / "workspace")
    )

    sandbox = FileSystemSandbox(workspace_root=target_workspace)
    profile = security_profile or SecurityProfile()
    policy_engine = ToolPolicyEngine(default_profile=profile, sandbox=sandbox)
    registry = ToolRegistry()
    audit_logger = AuditLogger()

    executor = ToolExecutor(
        registry=registry,
        policy_engine=policy_engine,
        sandbox=sandbox,
        event_bus=event_bus,
        audit_logger=audit_logger,
    )
    bridge = AIToolBridge(executor=executor)

    if register_builtins:
        register_builtin_tools(registry)

    return ToolSystem(
        registry=registry,
        sandbox=sandbox,
        policy_engine=policy_engine,
        executor=executor,
        audit_logger=audit_logger,
        bridge=bridge,
    )
