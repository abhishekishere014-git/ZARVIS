"""Security and privacy controls for JARVIS Phase 09 Vision Subsystem."""

from __future__ import annotations

import re
from typing import Any, List, Optional

from jarvis.vision.config import VisionConfig
from jarvis.vision.errors import SensitiveRegionError, VisionError
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    ScreenObservation,
    ScreenRegion,
    VisionPoint,
    VisualElement,
)


class VisionSecurityManager:
    """Manages visual privacy, credential masking, and coordinate validation."""

    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or VisionConfig()
        # Compile regex pattern for sensitive keywords
        patterns = [re.escape(kw) for kw in self.config.sensitive_keywords]
        self._sensitive_regex = re.compile(r"\b(" + "|".join(patterns) + r")\b", re.IGNORECASE)

    def is_text_sensitive(self, text: Optional[str]) -> bool:
        """Check if any text string contains sensitive credential keywords."""
        if not text:
            return False
        return bool(self._sensitive_regex.search(text))

    def detect_sensitive_element(self, element: VisualElement) -> bool:
        """Evaluate if an element should be classified as sensitive."""
        if element.element_type == ElementType.INPUT_PASSWORD:
            return True
        if self.is_text_sensitive(element.label):
            return True
        if self.is_text_sensitive(element.ocr_text):
            return True
        if self.is_text_sensitive(element.placeholder):
            return True
        return False

    def sanitize_element(self, element: VisualElement) -> VisualElement:
        """Return a copy of element with sensitive content redacted for telemetry/logging."""
        if not element.is_sensitive and not self.detect_sensitive_element(element):
            return element

        copy_el = element.model_copy(deep=True)
        copy_el.is_sensitive = True
        if copy_el.element_type == ElementType.INPUT_PASSWORD:
            copy_el.label = "[PASSWORD FIELD]"
            copy_el.ocr_text = "********"
            copy_el.placeholder = "********"
        else:
            if self.is_text_sensitive(copy_el.label):
                copy_el.label = "[REDACTED_LABEL]"
            if self.is_text_sensitive(copy_el.ocr_text):
                copy_el.ocr_text = "[REDACTED_OCR]"
            if self.is_text_sensitive(copy_el.placeholder):
                copy_el.placeholder = "[REDACTED_PLACEHOLDER]"
        return copy_el

    def sanitize_observation(self, obs: ScreenObservation) -> ScreenObservation:
        """Return an observation with all sensitive elements/regions scrubbed."""
        sanitized_elements = [self.sanitize_element(el) for el in obs.elements]
        sanitized_regions = []
        for reg in obs.regions:
            r_copy = reg.model_copy(deep=True)
            if self.is_text_sensitive(r_copy.title):
                r_copy.title = "[REDACTED_REGION]"
                r_copy.is_sensitive = True
            sanitized_regions.append(r_copy)

        obs_copy = obs.model_copy(deep=True)
        obs_copy.elements = sanitized_elements
        obs_copy.regions = sanitized_regions
        if self.is_text_sensitive(obs_copy.active_window_title):
            obs_copy.active_window_title = "[REDACTED_WINDOW]"
        if obs_copy.raw_text:
            # Redact occurrences in raw OCR text
            obs_copy.raw_text = self._sensitive_regex.sub("[REDACTED]", obs_copy.raw_text)
        return obs_copy

    def validate_coordinates(
        self,
        point: VisionPoint,
        screen_bounds: Optional[BoundingBox] = None,
    ) -> None:
        """Validate that coordinates fall within virtual desktop boundaries."""
        if point.x < 0 or point.y < 0:
            raise VisionError(
                f"Coordinates ({point.x}, {point.y}) cannot be negative"
            )
        if screen_bounds:
            if not screen_bounds.contains(point):
                raise VisionError(
                    f"Coordinates ({point.x}, {point.y}) are outside screen bounds "
                    f"[0..{screen_bounds.width}, 0..{screen_bounds.height}]"
                )

    def validate_action_target(self, element: VisualElement) -> None:
        """Verify whether an action on this target is permitted by privacy policies."""
        if element.is_sensitive and element.element_type == ElementType.INPUT_PASSWORD:
            # We don't block clicking password fields (user might want to focus it),
            # but we ensure it is marked sensitive so callers know not to log typed values.
            pass
