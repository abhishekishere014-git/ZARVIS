"""Central coordinator and lifecycle manager for JARVIS Phase 09 Vision Subsystem."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent
from jarvis.vision.config import VisionConfig
from jarvis.vision.errors import TargetAmbiguityError, VisionError
from jarvis.vision.grounding.resolver import TargetResolver
from jarvis.vision.models import (
    ElementType,
    GroundingResult,
    ScreenObservation,
    VisualElement,
)
from jarvis.vision.perception.analyzer import ScreenAnalyzer
from jarvis.vision.perception.elements import filter_elements
from jarvis.vision.providers.base import VisionProvider
from jarvis.vision.providers.mock import MockVisionProvider
from jarvis.vision.security import VisionSecurityManager

logger = logging.getLogger("jarvis.vision.manager")


class VisionManager:
    """Manages visual perception, caching, coordinate grounding, and telemetry."""

    def __init__(
        self,
        config: Optional[VisionConfig] = None,
        provider: Optional[VisionProvider] = None,
        screen_capture: Optional[Any] = None,
        analyzer: Optional[ScreenAnalyzer] = None,
        resolver: Optional[TargetResolver] = None,
        security_manager: Optional[VisionSecurityManager] = None,
        event_bus: Optional[AsyncEventBus] = None,
    ):
        self.config = config or VisionConfig.from_settings()
        self.event_bus = event_bus
        self.screen_capture = screen_capture
        self.security = security_manager or VisionSecurityManager(self.config)

        if provider is not None:
            self.provider = provider
        elif self.config.provider == "mock":
            self.provider = MockVisionProvider()
        else:
            # Default to mock provider if provider unknown
            self.provider = MockVisionProvider()

        self.analyzer = analyzer or ScreenAnalyzer(
            provider=self.provider,
            config=self.config,
            security_manager=self.security,
        )
        self.resolver = resolver or TargetResolver(
            config=self.config,
            security_manager=self.security,
        )

        self._latest_observations: Dict[int, ScreenObservation] = {}

    def get_latest_observation(self, monitor_index: int = 0) -> Optional[ScreenObservation]:
        """Get the cached observation for a monitor if still fresh."""
        obs = self._latest_observations.get(monitor_index)
        if obs and not obs.check_staleness(self.config.observation_ttl_sec):
            return obs
        return None

    async def capture_and_analyze(
        self,
        monitor_index: int = 0,
        force_refresh: bool = False,
        screenshot_path: Optional[str] = None,
        screen_width: int = 1920,
        screen_height: int = 1080,
    ) -> ScreenObservation:
        """Capture screen via Phase 08 capture manager (or mock) and analyze elements."""
        if not force_refresh:
            existing = self.get_latest_observation(monitor_index)
            if existing:
                return existing

        path = screenshot_path
        width = screen_width
        height = screen_height

        # If Phase 08 ScreenCaptureManager is provided, capture actual screen
        if not path and self.screen_capture is not None:
            try:
                cap_res = await self.screen_capture.capture(monitor_index=monitor_index)
                path = str(cap_res.file_path)
                width = cap_res.width
                height = cap_res.height
            except Exception as e:
                logger.warning("ScreenCaptureManager capture failed, falling back: %s", e)

        if not path:
            path = f"mock_screen_mon_{monitor_index}.png"

        obs = await self.analyzer.analyze(
            screenshot_path=path,
            screen_width=width,
            screen_height=height,
            monitor_index=monitor_index,
        )

        self._latest_observations[monitor_index] = obs

        # Emit telemetry event
        correlation_id = f"vis_{uuid.uuid4().hex[:8]}"
        sanitized = self.security.sanitize_observation(obs)
        await self.emit_event(
            event_type="vision.observation.captured",
            correlation_id=correlation_id,
            payload={
                "observation_id": obs.observation_id,
                "monitor_index": monitor_index,
                "element_count": len(sanitized.elements),
                "region_count": len(sanitized.regions),
                "active_window": sanitized.active_window_title,
            },
        )

        return obs

    async def find_elements(
        self,
        query: Optional[str] = None,
        element_type: Optional[ElementType] = None,
        monitor_index: int = 0,
        clickable_only: bool = False,
        region_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> List[VisualElement]:
        """Find elements on the screen matching semantic query or filters."""
        obs = await self.capture_and_analyze(
            monitor_index=monitor_index, force_refresh=force_refresh
        )

        elements = obs.elements
        if region_id:
            elements = [el for el in elements if el.parent_region_id == region_id]

        if query:
            candidates = self.resolver.matcher.match(query, elements)
            elements = [c.element for c in candidates]

        filtered = filter_elements(
            elements,
            element_type=element_type,
            clickable_only=clickable_only,
        )
        return filtered

    async def resolve_target(
        self,
        query: str,
        monitor_index: int = 0,
        element_type: Optional[ElementType] = None,
        region_id: Optional[str] = None,
        clickable_only: bool = False,
        min_confidence: Optional[float] = None,
        allow_ambiguous: bool = False,
        force_refresh: bool = False,
    ) -> GroundingResult:
        """Ground a semantic query to a verified coordinate target."""
        obs = await self.capture_and_analyze(
            monitor_index=monitor_index, force_refresh=force_refresh
        )

        correlation_id = f"vis_ground_{uuid.uuid4().hex[:8]}"
        try:
            result = self.resolver.resolve(
                query=query,
                observation=obs,
                element_type=element_type,
                region_id=region_id,
                clickable_only=clickable_only,
                min_confidence=min_confidence,
                allow_ambiguous=allow_ambiguous,
            )

            await self.emit_event(
                event_type="vision.target.grounded",
                correlation_id=correlation_id,
                payload={
                    "query": query,
                    "target_point": result.target_point.to_dict(),
                    "confidence": result.confidence,
                    "confidence_level": result.confidence_level.value,
                    "element_id": result.element.element_id,
                    "element_type": result.element.element_type.value,
                    "is_ambiguous": result.is_ambiguous,
                },
            )
            return result

        except TargetAmbiguityError as err:
            await self.emit_event(
                event_type="vision.target.ambiguous",
                correlation_id=correlation_id,
                payload={
                    "query": query,
                    "candidate_count": err.details.get("candidate_count", 0),
                    "score_diff": err.details.get("score_diff", 0.0),
                },
            )
            raise

    async def emit_event(
        self,
        event_type: str,
        correlation_id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit telemetry event to AsyncEventBus."""
        if not self.event_bus or not getattr(self.event_bus, "is_running", False):
            return

        raw_payload = {
            "timestamp": time.time(),
            **(payload or {}),
        }

        event = JarvisEvent(
            id=f"evt_vis_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}",
            type=event_type,
            correlation_id=correlation_id,
            payload=raw_payload,
        )
        try:
            await self.event_bus.publish(event)
        except Exception as exc:
            logger.warning("Failed to publish Vision event '%s': %s", event_type, exc)

    async def health_check(self) -> Dict[str, Any]:
        """Check health of the vision subsystem."""
        provider_healthy = await self.provider.health_check()
        return {
            "status": "healthy" if provider_healthy else "degraded",
            "provider": self.config.provider,
            "provider_healthy": provider_healthy,
            "cached_observations": len(self._latest_observations),
        }
