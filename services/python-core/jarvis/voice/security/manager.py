"""Audio security, privacy guardrails, and temporary file lifecycle management."""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
from jarvis.voice.errors import (
    UnsupportedAudioFormatError,
    VoiceSecurityError,
    VoiceTimeoutError,
)
from jarvis.voice.models import AudioFormat

logger = logging.getLogger("jarvis.voice.security")

# Secret redaction patterns matching Phase 06 standards
SECRET_PATTERNS = [
    (re.compile(r"sk-ant-[a-zA-Z0-9_\-]{20,}"), "[REDACTED_ANTHROPIC_KEY]"),
    (re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"), "[REDACTED_OPENAI_KEY]"),
    (re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "[REDACTED_GEMINI_KEY]"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"hf_[a-zA-Z0-9]{34}"), "[REDACTED_HF_TOKEN]"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
]


class AudioSecurityManager:
    """Enforces audio boundary limits, sandbox containment, and privacy protection."""

    def __init__(
        self,
        temp_dir: Path,
        max_recording_duration_sec: float = 30.0,
        max_audio_size_bytes: int = 25 * 1024 * 1024,  # 25 MB
        persist_raw_audio: bool = False,
    ) -> None:
        self.temp_dir = Path(temp_dir).resolve()
        self.max_recording_duration_sec = max_recording_duration_sec
        self.max_audio_size_bytes = max_audio_size_bytes
        self.persist_raw_audio = persist_raw_audio
        self._ensure_temp_dir()

    def _ensure_temp_dir(self) -> None:
        try:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("Could not create audio temp dir: %s", exc)

    def validate_audio_size(self, audio_bytes: bytes) -> None:
        """Enforces upper bound on raw audio byte size."""
        if len(audio_bytes) > self.max_audio_size_bytes:
            raise VoiceSecurityError(
                f"Audio payload size ({len(audio_bytes)} bytes) exceeds maximum allowable limit of {self.max_audio_size_bytes} bytes",
                details={"actual_bytes": len(audio_bytes), "max_bytes": self.max_audio_size_bytes},
            )

    def validate_audio_duration(self, duration_sec: float) -> None:
        """Enforces upper bound on audio duration."""
        if duration_sec > self.max_recording_duration_sec:
            raise VoiceTimeoutError(
                f"Audio duration ({duration_sec:.1f}s) exceeds maximum allowed recording limit of {self.max_recording_duration_sec}s",
                details={"duration_sec": duration_sec, "max_sec": self.max_recording_duration_sec},
            )

    def validate_audio_format(self, audio_format: AudioFormat) -> None:
        """Validates that sample rate and bit depth fall within acceptable ranges."""
        if audio_format.sample_rate not in (8000, 16000, 22050, 24000, 44100, 48000):
            raise UnsupportedAudioFormatError(
                f"Unsupported sample rate: {audio_format.sample_rate}Hz. Must be one of [8000, 16000, 22050, 24000, 44100, 48000]"
            )
        if audio_format.channels not in (1, 2):
            raise UnsupportedAudioFormatError(
                f"Unsupported channel count: {audio_format.channels}. Only mono (1) and stereo (2) are supported."
            )
        if audio_format.sample_width not in (1, 2, 4):
            raise UnsupportedAudioFormatError(
                f"Unsupported sample width: {audio_format.sample_width} bytes. Must be 1 (8-bit), 2 (16-bit), or 4 (32-bit)."
            )

    def sanitize_filename(self, filename: str) -> str:
        """Strips path traversal components and illegal characters from audio filenames."""
        # Remove directory separators, null bytes, and parent references
        cleaned = filename.replace("\x00", "").replace("/", "_").replace("\\", "_")
        cleaned = re.sub(r"\.\.+", "_", cleaned)
        cleaned = re.sub(r"[^\w\.\-]", "_", cleaned)
        if not cleaned or cleaned.startswith("."):
            cleaned = f"audio_{cleaned}"
        return cleaned

    def resolve_safe_temp_path(self, filename: str) -> Path:
        """Resolves and validates a temp audio file path strictly inside temp_dir."""
        if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
            raise VoiceSecurityError(
                f"Path traversal detected in audio temporary filename: '{filename}' attempts directory traversal"
            )

        safe_name = self.sanitize_filename(filename)
        candidate = (self.temp_dir / safe_name).resolve()

        # Path traversal & symlink escape verification
        try:
            candidate.relative_to(self.temp_dir)
        except ValueError:
            raise VoiceSecurityError(
                f"Path traversal detected in audio temporary filename: '{filename}' resolves outside '{self.temp_dir}'"
            )

        if candidate.is_symlink():
            raise VoiceSecurityError(f"Symlinks are prohibited in audio temp files: '{candidate}'")

        return candidate

    def cleanup_temp_file(self, path: Path) -> None:
        """Safely removes temporary audio files after transcription."""
        try:
            resolved = Path(path).resolve()
            resolved.relative_to(self.temp_dir)
            if resolved.exists() and resolved.is_file():
                resolved.unlink()
        except Exception as exc:
            logger.debug("Failed to clean up temporary audio file '%s': %s", path, exc)

    def scrub_telemetry_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures raw audio data and secret credentials are never published in events or logs."""
        scrubbed = {}
        for k, v in payload.items():
            if k.lower() in ("audio_bytes", "raw_audio", "pcm_bytes", "wav_bytes"):
                scrubbed[k] = "[OMITTED_RAW_AUDIO]"
            elif isinstance(v, str):
                scrubbed_str = v
                for pattern, repl in SECRET_PATTERNS:
                    scrubbed_str = pattern.sub(repl, scrubbed_str)
                scrubbed[k] = scrubbed_str
            elif isinstance(v, dict):
                scrubbed[k] = self.scrub_telemetry_payload(v)
            else:
                scrubbed[k] = v
        return scrubbed
