"""Unit tests for target ambiguity detection and resolution."""

import pytest
from jarvis.vision.errors import TargetAmbiguityError
from jarvis.vision.grounding.resolver import TargetResolver
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    RegionType,
    ScreenObservation,
    ScreenRegion,
    VisualElement,
)


def test_target_ambiguity_raises_error():
    resolver = TargetResolver()

    # Two identical submit buttons
    btn1 = VisualElement(
        element_id="btn_submit_top",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=100, y=100, width=80, height=30),
        label="Submit",
        confidence=0.95,
        parent_region_id="reg_form_1",
    )
    btn2 = VisualElement(
        element_id="btn_submit_bottom",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=100, y=500, width=80, height=30),
        label="Submit",
        confidence=0.95,
        parent_region_id="reg_form_2",
    )

    obs = ScreenObservation(
        elements=[btn1, btn2],
        image_width=1920,
        image_height=1080,
    )

    # When ambiguous, raises TargetAmbiguityError by default
    with pytest.raises(TargetAmbiguityError) as exc_info:
        resolver.resolve("Submit", obs, allow_ambiguous=False)

    err = exc_info.value
    assert err.query == "Submit"
    assert err.details["candidate_count"] >= 2
    assert len(err.candidates) >= 2


def test_target_ambiguity_allowed_flag():
    resolver = TargetResolver()

    btn1 = VisualElement(
        element_id="btn_submit_top",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=100, y=100, width=80, height=30),
        label="Submit",
        confidence=0.95,
    )
    btn2 = VisualElement(
        element_id="btn_submit_bottom",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=100, y=500, width=80, height=30),
        label="Submit",
        confidence=0.95,
    )

    obs = ScreenObservation(
        elements=[btn1, btn2],
        image_width=1920,
        image_height=1080,
    )

    # When allow_ambiguous=True, does not raise, flags is_ambiguous=True
    result = resolver.resolve("Submit", obs, allow_ambiguous=True)
    assert result.is_ambiguous is True
    assert result.element.element_id in ["btn_submit_top", "btn_submit_bottom"]


def test_target_ambiguity_disambiguated_by_region():
    resolver = TargetResolver()

    btn1 = VisualElement(
        element_id="btn_submit_header",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=100, y=50, width=80, height=30),
        label="Submit",
        parent_region_id="reg_header",
    )
    btn2 = VisualElement(
        element_id="btn_submit_footer",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=100, y=900, width=80, height=30),
        label="Submit",
        parent_region_id="reg_footer",
    )

    reg_header = ScreenRegion(
        region_id="reg_header",
        region_type=RegionType.TOOLBAR,
        bounds=BoundingBox(x=0, y=0, width=1920, height=100),
        element_ids=["btn_submit_header"],
    )
    reg_footer = ScreenRegion(
        region_id="reg_footer",
        region_type=RegionType.TOOLBAR,
        bounds=BoundingBox(x=0, y=850, width=1920, height=150),
        element_ids=["btn_submit_footer"],
    )

    obs = ScreenObservation(
        elements=[btn1, btn2],
        regions=[reg_header, reg_footer],
        image_width=1920,
        image_height=1080,
    )

    # Scoping search to reg_footer eliminates ambiguity cleanly
    res = resolver.resolve("Submit", obs, region_id="reg_footer")
    assert res.element.element_id == "btn_submit_footer"
    assert res.is_ambiguous is False
