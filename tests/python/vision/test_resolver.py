"""Unit tests for TargetResolver query execution and coordinate calculation."""

import pytest
from jarvis.vision.errors import ElementNotFoundError
from jarvis.vision.grounding.resolver import TargetResolver
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    ScreenObservation,
    VisualElement,
)


def test_resolver_basic_flow():
    resolver = TargetResolver()

    btn = VisualElement(
        element_id="btn_search",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=500, y=300, width=120, height=40),
        label="Search",
        is_clickable=True,
    )
    obs = ScreenObservation(
        elements=[btn],
        image_width=1920,
        image_height=1080,
    )

    result = resolver.resolve("search button", obs)
    assert result.element.element_id == "btn_search"
    assert result.target_point.x == 560  # 500 + 120//2
    assert result.target_point.y == 320  # 300 + 40//2
    assert result.confidence >= 0.85
    assert result.suggested_action == "click"


def test_resolver_type_action():
    resolver = TargetResolver()

    inp = VisualElement(
        element_id="inp_query",
        element_type=ElementType.INPUT_TEXT,
        bounds=BoundingBox(x=300, y=200, width=400, height=35),
        label="Search query",
        is_clickable=True,
    )
    obs = ScreenObservation(
        elements=[inp],
        image_width=1920,
        image_height=1080,
    )

    result = resolver.resolve("search query", obs)
    assert result.suggested_action == "type"


def test_resolver_element_not_found():
    resolver = TargetResolver()
    btn = VisualElement(
        element_id="btn_cancel",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=10, y=10, width=50, height=20),
        label="Cancel",
    )
    obs = ScreenObservation(
        elements=[btn],
        image_width=1920,
        image_height=1080,
    )

    with pytest.raises(ElementNotFoundError):
        resolver.resolve("Submit Order Now", obs)

    # Filtering by type when none match raises ElementNotFoundError
    with pytest.raises(ElementNotFoundError):
        resolver.resolve("Cancel", obs, element_type=ElementType.INPUT_TEXT)
