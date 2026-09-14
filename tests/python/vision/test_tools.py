"""Unit tests for Phase 09 Vision tools registered with ToolRegistry."""

import pytest
from jarvis.tools.models import ToolPermission
from jarvis.tools.registry import ToolRegistry
from jarvis.vision.manager import VisionManager
from jarvis.vision.providers.mock import MockVisionProvider
from jarvis.vision.tools.element_find import element_find
from jarvis.vision.tools.registration import register_vision_tools
from jarvis.vision.tools.screen_analyze import screen_analyze
from jarvis.vision.tools.target_resolve import target_resolve


@pytest.fixture
def test_vision_env():
    registry = ToolRegistry()
    provider = MockVisionProvider()
    mgr = VisionManager(provider=provider)
    registered_ids = register_vision_tools(registry, vision_manager=mgr)
    return registry, mgr, registered_ids


def test_tool_registration(test_vision_env):
    registry, mgr, registered_ids = test_vision_env

    assert "vision.screen.analyze" in registered_ids
    assert "vision.element.find" in registered_ids
    assert "vision.target.resolve" in registered_ids

    # Verify tool definitions
    analyze_tool = registry.get("vision.screen.analyze")
    assert analyze_tool is not None
    assert analyze_tool.category == "vision"
    assert ToolPermission.READ in analyze_tool.permissions


@pytest.mark.asyncio
async def test_screen_analyze_tool(test_vision_env):
    registry, mgr, _ = test_vision_env

    res = await screen_analyze(monitor_id=0, force_refresh=True)
    assert res["success"] is True
    assert "observation_id" in res
    assert res["element_count"] > 0
    assert res["region_count"] > 0
    assert len(res["elements"]) == res["element_count"]

    # Verify password was sanitized in output
    for el in res["elements"]:
        if el["element_type"] == "input_password":
            assert el["ocr_text"] == "********"


@pytest.mark.asyncio
async def test_element_find_tool(test_vision_env):
    registry, mgr, _ = test_vision_env

    res = await element_find(query="Google Search", monitor_id=0)
    assert res["success"] is True
    assert res["match_count"] >= 1
    assert any(el["label"] == "Google Search" for el in res["elements"])


@pytest.mark.asyncio
async def test_target_resolve_tool(test_vision_env):
    registry, mgr, _ = test_vision_env

    res = await target_resolve(query="Google Search", monitor_id=0)
    assert res["success"] is True
    assert res["query"] == "Google Search"
    assert "target_point" in res
    assert "x" in res["target_point"]
    assert "y" in res["target_point"]
    assert res["confidence"] >= 0.85
    assert res["suggested_action"] == "click"
