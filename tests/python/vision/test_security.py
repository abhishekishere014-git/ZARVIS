"""Unit tests for Vision security, privacy scrubbing, and coordinate boundary validation."""

import pytest
from jarvis.vision.errors import VisionError
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    RegionType,
    ScreenObservation,
    ScreenRegion,
    VisionPoint,
    VisualElement,
)
from jarvis.vision.security import VisionSecurityManager


def test_sensitive_keyword_detection():
    sec_mgr = VisionSecurityManager()

    assert sec_mgr.is_text_sensitive("Enter your password") is True
    assert sec_mgr.is_text_sensitive("API_KEY: 12345") is True
    assert sec_mgr.is_text_sensitive("Your auth token") is True
    assert sec_mgr.is_text_sensitive("CVV code on back") is True
    assert sec_mgr.is_text_sensitive("Submit form") is False
    assert sec_mgr.is_text_sensitive(None) is False


def test_sensitive_element_detection_and_sanitization():
    sec_mgr = VisionSecurityManager()

    pwd_el = VisualElement(
        element_id="pwd_1",
        element_type=ElementType.INPUT_PASSWORD,
        bounds=BoundingBox(x=10, y=10, width=100, height=30),
        label="Password",
        ocr_text="SecretPass123!",
        placeholder="Enter password",
    )

    assert sec_mgr.detect_sensitive_element(pwd_el) is True

    sanitized = sec_mgr.sanitize_element(pwd_el)
    assert sanitized.is_sensitive is True
    assert sanitized.ocr_text == "********"
    assert "SecretPass123!" not in sanitized.ocr_text
    assert sanitized.placeholder == "********"


def test_observation_scrubbing():
    sec_mgr = VisionSecurityManager()

    pwd_el = VisualElement(
        element_id="pwd_1",
        element_type=ElementType.INPUT_PASSWORD,
        bounds=BoundingBox(x=10, y=10, width=100, height=30),
        ocr_text="my_api_key_xyz",
    )
    reg = ScreenRegion(
        region_id="r1",
        region_type=RegionType.FORM,
        bounds=BoundingBox(x=0, y=0, width=200, height=200),
        title="Account Password Reset",
    )
    obs = ScreenObservation(
        elements=[pwd_el],
        regions=[reg],
        active_window_title="Reset password dialog",
        raw_text="Please enter your secret password now",
        image_width=1920,
        image_height=1080,
    )

    clean_obs = sec_mgr.sanitize_observation(obs)
    assert clean_obs.elements[0].is_sensitive is True
    assert clean_obs.elements[0].ocr_text == "********"
    assert clean_obs.regions[0].title == "[REDACTED_REGION]"
    assert clean_obs.active_window_title == "[REDACTED_WINDOW]"
    assert "password" not in clean_obs.raw_text.lower()


def test_coordinate_validation():
    sec_mgr = VisionSecurityManager()
    bounds = BoundingBox(x=0, y=0, width=1920, height=1080)

    # Valid point inside
    sec_mgr.validate_coordinates(VisionPoint(x=100, y=100), bounds)

    # Negative coordinates
    with pytest.raises(VisionError):
        sec_mgr.validate_coordinates(VisionPoint(x=-5, y=50), bounds)

    # Outside screen boundaries
    with pytest.raises(VisionError):
        sec_mgr.validate_coordinates(VisionPoint(x=2000, y=500), bounds)
