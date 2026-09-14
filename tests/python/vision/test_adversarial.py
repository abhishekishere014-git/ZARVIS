"""Adversarial and boundary tests for Phase 09 Vision Subsystem."""

import pytest
from jarvis.vision.errors import ElementNotFoundError, InvalidBoundingBoxError, VisionError
from jarvis.vision.grounding.resolver import TargetResolver
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    ScreenObservation,
    VisionPoint,
    VisualElement,
)
from jarvis.vision.security import VisionSecurityManager


def test_adversarial_prompt_injection_in_query():
    resolver = TargetResolver()

    btn = VisualElement(
        element_id="btn_normal",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=10, y=10, width=50, height=20),
        label="Download",
    )
    obs = ScreenObservation(elements=[btn], image_width=1920, image_height=1080)

    # Injection queries should simply be evaluated as text strings without code execution
    injection_queries = [
        "'; DROP TABLE users; --",
        "<script>alert(1)</script>",
        "__import__('os').system('calc')",
        "`rm -rf /`",
        "$(whoami)",
        "Download && notepad.exe",
    ]

    for q in injection_queries:
        try:
            res = resolver.resolve(q, obs)
            # If it matched "Download" due to substring token, it must be safe
            assert isinstance(res.target_point, VisionPoint)
        except ElementNotFoundError:
            pass  # Normal expected behavior if no match


def test_inverted_and_negative_bounding_boxes():
    with pytest.raises(InvalidBoundingBoxError):
        BoundingBox(x=0, y=0, width=-100, height=50)

    with pytest.raises(InvalidBoundingBoxError):
        BoundingBox(x=10, y=10, width=50, height=-20)


def test_empty_observation():
    resolver = TargetResolver()
    obs = ScreenObservation(elements=[], image_width=1920, image_height=1080)

    with pytest.raises(ElementNotFoundError):
        resolver.resolve("Click me", obs)


def test_security_coordinate_adversarial_bounds():
    sec_mgr = VisionSecurityManager()
    bounds = BoundingBox(x=0, y=0, width=1920, height=1080)

    # Intentionally overflow coordinates
    with pytest.raises(VisionError):
        sec_mgr.validate_coordinates(VisionPoint(x=999999, y=999999), bounds)

    with pytest.raises(VisionError):
        sec_mgr.validate_coordinates(VisionPoint(x=-1, y=-1), bounds)
