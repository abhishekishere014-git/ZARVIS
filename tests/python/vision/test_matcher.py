"""Unit tests for semantic element matching engine."""

from jarvis.vision.grounding.matcher import ElementMatcher
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    VisualElement,
)


def test_element_matcher_exact_and_fuzzy():
    matcher = ElementMatcher()

    btn1 = VisualElement(
        element_id="btn_search",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=10, y=10, width=50, height=30),
        label="Google Search",
    )
    btn2 = VisualElement(
        element_id="btn_cancel",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=70, y=10, width=50, height=30),
        label="Cancel",
    )

    candidates = matcher.match("Google Search", [btn1, btn2])
    assert len(candidates) >= 1
    assert candidates[0].element.element_id == "btn_search"
    assert candidates[0].score >= 0.85


def test_element_matcher_type_hints():
    matcher = ElementMatcher()

    # Query mentions "input"
    input_box = VisualElement(
        element_id="inp_user",
        element_type=ElementType.INPUT_TEXT,
        bounds=BoundingBox(x=10, y=10, width=100, height=30),
        label="Username",
        placeholder="Enter user name",
    )
    label_text = VisualElement(
        element_id="txt_user",
        element_type=ElementType.TEXT,
        bounds=BoundingBox(x=10, y=50, width=100, height=20),
        label="Username",
    )

    candidates = matcher.match("username input box", [input_box, label_text])
    assert len(candidates) > 0
    # Input element should be ranked higher due to type hint match
    assert candidates[0].element.element_id == "inp_user"


def test_element_matcher_clickable_bonus():
    matcher = ElementMatcher()

    btn = VisualElement(
        element_id="btn_save",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=10, y=10, width=50, height=30),
        label="Save Document",
        is_clickable=True,
    )
    txt = VisualElement(
        element_id="txt_save",
        element_type=ElementType.TEXT,
        bounds=BoundingBox(x=10, y=50, width=50, height=30),
        label="Save Document",
        is_clickable=False,
    )

    candidates = matcher.match("click save document", [btn, txt])
    assert len(candidates) > 0
    assert candidates[0].element.element_id == "btn_save"
    assert candidates[0].score > candidates[1].score


def test_element_matcher_no_match():
    matcher = ElementMatcher()
    btn = VisualElement(
        element_id="btn_ok",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=0, y=0, width=20, height=20),
        label="OK",
    )
    candidates = matcher.match("nonexistent element xyz123", [btn])
    assert len(candidates) == 0
