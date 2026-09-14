"""System telemetry and hardware inventory reporting."""

from jarvis.os.models import SystemInfo
from jarvis.os.providers.base import OSProvider


class SystemInfoManager:
    """Provides read-only system telemetry."""

    def __init__(self, provider: OSProvider) -> None:
        self.provider = provider

    def get_info(self) -> SystemInfo:
        return self.provider.get_system_info()
