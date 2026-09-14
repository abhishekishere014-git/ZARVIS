"""Configuration domain models for JARVIS Voice & Audio Pipeline."""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from jarvis.config.settings import JarvisSettings


class VoiceConfig(BaseModel):
    """Runtime configuration for Voice & Audio Pipeline."""
    enabled: bool = Field(default=True, description="Enable voice & audio pipeline")
    sample_rate: int = Field(default=16000, description="Sampling rate in Hz")
    channels: int = Field(default=1, description="Channels: 1 mono, 2 stereo")
    sample_width: int = Field(default=2, description="Bytes per sample (16-bit PCM = 2)")
    
    # STT Settings
    stt_provider: str = Field(default="router", description="STT provider: 'router', 'vosk', 'whisper', 'mock'")
    vosk_model_path: Optional[Path] = Field(default=None, description="Path to Vosk speech model")
    whisper_model: str = Field(default="base", description="Faster-Whisper model identifier")
    whisper_device: str = Field(default="cpu", description="Whisper inference device")
    whisper_compute_type: str = Field(default="int8", description="Whisper compute quantization")
    stt_fastpath_confidence_threshold: float = Field(default=0.75, description="Confidence required to accept Vosk fast-path")
    stt_fastpath_max_duration_sec: float = Field(default=5.0, description="Max utterance duration for Vosk fast-path")

    # VAD Settings
    vad_provider: str = Field(default="energy", description="VAD provider: 'energy', 'mock'")
    vad_energy_threshold: float = Field(default=500.0, description="Energy RMS threshold for speech")
    vad_silence_timeout_sec: float = Field(default=1.2, description="Silence duration to detect speech end")
    vad_min_speech_sec: float = Field(default=0.3, description="Minimum duration to qualify as speech")
    
    # Limits & Security
    max_recording_duration_sec: float = Field(default=30.0, description="Maximum recording duration")
    max_audio_size_bytes: int = Field(default=25 * 1024 * 1024, description="Maximum audio byte size")
    temp_dir: Path = Field(default=Path("./data/workspace/temp/audio"), description="Temporary audio sandbox directory")
    persist_raw_audio: bool = Field(default=False, description="Persist raw audio recordings (default False for privacy)")

    # TTS Settings
    tts_provider: str = Field(default="kokoro", description="TTS provider: 'kokoro', 'mock'")
    kokoro_model_path: Optional[Path] = Field(default=None, description="Path to Kokoro ONNX model")
    tts_voice: str = Field(default="af_heart", description="TTS voice identifier")
    tts_speed: float = Field(default=1.0, ge=0.25, le=4.0, description="TTS playback speed")

    @classmethod
    def from_settings(cls, settings: JarvisSettings) -> "VoiceConfig":
        """Builds VoiceConfig from central JarvisSettings."""
        return cls(
            enabled=settings.voice_enabled,
            sample_rate=settings.voice_sample_rate,
            channels=settings.voice_channels,
            sample_width=settings.voice_sample_width,
            stt_provider=settings.voice_stt_provider,
            vosk_model_path=settings.voice_vosk_model_path,
            whisper_model=settings.voice_whisper_model,
            whisper_device=settings.voice_whisper_device,
            whisper_compute_type=settings.voice_whisper_compute_type,
            vad_provider=settings.voice_vad_provider,
            vad_energy_threshold=settings.voice_vad_energy_threshold,
            vad_silence_timeout_sec=settings.voice_vad_silence_timeout_sec,
            vad_min_speech_sec=settings.voice_vad_min_speech_sec,
            max_recording_duration_sec=settings.voice_max_recording_duration_sec,
            max_audio_size_bytes=settings.voice_max_audio_size_bytes,
            temp_dir=settings.voice_temp_dir or (settings.workspace_dir / "temp" / "audio"),
            tts_provider=settings.voice_tts_provider,
            kokoro_model_path=settings.voice_kokoro_model_path,
            tts_voice=settings.voice_tts_voice,
            tts_speed=settings.voice_tts_speed,
        )
