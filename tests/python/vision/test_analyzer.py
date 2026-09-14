"""Unit tests for perception analyzer and spatial hierarchy."""

import pytest
from jarvis.vision.config import VisionConfig
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    RegionType,
    ScreenRegion,
    VisionPoint,
    VisualElement,
)
from jarvis.vision.perception.analyzer import ScreenAnalyzer
from jarvis.vision.perception.elements import (
    filter_elements,
    find_elements_at_point,
    find_elements_in_bounds,
)
from jarvis.vision.perception.regions import assign_elements_to_regions, find_enclosing_region
from jarvis.vision.providers.mock import MockVisionProvider
from jarvis.vision.security import VisionSecurityManager


@pytest.mark.asyncio
async def test_screen_analyzer_pipeline():
    provider = MockVisionProvider()
    config = VisionConfig(max_elements=15)
    sec_mgr = VisionSecurityManager(config)
    analyzer = ScreenAnalyzer(provider=provider, config=config, security_manager=sec_mgr)

    obs = await analyzer.analyze("screen.png", 1920, 1080, 0)
    assert len(obs.elements) <= 15
    assert len(obs.regions) > 0

    # Verify sensitive elements were detected
    sensitive_elements = [el for el in obs.elements if el.is_sensitive]
    assert len(sensitive_elements) > 0
    assert any(el.element_type == ElementType.INPUT_PASSWORD for el in sensitive_elements)

    # Verify parent region assignment
    assigned_count = sum(1 for el in obs.elements if el.parent_region_id is not None)
    assert assigned_count > 0


def test_spatial_filtering_utilities():
    el1 = VisualElement(
        element_id="e1",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=10, y=10, width=50, height=30),
        is_clickable=True,
    )
    el2 = VisualElement(
        element_id="e2",
        element_type=ElementType.TEXT,
        bounds=BoundingBox(x=100, y=100, width=80, height=20),
        is_clickable=False,
    )
    el3 = VisualElement(
        element_id="e3",
        element_type=ElementType.INPUT_PASSWORD,
        bounds=BoundingBox(x=10, y=100, width=100, height=30),
        is_sensitive=True,
    )

    elements = [el1, el2, el3]

    # Filter by clickable
    clickable = filter_elements(elements, clickable_only=True)
    assert len(clickable) == 2  # el1 and el3 are clickable by default

    # Filter non-sensitive
    safe = filter_elements(elements, non_sensitive_only=True)
    assert len(safe) == 2
    assert el3 not in safe

    # Filter by type
    buttons = filter_elements(elements, element_type=ElementType.BUTTON)
    assert len(buttons) == 1
    assert buttons[0] == el1

    # Find at point
    found = find_elements_at_point(elements, VisionPoint(x=20, y=20))
    assert len(found) == 1
    assert found[0] == el1

    # Find in bounds
    container = BoundingBox(x=0, y=0, width=70, height=50)
    contained = find_elements_in_bounds(elements, container)
    assert len(contained) == 1
    assert contained[0] == el1


def test_region_enclosure_and_assignment():
    reg1 = ScreenRegion(
        region_id="outer",
        region_type=RegionType.WINDOW,
        bounds=BoundingBox(x=0, y=0, width=500, height=500),
    )
    reg2 = ScreenRegion(
        region_id="inner",
        region_type=RegionType.FORM,
        bounds=BoundingBox(x=100, y=100, width=200, height=200),
    )
    regions = [reg1, reg2]

    # Point inside inner region should select the innermost (smallest area)
    enclosing = find_enclosing_region(regions, VisionPoint(x=150, y=150))
    assert enclosing is not None
    assert enclosing.region_id == "inner"

    # Point inside outer but outside inner
    enclosing_outer = find_enclosing_region(regions, VisionPoint(x=50, y=50))
    assert enclosing_outer is not None
    assert enclosing_outer.region_id == "outer"

    # Assign elements
    el = VisualElement(
        element_id="btn_form",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=120, y=120, width=40, height=20),
    )
    assign_elements_to_regions([el], regions)
    assert el.parent_region_id == "inner"
    assert "btn_form" in reg2.element_ids
