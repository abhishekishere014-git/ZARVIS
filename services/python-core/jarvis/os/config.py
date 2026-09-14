"""Configuration models for JARVIS OS Automation."""

from pathlib import Path
from pydantic import BaseModel, Field
from jarvis.config.settings import JarvisSettings


class OSAutomationConfig(BaseModel):
    """Runtime configuration for Controlled OS Automation."""
    enabled: bool = Field(default=True, description="Master enable switch for OS automation")
    max_actions_per_turn: int = Field(default=15, description="Maximum actions per autonomous agent turn")
    action_timeout_sec: float = Field(default=10.0, description="Timeout for individual operations in seconds")
    
    # Screen Settings
    screen_capture_enabled: bool = Field(default=True)
    screen_max_width: int = Field(default=3840)
    screen_max_height: int = Field(default=2160)
    screen_max_bytes: int = Field(default=10 * 1024 * 1024)  # 10 MB
    screen_temp_dir: Path = Field(default=Path("./data/workspace/temp/screens"))
    
    # Input Settings
    mouse_enabled: bool = Field(default=True)
    keyboard_enabled: bool = Field(default=True)
    keyboard_max_type_length: int = Field(default=500)
    
    # Clipboard Settings
    clipboard_enabled: bool = Field(default=True)
    clipboard_max_chars: int = Field(default=50000)
    
    # Window Settings
    window_management_enabled: bool = Field(default=True)
    require_approval_for_destructive_clicks: bool = Field(default=True)

    @classmethod
    def from_settings(cls, settings: JarvisSettings) -> "OSAutomationConfig":
        """Constructs OSAutomationConfig from centralized JarvisSettings."""
        return cls(
            enabled=settings.os_automation_enabled,
            max_actions_per_turn=settings.os_automation_max_actions_per_turn,
            action_timeout_sec=settings.os_action_timeout_sec,
            screen_capture_enabled=settings.screen_capture_enabled,
            screen_max_width=settings.screen_max_width,
            screen_max_height=settings.screen_max_height,
            screen_max_bytes=settings.screen_max_bytes,
            screen_temp_dir=settings.screen_temp_dir or (settings.workspace_dir / "temp" / "screens"),
            mouse_enabled=settings.mouse_enabled,
            keyboard_enabled=settings.keyboard_enabled,
            keyboard_max_type_length=settings.keyboard_max_type_length,
            clipboard_enabled=settings.clipboard_enabled,
            clipboard_max_chars=settings.clipboard_max_chars,
            window_management_enabled=settings.window_management_enabled,
            require_approval_for_destructive_clicks=settings.require_approval_for_destructive_clicks,
        )
