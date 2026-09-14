"""Screen capture management, file sandboxing, and format downscaling."""

import base64
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Optional, Tuple
from jarvis.os.errors import ScreenCaptureError
from jarvis.os.models import ScreenCaptureRequest, ScreenCaptureResult, ScreenInfo
from jarvis.os.providers.base import OSProvider
from jarvis.os.security import OSSecurityManager

logger = logging.getLogger("jarvis.os.screen.capture")


class ScreenCaptureManager:
    """Coordinates screen capture, size bounding, and temporary sandbox persistence."""

    def __init__(
        self,
        provider: OSProvider,
        security_manager: Optional[OSSecurityManager] = None,
        sandbox_dir: Optional[Path] = None,
        security: Optional[OSSecurityManager] = None,
        config: Optional[Any] = None,
        **kwargs,
    ) -> None:
        self.provider = provider
        sec = security or security_manager
        if sec is None:
            sec = OSSecurityManager(screens_temp_dir="temp/screens")
        self.security = sec
        self.sandbox_dir = sandbox_dir or getattr(self.security, "temp_dir", Path("data/workspace/temp/screens"))

    def capture(self, request: ScreenCaptureRequest) -> ScreenCaptureResult:
        """Captures visual screen data and stores strictly inside temporary sandbox."""
        raw_bytes = self.provider.capture_screen(
            region=request.region,
            monitor_id=request.monitor_id,
            image_format=request.image_format,
            max_width=request.max_width,
            max_height=request.max_height,
        )

        size_bytes = len(raw_bytes)
        if size_bytes > self.security.max_screen_bytes:
            raise ScreenCaptureError(
                f"Captured screenshot size ({size_bytes} bytes) exceeds safety limit of {self.security.max_screen_bytes} bytes"
            )

        # Generate unique safe temporary filename
        timestamp_str = int(time.time() * 1000)
        filename = f"screen_{timestamp_str}_{uuid.uuid4().hex[:6]}.{request.image_format}"
        safe_path = self.security.resolve_safe_screenshot_path(filename)

        with open(safe_path, "wb") as f:
            f.write(raw_bytes)

        # Derive image dimensions from region or screen info
        w, h = 1920, 1080
        if request.region:
            _, _, w, h = request.region
        else:
            info = self.provider.get_screen_info()
            w, h = info.virtual_width, info.virtual_height

        if request.max_width and w > request.max_width:
            scale = request.max_width / w
            w = int(w * scale)
            h = int(h * scale)

        b64_str = None
        if request.include_base64:
            b64_str = f"data:image/{request.image_format};base64," + base64.b64encode(raw_bytes).decode("ascii")

        return ScreenCaptureResult(
            image_path=str(safe_path),
            image_base64=b64_str,
            width=w,
            height=h,
            format=request.image_format,
            size_bytes=size_bytes,
            timestamp=time.time(),
        )

    def cleanup_old_screenshots(self, max_age_seconds: float = 300.0) -> int:
        """Removes temporary screenshots exceeding max_age_seconds."""
        purged = 0
        now = time.time()
        try:
            for p in self.security.temp_dir.glob("screen_*.*"):
                if p.is_file() and (now - p.stat().st_mtime > max_age_seconds):
                    try:
                        p.unlink()
                        purged += 1
                    except Exception:
                        pass
        except Exception as exc:
            logger.debug("Error during screenshot cleanup: %s", exc)
        return purged
