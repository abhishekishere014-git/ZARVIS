"""Base protocol and interfaces for JARVIS Phase 09 Vision Providers."""

from typing import Protocol, runtime_checkable

from jarvis.vision.models import ScreenObservation


@runtime_checkable
class VisionProvider(Protocol):
    """Provider protocol for visual perception and screen analysis."""

    async def analyze_screen(
        self,
        screenshot_path: str,
        screen_width: int,
        screen_height: int,
        monitor_index: int = 0,
    ) -> ScreenObservation:
        """Analyze a screenshot image and extract visual elements and regions."""
        ...

    async def health_check(self) -> bool:
        """Check whether provider backend is healthy and operational."""
        ...
