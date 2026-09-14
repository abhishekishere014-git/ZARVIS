"""JARVIS Voice & Audio Pipeline package."""

from jarvis.voice.audio import (
    AudioCapture,
    AudioDeviceInfo,
    AudioDeviceManager,
    AudioPlayback,
    BaseAudioCapture,
    BaseAudioPlayback,
    VirtualAudioCapture,
    VirtualAudioPlayback,
    calculate_pcm_rms,
    generate_sine_wave,
    pcm_to_wav,
    wav_to_pcm,
)
from jarvis.voice.config import VoiceConfig
from jarvis.voice.errors import (
    AudioCaptureError,
    AudioDeviceError,
    AudioPlaybackError,
    STTError,
    STTProviderUnavailableError,
    TTSError,
    TTSProviderUnavailableError,
    UnsupportedAudioFormatError,
    VADError,
    VoiceError,
    VoiceInterruptedError,
    VoiceSecurityError,
    VoiceStateError,
    VoiceTimeoutError,
)
from jarvis.voice.factory import build_voice_pipeline
from jarvis.voice.models import (
    AudioChunk,
    AudioEncoding,
    AudioFormat,
    AudioMetadata,
    STTConfidence,
    STTRequest,
    STTResult,
    Transcript,
    TranscriptSegment,
    TTSRequest,
    TTSResult,
    VADResult,
    VoiceRequest,
    VoiceResponse,
    VoiceSessionState,
)
from jarvis.voice.pipeline import VoicePipeline
from jarvis.voice.security import AudioSecurityManager
from jarvis.voice.session import VoiceSession
from jarvis.voice.state import VoiceStateMachine
from jarvis.voice.stt import (
    FasterWhisperSTTProvider,
    MockSTTProvider,
    STTProvider,
    STTRouter,
    VoskSTTProvider,
)
from jarvis.voice.tts import (
    KokoroTTSProvider,
    MockTTSProvider,
    TTSProvider,
)
from jarvis.voice.vad import (
    EnergyVAD,
    MockVAD,
    VADProvider,
    VADSegmenter,
)

__all__ = [
    # Models
    "AudioFormat",
    "AudioMetadata",
    "AudioEncoding",
    "AudioChunk",
    "TranscriptSegment",
    "Transcript",
    "STTConfidence",
    "VoiceSessionState",
    "VADResult",
    "STTRequest",
    "STTResult",
    "TTSRequest",
    "TTSResult",
    "VoiceRequest",
    "VoiceResponse",
    # Errors
    "VoiceError",
    "AudioDeviceError",
    "AudioCaptureError",
    "AudioPlaybackError",
    "UnsupportedAudioFormatError",
    "VADError",
    "STTError",
    "STTProviderUnavailableError",
    "TTSError",
    "TTSProviderUnavailableError",
    "VoiceTimeoutError",
    "VoiceInterruptedError",
    "VoiceSecurityError",
    "VoiceStateError",
    # Config & Pipeline
    "VoiceConfig",
    "VoicePipeline",
    "VoiceSession",
    "VoiceStateMachine",
    "AudioSecurityManager",
    "build_voice_pipeline",
    # Audio
    "AudioCapture",
    "AudioPlayback",
    "BaseAudioCapture",
    "BaseAudioPlayback",
    "VirtualAudioCapture",
    "VirtualAudioPlayback",
    "AudioDeviceInfo",
    "AudioDeviceManager",
    "calculate_pcm_rms",
    "pcm_to_wav",
    "wav_to_pcm",
    "generate_sine_wave",
    # VAD
    "VADProvider",
    "VADSegmenter",
    "EnergyVAD",
    "MockVAD",
    # STT
    "STTProvider",
    "VoskSTTProvider",
    "FasterWhisperSTTProvider",
    "MockSTTProvider",
    "STTRouter",
    # TTS
    "TTSProvider",
    "KokoroTTSProvider",
    "MockTTSProvider",
]
