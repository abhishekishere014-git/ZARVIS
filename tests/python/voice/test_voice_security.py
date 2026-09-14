"""Security and privacy tests for Voice & Audio Pipeline."""

from pathlib import Path
import pytest
from jarvis.voice.errors import (
    UnsupportedAudioFormatError,
    VoiceSecurityError,
    VoiceTimeoutError,
)
from jarvis.voice.models import AudioFormat
from jarvis.voice.security.manager import AudioSecurityManager


def test_audio_size_limit(tmp_path: Path):
    sec = AudioSecurityManager(temp_dir=tmp_path, max_audio_size_bytes=1024)
    # Valid payload
    sec.validate_audio_size(b"\x00" * 500)

    # Oversized payload
    with pytest.raises(VoiceSecurityError, match="exceeds maximum allowable limit"):
        sec.validate_audio_size(b"\x00" * 2000)


def test_audio_duration_limit(tmp_path: Path):
    sec = AudioSecurityManager(temp_dir=tmp_path, max_recording_duration_sec=10.0)
    sec.validate_audio_duration(5.0)

    with pytest.raises(VoiceTimeoutError, match="exceeds maximum allowed recording limit"):
        sec.validate_audio_duration(15.0)


def test_unsupported_audio_formats(tmp_path: Path):
    sec = AudioSecurityManager(temp_dir=tmp_path)

    # Invalid sample rate
    with pytest.raises(UnsupportedAudioFormatError, match="Unsupported sample rate"):
        sec.validate_audio_format(AudioFormat(sample_rate=12345))

    # Invalid channels
    with pytest.raises(UnsupportedAudioFormatError, match="Unsupported channel count"):
        sec.validate_audio_format(AudioFormat(channels=6))


def test_path_traversal_and_filename_sanitization(tmp_path: Path):
    sec = AudioSecurityManager(temp_dir=tmp_path)

    # Sanitization checks
    safe_name = sec.sanitize_filename("../../etc/passwd.wav")
    assert ".." not in safe_name
    assert "/" not in safe_name

    # Safe path resolution
    resolved = sec.resolve_safe_temp_path("recording.wav")
    assert resolved.parent == tmp_path.resolve()

    # Direct traversal attempt in filename resolution
    with pytest.raises(VoiceSecurityError, match="Path traversal"):
        # Crafting path that forces escape
        sec.resolve_safe_temp_path("../../../outside.wav")


def test_secret_and_audio_redaction(tmp_path: Path):
    sec = AudioSecurityManager(temp_dir=tmp_path)

    payload = {
        "audio_bytes": b"\x00" * 500,
        "openai_key": "Bearer sk-123456789012345678901234567890",
        "anthropic_key": "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234",
        "nested": {
            "pcm_bytes": b"\x01\x02",
            "token": "ghp_123456789012345678901234567890123456",
        },
    }

    scrubbed = sec.scrub_telemetry_payload(payload)
    assert scrubbed["audio_bytes"] == "[OMITTED_RAW_AUDIO]"
    assert "[REDACTED" in scrubbed["openai_key"]
    assert "[REDACTED" in scrubbed["anthropic_key"]
    assert scrubbed["nested"]["pcm_bytes"] == "[OMITTED_RAW_AUDIO]"
    assert "[REDACTED_GITHUB_TOKEN]" in scrubbed["nested"]["token"]
