"""Unit tests for Phase 09 Vision data models."""

import time
import pytest
from jarvis.vision.errors import InvalidBoundingBoxError
from jarvis.vision.models import (
    BoundingBox,
    ConfidenceLevel,
    ElementType,
    GroundingCandidate,
    GroundingResult,
    RegionType,
    ScreenObservation,
    ScreenRegion,
    VisionPoint,
    VisualElement,
)


def test_vision_point():
    p = VisionPoint(x=150, y=250)
    assert p.x == 150
    assert p.y == 250
    assert p.to_tuple() == (150, 250)
    assert p.to_dict() == {"x": 150, "y": 250}


def test_bounding_box_geometry():
    box = BoundingBox(x=100, y=200, width=50, height=30)
    assert box.left == 100
    assert box.top == 200
    assert box.right == 150
    assert box.bottom == 230
    assert box.area == 1500
    assert box.center.x == 125
    assert box.center.y == 215

    # Point containment
    assert box.contains(VisionPoint(x=125, y=215))
    assert box.contains(VisionPoint(x=100, y=200))  # boundary
    assert not box.contains(VisionPoint(x=99, y=200))
    assert not box.contains(VisionPoint(x=151, y=200))


def test_bounding_box_validation():
    with pytest.raises(InvalidBoundingBoxError):
        BoundingBox(x=0, y=0, width=-10, height=50)

    with pytest.raises(InvalidBoundingBoxError):
        BoundingBox(x=0, y=0, width=50, height=-5)


def test_bounding_box_intersection_and_iou():
    box1 = BoundingBox(x=0, y=0, width=100, height=100)
    box2 = BoundingBox(x=50, y=50, width=100, height=100)
    box3 = BoundingBox(x=200, y=200, width=50, height=50)

    assert box1.intersects(box2)
    assert not box1.intersects(box3)

    inter = box1.intersection(box2)
    assert inter is not None
    assert inter.x == 50
    assert inter.y == 50
    assert inter.width == 50
    assert inter.height == 50
    assert inter.area == 2500

    assert box1.intersection(box3) is None

    # IoU
    # union area = 10000 + 10000 - 2500 = 17500
    # iou = 2500 / 17500 = 1/7 ~= 0.142857
    iou = box1.iou(box2)
    assert abs(iou - (1 / 7)) < 0.001
    assert box1.iou(box3) == 0.0


def test_visual_element_properties():
    box = BoundingBox(x=50, y=100, width=80, height=40)
    el = VisualElement(
        element_id="elem_1",
        element_type=ElementType.BUTTON,
        bounds=box,
        label="Submit",
        ocr_text="SUBMIT",
        confidence=0.95,
    )
    assert el.center.x == 90
    assert el.center.y == 120
    assert el.display_text == "Submit"
    summary = el.to_summary()
    assert summary["element_id"] == "elem_1"
    assert summary["element_type"] == "button"
    assert summary["confidence"] == 0.95


def test_screen_region():
    box = BoundingBox(x=0, y=0, width=500, height=500)
    reg = ScreenRegion(
        region_id="reg_1",
        region_type=RegionType.WINDOW,
        bounds=box,
        title="App Window",
        element_ids=["elem_1", "elem_2"],
    )
    assert reg.region_type == RegionType.WINDOW
    summary = reg.to_summary()
    assert summary["region_id"] == "reg_1"
    assert summary["element_count"] == 2


def test_screen_observation():
    now = time.time()
    el1 = VisualElement(
        element_id="e1",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=10, y=10, width=20, height=20),
        parent_region_id="r1",
    )
    reg1 = ScreenRegion(
        region_id="r1",
        region_type=RegionType.WINDOW,
        bounds=BoundingBox(x=0, y=0, width=100, height=100),
        element_ids=["e1"],
    )

    obs = ScreenObservation(
        observation_id="obs_1",
        timestamp=now - 5.0,
        elements=[el1],
        regions=[reg1],
        image_width=1920,
        image_height=1080,
    )

    assert obs.age(current_time=now) >= 5.0
    assert not obs.check_staleness(ttl_sec=10.0, current_time=now)
    assert obs.check_staleness(ttl_sec=3.0, current_time=now)
    assert obs.is_stale

    assert obs.find_by_id("e1") == el1
    assert obs.find_by_id("missing") is None

    matches = obs.find_at_point(VisionPoint(x=15, y=15))
    assert len(matches) == 1
    assert matches[0].element_id == "e1"

    region_elements = obs.find_in_region("r1")
    assert len(region_elements) == 1
    assert region_elements[0].element_id == "e1"


def test_grounding_result():
    el = VisualElement(
        element_id="btn_1",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=100, y=200, width=50, height=30),
        label="Click Me",
    )
    candidate = GroundingCandidate(element=el, score=0.92, match_reason="High similarity")
    res = GroundingResult(
        query="click me",
        element=el,
        target_point=VisionPoint(x=125, y=215),
        confidence=0.92,
        confidence_level=ConfidenceLevel.HIGH,
        observation_id="obs_1",
        candidates=[candidate],
        suggested_action="click",
    )
    d = res.to_dict()
    assert d["query"] == "click me"
    assert d["confidence"] == 0.92
    assert d["confidence_level"] == "high"
    assert d["target_point"] == {"x": 125, "y": 215}
    assert d["suggested_action"] == "click"
