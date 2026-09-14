"""Unit tests for confidence scoring and rejection thresholds."""

import pytest
from jarvis.vision.errors import ConfidenceRejectedError
from jarvis.vision.grounding.confidence import (
    calculate_text_similarity,
    categorize_confidence,
)
from jarvis.vision.grounding.resolver import TargetResolver
from jarvis.vision.models import (
    BoundingBox,
    ConfidenceLevel,
    ElementType,
    ScreenObservation,
    VisualElement,
)


def test_calculate_text_similarity():
    # Exact
    assert calculate_text_similarity("submit", "submit") == 1.0
    # Case insensitive
    assert calculate_text_similarity("SUBMIT", "submit") == 1.0
    # Substring
    sim_sub = calculate_text_similarity("search", "google search")
    assert 0.80 <= sim_sub <= 0.95
    # Token overlap
    sim_tokens = calculate_text_similarity("save file document", "save file")
    assert sim_tokens >= 0.70
    # Empty
    assert calculate_text_similarity("", "test") == 0.0
    assert calculate_text_similarity("test", "") == 0.0


def test_categorize_confidence():
    assert categorize_confidence(0.95) == ConfidenceLevel.HIGH
    assert categorize_confidence(0.85) == ConfidenceLevel.HIGH
    assert categorize_confidence(0.84) == ConfidenceLevel.MEDIUM
    assert categorize_confidence(0.60) == ConfidenceLevel.MEDIUM
    assert categorize_confidence(0.59) == ConfidenceLevel.LOW
    assert categorize_confidence(0.10) == ConfidenceLevel.LOW


def test_confidence_rejection_error():
    resolver = TargetResolver()

    el = VisualElement(
        element_id="btn_random",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=10, y=10, width=50, height=20),
        label="Upload File",
        confidence=0.7,
    )
    obs = ScreenObservation(
        elements=[el],
        image_width=1920,
        image_height=1080,
    )

    # Looking for "Upload" against "Download" yields low confidence
    with pytest.raises(ConfidenceRejectedError) as exc_info:
        resolver.resolve(query="Upload", observation=obs, min_confidence=0.85)

    err = exc_info.value
    assert err.query == "Upload"
    assert err.threshold == 0.85
    assert err.confidence < 0.85
