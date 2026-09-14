"""Normalized error taxonomy for JARVIS Voice & Audio Pipeline."""

from typing import Any, Dict, Optional
from jarvis.core.exceptions import JarvisError


class VoiceError(JarvisError):
    """Base exception for all voice subsystem errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)


class AudioDeviceError(VoiceError):
    """Raised when an audio input/output device cannot be accessed or enumerated."""
    pass


class AudioCaptureError(VoiceError):
    """Raised when audio stream capture fails or encounters hardware overflow."""
    pass


class AudioPlaybackError(VoiceError):
    """Raised when audio playback fails or encounters buffer underrun."""
    pass


class UnsupportedAudioFormatError(VoiceError):
    """Raised when requested sample rate, bit depth, or encoding is unsupported."""
    pass


class VADError(VoiceError):
    """Raised when Voice Activity Detection fails."""
    pass


class STTError(VoiceError):
    """Raised when speech-to-text recognition fails."""
    pass


class STTProviderUnavailableError(STTError):
    """Raised when no requested or fallback STT provider is available."""
    pass


class TTSError(VoiceError):
    """Raised when text-to-speech synthesis fails."""
    pass


class TTSProviderUnavailableError(TTSError):
    """Raised when no requested or fallback TTS provider is available."""
    pass


class VoiceTimeoutError(VoiceError):
    """Raised when recording, listening, or processing exceeds the maximum duration."""
    pass


class VoiceInterruptedError(VoiceError):
    """Raised when an active voice session is interrupted by user barge-in."""
    pass


class VoiceSecurityError(VoiceError):
    """Raised when audio input exceeds safety limits, contains invalid paths, or violates privacy rules."""
    pass


class VoiceStateError(VoiceError):
    """Raised when an invalid state transition is attempted in the voice state machine."""
    pass
