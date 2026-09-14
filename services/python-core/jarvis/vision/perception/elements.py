"""Element extraction and spatial filtering utilities for Phase 09."""

from __future__ import annotations

from typing import Callable, Iterable, List, Optional

from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    VisionPoint,
    VisualElement,
)


def filter_elements(
    elements: Iterable[VisualElement],
    element_type: Optional[ElementType] = None,
    clickable_only: bool = False,
    non_sensitive_only: bool = False,
    predicate: Optional[Callable[[VisualElement], bool]] = None,
) -> List[VisualElement]:
    """Filter elements according to criteria."""
    filtered = []
    for el in elements:
        if element_type is not None and el.element_type != element_type:
            continue
        if clickable_only and not el.is_clickable:
            continue
        if non_sensitive_only and el.is_sensitive:
            continue
        if predicate is not None and not predicate(el):
            continue
        filtered.append(el)
    return filtered


def find_elements_at_point(
    elements: Iterable[VisualElement], point: VisionPoint
) -> List[VisualElement]:
    """Find all elements whose bounding box covers the given point, sorted by smallest area first."""
    matches = [el for el in elements if el.bounds.contains(point)]
    # Sort smallest area first (deepest element in visual hierarchy)
    matches.sort(key=lambda el: el.bounds.area)
    return matches


def find_elements_in_bounds(
    elements: Iterable[VisualElement], bounds: BoundingBox
) -> List[VisualElement]:
    """Find all elements completely contained within bounds."""
    return [
        el
        for el in elements
        if (
            el.bounds.left >= bounds.left
            and el.bounds.right <= bounds.right
            and el.bounds.top >= bounds.top
            and el.bounds.bottom <= bounds.bottom
        )
    ]
