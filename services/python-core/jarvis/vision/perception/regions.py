"""Screen region management and spatial hierarchy utilities for Phase 09."""

from __future__ import annotations

from typing import Iterable, List, Optional

from jarvis.vision.models import (
    BoundingBox,
    RegionType,
    ScreenRegion,
    VisionPoint,
    VisualElement,
)


def find_enclosing_region(
    regions: Iterable[ScreenRegion], point: VisionPoint
) -> Optional[ScreenRegion]:
    """Find the smallest (innermost) region enclosing the given point."""
    enclosing = [r for r in regions if r.bounds.contains(point)]
    if not enclosing:
        return None
    # Sort smallest area first
    enclosing.sort(key=lambda r: r.bounds.area)
    return enclosing[0]


def assign_elements_to_regions(
    elements: List[VisualElement], regions: List[ScreenRegion]
) -> None:
    """Link visual elements to their innermost enclosing region."""
    for el in elements:
        enclosing = find_enclosing_region(regions, el.center)
        if enclosing:
            el.parent_region_id = enclosing.region_id
            if el.element_id not in enclosing.element_ids:
                enclosing.element_ids.append(el.element_id)
            if enclosing.is_sensitive:
                el.is_sensitive = True


def get_focused_region(regions: Iterable[ScreenRegion]) -> Optional[ScreenRegion]:
    """Return the currently focused region if any."""
    for r in regions:
        if r.is_focused:
            return r
    return None
