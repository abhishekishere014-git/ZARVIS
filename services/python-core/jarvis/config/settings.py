"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class JarvisSettings(BaseSettings):
    """Runtime configuration for JARVIS Python Core."""

    model_config = SettingsConfigDict(
        env_prefix="JARVIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["development", "production", "test"] = "development"
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Security: loopback binding only by default
    core_host: str = Field(default="127.0.0.1", description="Bind IP for core IPC")
    core_port: int = Field(default=8765, description="Port for core IPC")

    data_dir: Path = Field(default=Path("./data"), description="Directory for persistent data")
    workspace_dir: Path = Field(
        default=Path("./data/workspace"),
        description="Directory for restricted sandboxed tool execution and generated files",
    )
    vault_backend: Literal["keyring", "memory"] = Field(
        default="keyring",
        description="Backend for credential isolation (Windows Credential Manager via keyring, or memory for tests)"
    )

    # Memory Engine Configuration (Phase 06)
    memory_enabled: bool = Field(default=True, description="Enable tri-tier memory engine")
    memory_db_path: Path | None = Field(default=None, description="Custom path to SQLite memory DB (defaults to data_dir/memory/jarvis-memory.db)")
    memory_max_working_messages: int = Field(default=50, description="Max messages in working memory buffer")
    memory_max_working_tokens: int = Field(default=8192, description="Max tokens in working memory buffer")
    memory_retention_days: int = Field(default=90, description="Durable retention window in days")
    memory_semantic_enabled: bool = Field(default=True, description="Enable vector semantic retrieval")
    memory_top_k: int = Field(default=5, description="Default top-K memories retrieved")
    memory_embedding_provider: str = Field(default="hash", description="Embedding provider: 'hash', 'mock', 'openai'")

    # Voice Pipeline Configuration (Phase 07)
    voice_enabled: bool = Field(default=True, description="Enable voice & audio pipeline")
    voice_sample_rate: int = Field(default=16000, description="Audio sample rate in Hz (16000 standard for speech)")
    voice_channels: int = Field(default=1, description="Audio channels (1 for mono)")
    voice_sample_width: int = Field(default=2, description="Audio sample width in bytes (2 for 16-bit PCM)")
    voice_stt_provider: str = Field(default="router", description="STT provider: 'router', 'vosk', 'whisper', 'mock'")
    voice_vosk_model_path: Path | None = Field(default=None, description="Path to local Vosk model directory")
    voice_whisper_model: str = Field(default="base", description="Faster-Whisper model name/size")
    voice_whisper_device: str = Field(default="cpu", description="Whisper compute device: 'cpu' or 'cuda'")
    voice_whisper_compute_type: str = Field(default="int8", description="Whisper quantization: 'int8', 'float16', 'float32'")
    voice_vad_provider: str = Field(default="energy", description="VAD provider: 'energy', 'mock'")
    voice_vad_energy_threshold: float = Field(default=500.0, description="RMS energy threshold for speech activity")
    voice_vad_silence_timeout_sec: float = Field(default=1.2, description="Seconds of silence to detect end of speech")
    voice_vad_min_speech_sec: float = Field(default=0.3, description="Minimum duration of speech to process")
    voice_max_recording_duration_sec: float = Field(default=30.0, description="Maximum recording duration in seconds")
    voice_max_audio_size_bytes: int = Field(default=25 * 1024 * 1024, description="Maximum audio payload size in bytes (25MB)")
    voice_tts_provider: str = Field(default="kokoro", description="TTS provider: 'kokoro', 'mock'")
    voice_kokoro_model_path: Path | None = Field(default=None, description="Path to Kokoro ONNX model file")
    voice_tts_voice: str = Field(default="af_heart", description="TTS voice identifier")
    voice_tts_speed: float = Field(default=1.0, description="TTS playback speed multiplier")
    voice_temp_dir: Path | None = Field(default=None, description="Temporary audio directory (defaults to workspace/temp/audio)")

    # OS Automation Configuration (Phase 08)
    os_automation_enabled: bool = Field(default=True, description="Enable controlled OS automation subsystem")
    os_automation_max_actions_per_turn: int = Field(default=15, description="Maximum OS actions per agent turn")
    os_action_timeout_sec: float = Field(default=10.0, description="Timeout for individual OS actions in seconds")
    screen_capture_enabled: bool = Field(default=True, description="Enable screen capture capability")
    screen_max_width: int = Field(default=3840, description="Maximum supported screenshot width")
    screen_max_height: int = Field(default=2160, description="Maximum supported screenshot height")
    screen_max_bytes: int = Field(default=10 * 1024 * 1024, description="Maximum screenshot size in bytes (10MB)")
    screen_temp_dir: Path | None = Field(default=None, description="Temporary screen directory (defaults to workspace/temp/screens)")
    mouse_enabled: bool = Field(default=True, description="Enable mouse movement and clicking")
    keyboard_enabled: bool = Field(default=True, description="Enable keyboard typing and hotkeys")
    keyboard_max_type_length: int = Field(default=500, description="Maximum characters typed per action")
    clipboard_enabled: bool = Field(default=True, description="Enable clipboard read/write/clear")
    clipboard_max_chars: int = Field(default=50000, description="Maximum clipboard characters allowed")
    window_management_enabled: bool = Field(default=True, description="Enable window discovery and focus/state control")
    require_approval_for_destructive_clicks: bool = Field(default=True, description="Require user approval for high-risk clicks")


    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def is_test(self) -> bool:
        return self.env == "test"
