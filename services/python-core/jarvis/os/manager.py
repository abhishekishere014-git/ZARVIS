"""Central manager and event dispatcher for the JARVIS OS Automation subsystem."""

import logging
import time
import uuid
from typing import Any, Dict, Optional
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent
from jarvis.os.clipboard.manager import ClipboardManager
from jarvis.os.config import OSAutomationConfig
from jarvis.os.errors import OSErrorBase, OSPolicyViolationError
from jarvis.os.input.keyboard import KeyboardManager
from jarvis.os.input.mouse import MouseManager
from jarvis.os.models import OSActionRequest, OSActionResult, OSVerificationResult
from jarvis.os.providers.base import OSProvider
from jarvis.os.screen.capture import ScreenCaptureManager
from jarvis.os.screen.monitor import MonitorManager
from jarvis.os.security import OSSecurityManager
from jarvis.os.system.info import SystemInfoManager
from jarvis.os.verification.verifier import OSActionVerifier
from jarvis.os.window.manager import WindowManager

logger = logging.getLogger("jarvis.os.manager")


class OSAutomationManager:
    """Coordinates OS automation subsystems, security validation, and telemetry."""

    def __init__(
        self,
        config: Optional[OSAutomationConfig] = None,
        provider: Optional[OSProvider] = None,
        security_manager: Optional[OSSecurityManager] = None,
        event_bus: Optional[AsyncEventBus] = None,
        workspace_root: Optional[Any] = None,
        **kwargs,
    ) -> None:
        self.config = config or OSAutomationConfig()
        if workspace_root:
            from pathlib import Path
            self.config.screen_temp_dir = Path(workspace_root) / "temp/screens"

        if provider is None:
            from jarvis.os.providers.mock import MockOSProvider
            self.provider = MockOSProvider()
        else:
            self.provider = provider

        self.event_bus = event_bus

        self.security = security_manager or OSSecurityManager(
            temp_dir=self.config.screen_temp_dir,
            max_type_length=self.config.keyboard_max_type_length,
            max_clipboard_chars=self.config.clipboard_max_chars,
            max_screen_bytes=self.config.screen_max_bytes,
        )

        self.screen = ScreenCaptureManager(
            provider=self.provider,
            security_manager=self.security,
            sandbox_dir=self.config.screen_temp_dir,
        )
        self.monitor = MonitorManager(provider=self.provider)
        self.mouse = MouseManager(
            provider=self.provider,
            security_manager=self.security,
            require_approval_for_destructive=self.config.require_approval_for_destructive_clicks,
        )
        self.keyboard = KeyboardManager(
            provider=self.provider,
            security_manager=self.security,
        )
        self.window = WindowManager(provider=self.provider)
        self.clipboard = ClipboardManager(
            provider=self.provider,
            security_manager=self.security,
        )
        self.system = SystemInfoManager(provider=self.provider)
        self.verifier = OSActionVerifier(provider=self.provider)

    async def emit_event(
        self,
        event_type: str,
        correlation_id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emits scrubbed telemetry event to AsyncEventBus."""
        if not self.event_bus or not self.event_bus.is_running:
            return

        raw_payload = {
            "timestamp": time.time(),
            **(payload or {}),
        }
        safe_payload = self.security.scrub_telemetry_payload(raw_payload)

        event = JarvisEvent(
            id=f"evt_os_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}",
            type=event_type,
            correlation_id=correlation_id,
            payload=safe_payload,
        )
        try:
            await self.event_bus.publish(event)
        except Exception as exc:
            logger.warning("Failed to publish OS event '%s': %s", event_type, exc)
