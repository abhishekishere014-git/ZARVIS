"""Display monitor enumeration and geometry queries."""

from typing import List
from jarvis.os.models import MonitorInfo, ScreenInfo
from jarvis.os.providers.base import OSProvider


class MonitorManager:
    """Manages queries regarding connected monitors and virtual screen geometry."""

    def __init__(self, provider: OSProvider) -> None:
        self.provider = provider

    def get_screen_info(self) -> ScreenInfo:
        return self.provider.get_screen_info()

    def list_monitors(self) -> List[MonitorInfo]:
        return self.provider.get_screen_info().monitors

    get_monitors = list_monitors

    def get_primary_monitor(self) -> MonitorInfo:
        info = self.provider.get_screen_info()
        for m in info.monitors:
            if m.is_primary:
                return m
        return info.monitors[0] if info.monitors else MonitorInfo(id=0, width=1920, height=1080)
