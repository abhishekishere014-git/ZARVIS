"""Configuration dataclass for JARVIS Phase 09 Vision Subsystem."""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


DEFAULT_SENSITIVE_KEYWORDS = [
    "password",
    "passwd",
    "pin",
    "secret",
    "api_key",
    "apikey",
    "token",
    "auth_token",
    "access_token",
    "credit_card",
    "cvv",
    "ssn",
    "social_security",
    "private_key",
]


class VisionConfig(BaseModel):
    """Runtime configuration for visual perception and grounding."""

    enabled: bool = Field(default=True, description="Enable vision subsystem")
    provider: str = Field(default="mock", description="Vision provider type ('mock', 'local_ocr', 'multimodal_ai')")
    confidence_threshold_high: float = Field(
        default=0.85,
        description="High confidence threshold for autonomous interaction",
    )
    confidence_threshold_medium: float = Field(
        default=0.60,
        description="Medium confidence threshold",
    )
    observation_ttl_sec: float = Field(
        default=15.0,
        description="Screen observation TTL in seconds before considered stale",
    )
    max_elements: int = Field(
        default=200,
        description="Maximum elements extracted per screen analysis",
    )
    downscale_width: int = Field(
        default=1920,
        description="Target width for downscaled screen perception",
    )
    downscale_height: int = Field(
        default=1080,
        description="Target height for downscaled screen perception",
    )
    ambiguity_threshold_delta: float = Field(
        default=0.08,
        description="Score delta within which candidates are considered ambiguous",
    )
    sensitive_keywords: List[str] = Field(
        default_factory=lambda: list(DEFAULT_SENSITIVE_KEYWORDS),
        description="Keywords indicating sensitive or confidential screen content",
    )

    @classmethod
    def from_settings(cls, settings: Any = None) -> VisionConfig:
        """Create VisionConfig from JarvisSettings if available."""
        if settings is None:
            from jarvis.config.settings import get_settings
            settings = get_settings()

        return cls(
            enabled=getattr(settings, "vision_enabled", True),
            provider=getattr(settings, "vision_provider", "mock"),
            confidence_threshold_high=getattr(settings, "vision_confidence_threshold_high", 0.85),
            confidence_threshold_medium=getattr(settings, "vision_confidence_threshold_medium", 0.60),
            observation_ttl_sec=getattr(settings, "vision_observation_ttl_sec", 15.0),
            max_elements=getattr(settings, "vision_max_elements", 200),
            downscale_width=getattr(settings, "vision_downscale_width", 1920),
            downscale_height=getattr(settings, "vision_downscale_height", 1080),
        )
