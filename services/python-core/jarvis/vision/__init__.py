"""JARVIS Phase 09 — Vision, Screen Understanding & Visual Grounding Layer."""

from jarvis.vision.config import VisionConfig
from jarvis.vision.errors import (
    ConfidenceRejectedError,
    ElementNotFoundError,
    InvalidBoundingBoxError,
    InvalidObservationError,
    SensitiveRegionError,
    StaleObservationError,
    TargetAmbiguityError,
    VisionCaptureError,
    VisionError,
    VisionProviderError,
)
from jarvis.vision.grounding.confidence import (
    calculate_text_similarity,
    categorize_confidence,
)
from jarvis.vision.grounding.matcher import ElementMatcher
from jarvis.vision.grounding.resolver import TargetResolver
from jarvis.vision.manager import VisionManager
from jarvis.vision.models import (
    BoundingBox,
    ConfidenceLevel,
    ElementType,
    GroundingCandidate,
    GroundingResult,
    RegionType,
    ScreenObservation,
    ScreenRegion,
    VisionPoint,
    VisualElement,
)
from jarvis.vision.perception.analyzer import ScreenAnalyzer
from jarvis.vision.perception.elements import (
    filter_elements,
    find_elements_at_point,
    find_elements_in_bounds,
)
from jarvis.vision.perception.regions import (
    assign_elements_to_regions,
    find_enclosing_region,
    get_focused_region,
)
from jarvis.vision.providers.base import VisionProvider
from jarvis.vision.providers.mock import MockVisionProvider
from jarvis.vision.security import VisionSecurityManager
from jarvis.vision.tools.registration import ALL_VISION_TOOLS, register_vision_tools

__all__ = [
    # Config & Manager
    "VisionConfig",
    "VisionManager",
    "VisionSecurityManager",
    # Providers
    "VisionProvider",
    "MockVisionProvider",
    # Perception
    "ScreenAnalyzer",
    "filter_elements",
    "find_elements_at_point",
    "find_elements_in_bounds",
    "assign_elements_to_regions",
    "find_enclosing_region",
    "get_focused_region",
    # Grounding
    "ElementMatcher",
    "TargetResolver",
    "calculate_text_similarity",
    "categorize_confidence",
    # Models
    "VisionPoint",
    "BoundingBox",
    "VisualElement",
    "ScreenRegion",
    "ScreenObservation",
    "GroundingCandidate",
    "GroundingResult",
    "ElementType",
    "RegionType",
    "ConfidenceLevel",
    # Errors
    "VisionError",
    "VisionProviderError",
    "VisionCaptureError",
    "InvalidObservationError",
    "ElementNotFoundError",
    "TargetAmbiguityError",
    "ConfidenceRejectedError",
    "StaleObservationError",
    "SensitiveRegionError",
    "InvalidBoundingBoxError",
    # Tools
    "ALL_VISION_TOOLS",
    "register_vision_tools",
]
