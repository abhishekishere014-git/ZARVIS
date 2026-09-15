"""System bootstrap wiring all JARVIS subsystems into a unified runtime engine."""

from __future__ import annotations

import logging
from typing import Optional

from jarvis.agents.factory import build_agent_system
from jarvis.config.settings import JarvisSettings
from jarvis.core.engine import JarvisEngine
from jarvis.ipc.server import IPCServer
from jarvis.ipc.service import IPCService
from jarvis.ipc.subsystems import SubsystemRegistry
from jarvis.memory.manager import MemoryManager
from jarvis.tools.factory import build_tool_system
from jarvis.vision.manager import VisionManager
from jarvis.voice.factory import build_voice_pipeline

logger = logging.getLogger("jarvis.bootstrap")


def bootstrap_system(
    settings: Optional[JarvisSettings] = None,
    engine: Optional[JarvisEngine] = None,
) -> tuple[JarvisEngine, SubsystemRegistry]:
    """Assembles all subsystem components and attaches them to the JarvisEngine lifecycle."""
    effective_settings = settings or JarvisSettings()
    target_engine = engine or JarvisEngine(settings=effective_settings)

    logger.info("Bootstrapping JARVIS multi-layer subsystems...")

    # 1. Memory Subsystem (Phase 06)
    memory_manager: Optional[MemoryManager] = None
    try:
        memory_manager = MemoryManager(event_bus=target_engine.bus)
        logger.info("Memory Subsystem initialized.")
    except Exception as exc:
        logger.warning("Memory Subsystem init error: %s", exc)

    # 2. Tool Subsystem (Phase 04)
    tool_system = build_tool_system(
        settings=effective_settings,
        event_bus=target_engine.bus,
        register_builtins=True,
    )
    logger.info("Tool Subsystem initialized (%d tools).", len(tool_system.registry.list()))

    # 3. Autonomous Multi-Agent Runtime (Phase 05)
    agent_system = build_agent_system(
        tool_system=tool_system,
        event_bus=target_engine.bus,
        settings=effective_settings,
        memory=memory_manager,
        register_builtins=True,
    )
    logger.info("Agent Runtime initialized.")

    # 4. Vision Subsystem (Phase 09)
    try:
        import sys
        if sys.platform == "win32" and effective_settings.env != "test":
            from jarvis.os.providers.windows import WindowsOSProvider
            os_provider = WindowsOSProvider()
        else:
            from jarvis.os.providers.mock import MockOSProvider
            os_provider = MockOSProvider()
    except Exception:
        from jarvis.os.providers.mock import MockOSProvider
        os_provider = MockOSProvider()

    from jarvis.os.screen.capture import ScreenCaptureManager
    screen_capture = ScreenCaptureManager(provider=os_provider)
    vision_manager = VisionManager(screen_capture=screen_capture, event_bus=target_engine.bus)
    logger.info("Vision Subsystem initialized with ScreenCaptureManager.")

    # 5. Voice & Audio Pipeline (Phase 07)
    voice_pipeline = build_voice_pipeline(
        settings=effective_settings,
        orchestrator=agent_system.orchestrator,
        event_bus=target_engine.bus,
        use_mock_audio=True,
        use_mock_models=True,
    )
    logger.info("Voice Pipeline initialized.")

    # 6. Subsystem Registry & IPC Server (Phase 10 & 11)
    subsystems = SubsystemRegistry(
        agent_orchestrator=agent_system.orchestrator,
        vision_manager=vision_manager,
        voice_pipeline=voice_pipeline,
        tool_system=tool_system,
        memory_manager=memory_manager,
    )

    ipc_server = IPCServer(
        host=effective_settings.core_host,
        port=effective_settings.core_port,
        event_bus=target_engine.bus,
        subsystems=subsystems,
    )

    ipc_service = IPCService(server=ipc_server)
    target_engine.register_service(ipc_service)
    logger.info("Registered IPCService on JarvisEngine (Port %d).", effective_settings.core_port)

    return target_engine, subsystems
