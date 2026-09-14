"""Performance benchmarks for Phase 09 Vision Grounding."""

import time
import pytest
from jarvis.vision.grounding.resolver import TargetResolver
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    ScreenObservation,
    VisualElement,
)


def test_target_resolution_latency_200_elements():
    resolver = TargetResolver()

    # Generate 200 elements
    elements = []
    for i in range(200):
        el = VisualElement(
            element_id=f"el_{i}",
            element_type=ElementType.BUTTON if i % 2 == 0 else ElementType.TEXT,
            bounds=BoundingBox(x=(i * 10) % 1800, y=(i * 5) % 900, width=50, height=30),
            label=f"Action Button {i}" if i != 142 else "Target Special Action",
            confidence=0.9,
        )
        elements.append(el)

    obs = ScreenObservation(
        elements=elements,
        image_width=1920,
        image_height=1080,
    )

    start = time.perf_counter()
    result = resolver.resolve("Target Special Action", obs)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result.element.element_id == "el_142"
    # Latency should be well under 100ms
    assert elapsed_ms < 100.0, f"Resolution took {elapsed_ms:.2f}ms, expected < 100ms"
