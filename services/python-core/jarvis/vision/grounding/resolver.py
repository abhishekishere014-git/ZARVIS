"""Target resolution and grounding validation for Phase 09 Visual Grounding."""

from __future__ import annotations

import time
from typing import List, Optional

from jarvis.vision.config import VisionConfig
from jarvis.vision.errors import (
    ConfidenceRejectedError,
    ElementNotFoundError,
    StaleObservationError,
    TargetAmbiguityError,
)
from jarvis.vision.grounding.confidence import categorize_confidence
from jarvis.vision.grounding.matcher import ElementMatcher
from jarvis.vision.models import (
    ElementType,
    GroundingCandidate,
    GroundingResult,
    ScreenObservation,
    VisionPoint,
    VisualElement,
)
from jarvis.vision.security import VisionSecurityManager


class TargetResolver:
    """Resolves semantic descriptions into validated, confidence-scored screen coordinates."""

    def __init__(
        self,
        config: Optional[VisionConfig] = None,
        matcher: Optional[ElementMatcher] = None,
        security_manager: Optional[VisionSecurityManager] = None,
    ):
        self.config = config or VisionConfig()
        self.matcher = matcher or ElementMatcher()
        self.security_manager = security_manager or VisionSecurityManager(self.config)

    def resolve(
        self,
        query: str,
        observation: ScreenObservation,
        element_type: Optional[ElementType] = None,
        region_id: Optional[str] = None,
        clickable_only: bool = False,
        min_confidence: Optional[float] = None,
        allow_ambiguous: bool = False,
        current_time: Optional[float] = None,
    ) -> GroundingResult:
        """Resolve a semantic query against an observation into a screen target point."""
        # 1. Staleness check
        now = current_time if current_time is not None else time.time()
        age = observation.age(now)
        if age > self.config.observation_ttl_sec:
            raise StaleObservationError(age_sec=age, ttl_sec=self.config.observation_ttl_sec)

        # 2. Scope filtering
        elements = observation.elements
        if region_id:
            elements = [el for el in elements if el.parent_region_id == region_id]
        if element_type:
            elements = [el for el in elements if el.element_type == element_type]
        if clickable_only:
            elements = [el for el in elements if el.is_clickable]

        if not elements:
            raise ElementNotFoundError(
                query,
                details={
                    "total_observation_elements": len(observation.elements),
                    "region_id": region_id,
                    "element_type": element_type.value if element_type else None,
                },
            )

        # 3. Match and rank candidates
        candidates = self.matcher.match(query, elements)
        if not candidates:
            raise ElementNotFoundError(query)

        best_match = candidates[0]
        required_threshold = (
            min_confidence
            if min_confidence is not None
            else self.config.confidence_threshold_medium
        )

        # 4. Confidence threshold check
        if best_match.score < required_threshold:
            raise ConfidenceRejectedError(
                query=query,
                confidence=best_match.score,
                threshold=required_threshold,
                details={"best_candidate": best_match.element.to_summary()},
            )

        # 5. Ambiguity check
        is_ambiguous = False
        if len(candidates) > 1:
            second_match = candidates[1]
            score_diff = best_match.score - second_match.score
            if score_diff <= self.config.ambiguity_threshold_delta:
                is_ambiguous = True
                if not allow_ambiguous:
                    ambiguous_candidates = [
                        c.element.to_summary() for c in candidates[:3]
                    ]
                    raise TargetAmbiguityError(
                        query=query,
                        candidates=ambiguous_candidates,
                        score_diff=score_diff,
                    )

        # 6. Coordinate determination & boundary validation
        target_point = best_match.element.center
        self.security_manager.validate_coordinates(target_point)

        # 7. Build GroundingResult
        confidence_level = categorize_confidence(
            best_match.score,
            high_threshold=self.config.confidence_threshold_high,
            medium_threshold=self.config.confidence_threshold_medium,
        )

        suggested_action = "click" if best_match.element.is_clickable else "inspect"
        if best_match.element.element_type in [ElementType.INPUT_TEXT, ElementType.INPUT_PASSWORD]:
            suggested_action = "type"

        return GroundingResult(
            query=query,
            element=best_match.element,
            target_point=target_point,
            confidence=best_match.score,
            confidence_level=confidence_level,
            observation_id=observation.observation_id,
            candidates=candidates[:5],
            is_ambiguous=is_ambiguous,
            suggested_action=suggested_action,
        )
