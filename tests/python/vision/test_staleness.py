"""Unit tests for observation TTL and staleness validation."""

import time
import pytest
from jarvis.vision.config import VisionConfig
from jarvis.vision.errors import StaleObservationError
from jarvis.vision.grounding.resolver import TargetResolver
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    ScreenObservation,
    VisualElement,
)


def test_staleness_rejection():
    config = VisionConfig(observation_ttl_sec=10.0)
    resolver = TargetResolver(config=config)

    now = time.time()
    # Observation created 15 seconds ago (> 10s TTL)
    stale_time = now - 15.0

    btn = VisualElement(
        element_id="btn_ok",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=10, y=10, width=50, height=20),
        label="OK",
    )
    obs = ScreenObservation(
        timestamp=stale_time,
        elements=[btn],
        image_width=1920,
        image_height=1080,
    )

    with pytest.raises(StaleObservationError) as exc_info:
        resolver.resolve(query="OK", observation=obs, current_time=now)

    err = exc_info.value
    assert err.ttl_sec == 10.0
    assert err.age_sec >= 15.0


def test_fresh_observation_succeeds():
    config = VisionConfig(observation_ttl_sec=10.0)
    resolver = TargetResolver(config=config)

    now = time.time()
    fresh_time = now - 2.0

    btn = VisualElement(
        element_id="btn_ok",
        element_type=ElementType.BUTTON,
        bounds=BoundingBox(x=10, y=10, width=50, height=20),
        label="OK",
    )
    obs = ScreenObservation(
        timestamp=fresh_time,
        elements=[btn],
        image_width=1920,
        image_height=1080,
    )

    result = resolver.resolve(query="OK", observation=obs, current_time=now)
    assert result.element.element_id == "btn_ok"
