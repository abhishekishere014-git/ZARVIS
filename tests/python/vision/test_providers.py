"""Unit tests for Vision providers in Phase 09."""

import pytest
from jarvis.vision.errors import VisionProviderError
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    VisualElement,
)
from jarvis.vision.providers.mock import MockVisionProvider


@pytest.mark.asyncio
async def test_mock_provider_default_desktop():
    provider = MockVisionProvider()
    obs = await provider.analyze_screen(
        screenshot_path="dummy.png",
        screen_width=1920,
        screen_height=1080,
        monitor_index=0,
    )
    assert obs.image_width == 1920
    assert obs.image_height == 1080
    assert obs.monitor_index == 0
    assert len(obs.elements) > 0
    assert len(obs.regions) > 0
    assert obs.active_window_title == "Google Chrome - Search"

    # Verify standard elements exist
    labels = [el.label for el in obs.elements]
    assert "Google Search" in labels
    assert "Address Bar" in labels
    assert "Settings" in labels


@pytest.mark.asyncio
async def test_mock_provider_multi_monitor():
    provider = MockVisionProvider()
    obs1 = await provider.analyze_screen(
        screenshot_path="dummy.png",
        screen_width=1920,
        screen_height=1080,
        monitor_index=1,
    )
    assert obs1.monitor_index == 1
    # Check elements on monitor 1 have shifted x coordinates >= 1920
    for el in obs1.elements:
        assert el.bounds.x >= 1920


@pytest.mark.asyncio
async def test_mock_provider_custom_elements():
    provider = MockVisionProvider()
    custom_el = VisualElement(
        element_id="custom_btn",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=10, y=10, width=50, height=20),
        label="Custom Action",
    )
    provider.add_element(custom_el)

    obs = await provider.analyze_screen("dummy.png", 1920, 1080, 0)
    found = [el for el in obs.elements if el.element_id == "custom_btn"]
    assert len(found) == 1
    assert found[0].label == "Custom Action"

    # Reset
    provider.reset()
    obs2 = await provider.analyze_screen("dummy.png", 1920, 1080, 0)
    found2 = [el for el in obs2.elements if el.element_id == "custom_btn"]
    assert len(found2) == 0


@pytest.mark.asyncio
async def test_mock_provider_failure_injection():
    provider = MockVisionProvider(simulate_failure=True)
    with pytest.raises(VisionProviderError) as exc_info:
        await provider.analyze_screen("dummy.png", 1920, 1080, 0)
    assert "Simulated vision provider failure" in str(exc_info.value)

    assert await provider.health_check() is False
