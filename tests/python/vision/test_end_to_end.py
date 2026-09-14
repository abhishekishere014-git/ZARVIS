"""End-to-end integration tests for Phase 09 Vision Grounding."""

import pytest
from jarvis.os.manager import OSAutomationManager
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.tools.keyboard_tools import keyboard_type
from jarvis.os.tools.mouse_tools import mouse_click
from jarvis.os.tools.registration import register_os_tools
from jarvis.tools.registry import ToolRegistry
from jarvis.vision.manager import VisionManager
from jarvis.vision.providers.mock import MockVisionProvider
from jarvis.vision.tools.registration import register_vision_tools
from jarvis.vision.tools.screen_analyze import screen_analyze
from jarvis.vision.tools.target_resolve import target_resolve


@pytest.mark.asyncio
async def test_full_user_search_workflow():
    registry = ToolRegistry()

    # Wire up OS automation
    os_provider = MockOSProvider()
    os_mgr = OSAutomationManager(provider=os_provider)
    register_os_tools(registry, os_manager=os_mgr)

    # Wire up Vision
    vision_provider = MockVisionProvider()
    vision_mgr = VisionManager(provider=vision_provider)
    register_vision_tools(registry, vision_manager=vision_mgr)

    # 1. Analyze screen
    analyze_res = await screen_analyze(monitor_id=0, force_refresh=True)
    assert analyze_res["success"] is True
    assert analyze_res["element_count"] > 0

    # 2. Resolve "Search Box"
    resolve_inp = await target_resolve(query="Search Box", monitor_id=0)
    assert resolve_inp["success"] is True
    assert resolve_inp["suggested_action"] == "type"

    # 3. Focus search box and type
    await mouse_click(x=resolve_inp["target_point"]["x"], y=resolve_inp["target_point"]["y"])
    type_res = await keyboard_type(text="Autonomous AI Agents")
    assert type_res["typed"] is True

    # 4. Resolve "Google Search" button
    resolve_btn = await target_resolve(query="Google Search", monitor_id=0)
    assert resolve_btn["success"] is True
    assert resolve_btn["suggested_action"] == "click"

    # 5. Click the button
    click_res = await mouse_click(x=resolve_btn["target_point"]["x"], y=resolve_btn["target_point"]["y"])
    assert click_res["clicked"] is True


@pytest.mark.asyncio
async def test_multi_monitor_grounding_workflow():
    registry = ToolRegistry()
    vision_provider = MockVisionProvider()
    vision_mgr = VisionManager(provider=vision_provider)
    register_vision_tools(registry, vision_manager=vision_mgr)

    # Resolve target on monitor 1 (offset x >= 1920)
    res = await target_resolve(query="Google Search", monitor_id=1, force_refresh=True)
    assert res["success"] is True
    assert res["target_point"]["x"] >= 1920
