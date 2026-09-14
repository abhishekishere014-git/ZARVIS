"""Integration tests between Phase 09 Vision Grounding and Phase 08 OS Automation."""

import pytest
from jarvis.os.manager import OSAutomationManager
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.tools.keyboard_tools import keyboard_type
from jarvis.os.tools.mouse_tools import mouse_click, mouse_move
from jarvis.os.tools.registration import register_os_tools
from jarvis.tools.registry import ToolRegistry
from jarvis.vision.manager import VisionManager
from jarvis.vision.providers.mock import MockVisionProvider
from jarvis.vision.tools.registration import register_vision_tools
from jarvis.vision.tools.target_resolve import target_resolve


@pytest.fixture
def integrated_env():
    registry = ToolRegistry()

    # OS Automation setup
    os_provider = MockOSProvider()
    os_mgr = OSAutomationManager(provider=os_provider)
    register_os_tools(registry, os_manager=os_mgr)

    # Vision setup
    vision_provider = MockVisionProvider()
    vision_mgr = VisionManager(provider=vision_provider)
    register_vision_tools(registry, vision_manager=vision_mgr)

    return registry, os_mgr, vision_mgr


@pytest.mark.asyncio
async def test_vision_grounding_to_mouse_click(integrated_env):
    registry, os_mgr, vision_mgr = integrated_env

    # 1. Resolve target via Vision
    res = await target_resolve(query="Google Search", monitor_id=0)
    assert res["success"] is True
    target_x = res["target_point"]["x"]
    target_y = res["target_point"]["y"]

    # 2. Feed coordinates into OS mouse click
    click_res = await mouse_click(x=target_x, y=target_y)
    assert click_res["clicked"] is True
    assert click_res["position"] == (target_x, target_y)


@pytest.mark.asyncio
async def test_vision_grounding_to_keyboard_type(integrated_env):
    registry, os_mgr, vision_mgr = integrated_env

    # 1. Resolve text input field
    res = await target_resolve(query="Address Bar", monitor_id=0)
    assert res["success"] is True
    target_x = res["target_point"]["x"]
    target_y = res["target_point"]["y"]

    # 2. Click to focus
    await mouse_click(x=target_x, y=target_y)

    # 3. Type text into focused input
    type_res = await keyboard_type(text="https://github.com")
    assert type_res["typed"] is True
    assert type_res["chars_count"] == len("https://github.com")
