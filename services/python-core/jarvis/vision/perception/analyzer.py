"""High-level screen analysis coordinator for JARVIS Phase 09."""

from __future__ import annotations

from typing import Optional

from jarvis.vision.config import VisionConfig
from jarvis.vision.models import ScreenObservation
from jarvis.vision.perception.regions import assign_elements_to_regions
from jarvis.vision.providers.base import VisionProvider
from jarvis.vision.security import VisionSecurityManager


class ScreenAnalyzer:
    """Performs visual understanding, element linking, and security tagging."""

    def __init__(
        self,
        provider: VisionProvider,
        config: Optional[VisionConfig] = None,
        security_manager: Optional[VisionSecurityManager] = None,
    ):
        self.provider = provider
        self.config = config or VisionConfig()
        self.security_manager = security_manager or VisionSecurityManager(self.config)

    async def analyze(
        self,
        screenshot_path: str,
        screen_width: int,
        screen_height: int,
        monitor_index: int = 0,
    ) -> ScreenObservation:
        """Run perception pipeline on a screenshot and enrich the observation."""
        # 1. Provider analysis
        obs = await self.provider.analyze_screen(
            screenshot_path=screenshot_path,
            screen_width=screen_width,
            screen_height=screen_height,
            monitor_index=monitor_index,
        )

        # 2. Structural hierarchy: assign elements to regions
        assign_elements_to_regions(obs.elements, obs.regions)

        # 3. Privacy & Security: flag sensitive elements and regions
        for el in obs.elements:
            if self.security_manager.detect_sensitive_element(el):
                el.is_sensitive = True

        for reg in obs.regions:
            if self.security_manager.is_text_sensitive(reg.title):
                reg.is_sensitive = True

        # 4. Enforce max elements limit if necessary
        if len(obs.elements) > self.config.max_elements:
            # Keep highest confidence elements
            obs.elements.sort(key=lambda e: e.confidence, reverse=True)
            obs.elements = obs.elements[: self.config.max_elements]

        return obs
