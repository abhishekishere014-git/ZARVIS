"""Vision subsystem error hierarchy for JARVIS Phase 09."""

from typing import Any, List, Optional


class VisionError(Exception):
    """Base exception for all vision subsystem errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class VisionProviderError(VisionError):
    """Raised when an underlying vision provider fails or is unreachable."""
    pass


class VisionCaptureError(VisionError):
    """Raised when screen capture fails prior to visual analysis."""
    pass


class InvalidObservationError(VisionError):
    """Raised when visual observation payload is malformed or invalid."""
    pass


class ElementNotFoundError(VisionError):
    """Raised when a semantic query cannot locate any matching visual element."""

    def __init__(self, query: str, details: Optional[dict[str, Any]] = None):
        d = details or {}
        d["query"] = query
        super().__init__(f"No visual element found matching query: '{query}'", d)
        self.query = query


class TargetAmbiguityError(VisionError):
    """Raised when multiple candidate elements match a query with close confidence."""

    def __init__(
        self,
        query: str,
        candidates: List[Any],
        score_diff: float,
        details: Optional[dict[str, Any]] = None,
    ):
        d = details or {}
        d["query"] = query
        d["candidate_count"] = len(candidates)
        d["score_diff"] = score_diff
        super().__init__(
            f"Ambiguous target for query '{query}': {len(candidates)} candidates match within score delta {score_diff:.3f}. Refinement required.",
            d,
        )
        self.query = query
        self.candidates = candidates
        self.score_diff = score_diff


class ConfidenceRejectedError(VisionError):
    """Raised when best match confidence is below required threshold."""

    def __init__(
        self,
        query: str,
        confidence: float,
        threshold: float,
        details: Optional[dict[str, Any]] = None,
    ):
        d = details or {}
        d["query"] = query
        d["confidence"] = confidence
        d["threshold"] = threshold
        super().__init__(
            f"Match confidence {confidence:.3f} below required threshold {threshold:.3f} for query '{query}'",
            d,
        )
        self.query = query
        self.confidence = confidence
        self.threshold = threshold


class StaleObservationError(VisionError):
    """Raised when attempting to ground or act on an observation older than TTL."""

    def __init__(
        self,
        age_sec: float,
        ttl_sec: float,
        details: Optional[dict[str, Any]] = None,
    ):
        d = details or {}
        d["age_sec"] = age_sec
        d["ttl_sec"] = ttl_sec
        super().__init__(
            f"Observation is stale (age: {age_sec:.2f}s > TTL: {ttl_sec:.2f}s). New screen capture required.",
            d,
        )
        self.age_sec = age_sec
        self.ttl_sec = ttl_sec


class SensitiveRegionError(VisionError):
    """Raised when attempting to interact with or expose a sensitive/redacted visual region."""

    def __init__(self, region_name: str, details: Optional[dict[str, Any]] = None):
        d = details or {}
        d["region"] = region_name
        super().__init__(
            f"Action blocked on sensitive/redacted visual region: '{region_name}'",
            d,
        )
        self.region_name = region_name


class InvalidBoundingBoxError(VisionError):
    """Raised when a bounding box coordinates are negative or inverted."""
    pass
