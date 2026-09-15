"""Tests for SubsystemRegistry and IPC subsystem request handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from jarvis.agents.models import AgentFinalResponse, AgentState
from jarvis.agents.orchestrator import AgentOrchestrator
from jarvis.ipc.router import IPCRouter
from jarvis.ipc.subsystems import SubsystemRegistry
from jarvis.protocol.models import JarvisRequest, PROTOCOL_VERSION
from jarvis.tools.factory import ToolSystem
from jarvis.tools.models import ToolResult, ToolExecutionStatus
from jarvis.vision.manager import VisionManager
from jarvis.vision.models import ScreenObservation, VisualElement, ElementType, BoundingBox


@pytest.fixture
def empty_registry():
    return SubsystemRegistry()


@pytest.fixture
def populated_router():
    router = IPCRouter()
    
    # Mock Orchestrator
    orchestrator = MagicMock(spec=AgentOrchestrator)
    orchestrator.run = AsyncMock(return_value=AgentFinalResponse(
        run_id="run_test_001",
        goal_id="goal_test_001",
        status=AgentState.COMPLETED,
        summary="Task completed successfully.",
        task_statistics={"total": 3, "completed": 3},
        execution_time_ms=1230.0,
    ))

    # Mock Vision Manager
    vision = MagicMock(spec=VisionManager)
    vision.capture_and_analyze = AsyncMock(return_value=ScreenObservation(
        observation_id="obs_test_001",
        image_width=2560,
        image_height=1440,
        monitor_index=0,
        elements=[
            VisualElement(
                element_id="el_1",
                element_type=ElementType.BUTTON,
                bounds=BoundingBox(x=10, y=20, width=100, height=40),
                label="Submit",
                confidence=0.98,
            )
        ],
        active_window_title="ZARVIS Workspace",
    ))

    subsystems = SubsystemRegistry(
        agent_orchestrator=orchestrator,
        vision_manager=vision,
    )
    subsystems.register_handlers(router)
    return router, orchestrator, vision


@pytest.mark.asyncio
async def test_agent_execute_with_orchestrator(populated_router):
    router, orchestrator, _ = populated_router
    req = JarvisRequest(
        id="req_1",
        type="agent.execute",
        version=PROTOCOL_VERSION,
        timestamp="2026-09-15T00:00:00Z",
        payload={"goal": "Summarize latest sales data"},
    )
    res = await router.dispatch(req)
    assert res.success is True
    assert res.payload["run_id"] == "run_test_001"
    assert res.payload["status"] == "completed"
    assert res.payload["summary"] == "Task completed successfully."
    orchestrator.run.assert_awaited_once_with("Summarize latest sales data")


@pytest.mark.asyncio
async def test_agent_execute_validation_error(populated_router):
    router, _, _ = populated_router
    req = JarvisRequest(
        id="req_2",
        type="agent.execute",
        version=PROTOCOL_VERSION,
        timestamp="2026-09-15T00:00:00Z",
        payload={"goal": ""},
    )
    res = await router.dispatch(req)
    assert res.success is False
    assert res.error is not None
    assert "Invalid request" in res.error.message


@pytest.mark.asyncio
async def test_agent_execute_fallback(empty_registry):
    router = IPCRouter()
    empty_registry.register_handlers(router)
    req = JarvisRequest(
        id="req_3",
        type="agent.execute",
        version=PROTOCOL_VERSION,
        timestamp="2026-09-15T00:00:00Z",
        payload={"goal": "Open file"},
    )
    res = await router.dispatch(req)
    assert res.success is True
    assert res.payload["status"] == "completed"
    assert "Autonomous Agent Runtime received goal" in res.payload["summary"]


@pytest.mark.asyncio
async def test_vision_scan(populated_router):
    router, _, vision = populated_router
    req = JarvisRequest(
        id="req_4",
        type="vision.scan",
        version=PROTOCOL_VERSION,
        timestamp="2026-09-15T00:00:00Z",
        payload={"monitor_index": 0},
    )
    res = await router.dispatch(req)
    assert res.success is True
    assert res.payload["observation_id"] == "obs_test_001"
    assert res.payload["resolution"]["width"] == 2560
    assert res.payload["resolution"]["height"] == 1440
    assert len(res.payload["elements"]) == 1
    assert res.payload["elements"][0]["label"] == "Submit"
    vision.capture_and_analyze.assert_awaited_once_with(monitor_index=0)


@pytest.mark.asyncio
async def test_vision_scan_fallback(empty_registry):
    router = IPCRouter()
    empty_registry.register_handlers(router)
    req = JarvisRequest(
        id="req_5",
        type="vision.scan",
        version=PROTOCOL_VERSION,
        timestamp="2026-09-15T00:00:00Z",
        payload={"monitor_index": 1},
    )
    res = await router.dispatch(req)
    assert res.success is True
    assert res.payload["monitor_index"] == 1
    assert res.payload["interactive_count"] == 3


@pytest.mark.asyncio
async def test_voice_interact_fallback(empty_registry):
    router = IPCRouter()
    empty_registry.register_handlers(router)
    req = JarvisRequest(
        id="req_6",
        type="voice.interact",
        version=PROTOCOL_VERSION,
        timestamp="2026-09-15T00:00:00Z",
        payload={"text": "Hello ZARVIS"},
    )
    res = await router.dispatch(req)
    assert res.success is True
    assert res.payload["status"] == "ready"


@pytest.mark.asyncio
async def test_tools_list_fallback(empty_registry):
    router = IPCRouter()
    empty_registry.register_handlers(router)
    req = JarvisRequest(
        id="req_7",
        type="tools.list",
        version=PROTOCOL_VERSION,
        timestamp="2026-09-15T00:00:00Z",
        payload={},
    )
    res = await router.dispatch(req)
    assert res.success is True
    assert len(res.payload["tools"]) >= 4


@pytest.mark.asyncio
async def test_voice_stop(empty_registry):
    router = IPCRouter()
    empty_registry.register_handlers(router)
    req = JarvisRequest(
        id="req_8",
        type="voice.stop",
        version=PROTOCOL_VERSION,
        timestamp="2026-09-15T00:00:00Z",
        payload={},
    )
    res = await router.dispatch(req)
    assert res.success is True
    assert res.payload["stopped"] is True
    assert res.payload["status"] == "idle"

