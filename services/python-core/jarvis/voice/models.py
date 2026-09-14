"""Domain models and contracts for JARVIS Voice & Audio Pipeline."""

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AudioEncoding(str, Enum):
    """Supported audio encodings."""
    PCM_S16LE = "pcm_s16le"
    WAV = "wav"


class AudioFormat(BaseModel):
    """Audio stream and file formatting specification."""
    sample_rate: int = Field(default=16000, description="Sample rate in Hz (e.g. 16000)")
    channels: int = Field(default=1, description="Number of channels (1=mono, 2=stereo)")
    sample_width: int = Field(default=2, description="Bytes per sample (2 for 16-bit PCM)")
    encoding: AudioEncoding = Field(default=AudioEncoding.PCM_S16LE, description="Audio encoding format")

    @property
    def bytes_per_second(self) -> int:
        return self.sample_rate * self.channels * self.sample_width

    @property
    def frame_size(self) -> int:
        return self.channels * self.sample_width


class AudioMetadata(BaseModel):
    """Metadata describing captured or synthesized audio."""
    duration_sec: float = Field(ge=0.0, description="Duration in seconds")
    frame_count: int = Field(ge=0, description="Total audio frames")
    sample_rate: int = Field(default=16000)
    channels: int = Field(default=1)
    sample_width: int = Field(default=2)
    file_size_bytes: int = Field(default=0, ge=0)
    source_device: Optional[str] = Field(default=None)
    created_at: float = Field(default_factory=time.time)


class STTConfidence(str, Enum):
    """Normalized confidence tier."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @classmethod
    def from_score(cls, score: float) -> "STTConfidence":
        if score >= 0.80:
            return cls.HIGH
        elif score >= 0.50:
            return cls.MEDIUM
        return cls.LOW


class TranscriptSegment(BaseModel):
    """Time-indexed segment of transcribed speech."""
    text: str = Field(..., description="Recognized text fragment")
    start_sec: float = Field(default=0.0, ge=0.0)
    end_sec: float = Field(default=0.0, ge=0.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    language: Optional[str] = Field(default=None)


class Transcript(BaseModel):
    """Full speech transcription result."""
    text: str = Field(default="", description="Consolidated recognized text")
    segments: List[TranscriptSegment] = Field(default_factory=list)
    language: str = Field(default="en", description="Detected language code (e.g. 'en', 'hi', 'hi-en')")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_final: bool = Field(default=True, description="Whether this is a final or interim transcript")
    raw_text: Optional[str] = Field(default=None, description="Original unnormalized raw transcript")

    @property
    def confidence_tier(self) -> STTConfidence:
        return STTConfidence.from_score(self.confidence)


class VoiceSessionState(str, Enum):
    """Deterministic states of the voice conversation lifecycle."""
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    ERROR = "ERROR"


class AudioChunk(BaseModel):
    """Single discrete chunk of streamed audio."""
    data: bytes = Field(..., description="Raw audio byte payload")
    sequence: int = Field(default=0, ge=0)
    timestamp: float = Field(default_factory=time.time)
    duration_sec: float = Field(default=0.0, ge=0.0)
    is_speech: bool = Field(default=False)


class VADResult(BaseModel):
    """Result of Voice Activity Detection on an audio segment."""
    is_speech: bool = Field(..., description="True if human speech activity was detected")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    energy: float = Field(default=0.0, ge=0.0, description="Measured RMS energy level")
    timestamp: float = Field(default_factory=time.time)


class STTRequest(BaseModel):
    """Request envelope for speech transcription."""
    audio_bytes: bytes = Field(..., description="Audio byte payload (PCM or WAV)")
    audio_format: AudioFormat = Field(default_factory=AudioFormat)
    language: Optional[str] = Field(default=None, description="Expected or hint language code")
    prompt: Optional[str] = Field(default=None, description="Optional vocabulary prompt or context")


class STTResult(BaseModel):
    """Result output from an STT engine."""
    text: str = Field(default="")
    segments: List[TranscriptSegment] = Field(default_factory=list)
    language: str = Field(default="en")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_final: bool = Field(default=True)
    provider: str = Field(default="unknown")
    latency_ms: float = Field(default=0.0, ge=0.0)

    def to_transcript(self) -> Transcript:
        return Transcript(
            text=self.text,
            segments=self.segments,
            language=self.language,
            confidence=self.confidence,
            is_final=self.is_final,
            raw_text=self.text,
        )


class TTSRequest(BaseModel):
    """Request envelope for text-to-speech synthesis."""
    text: str = Field(..., min_length=1, description="Text to synthesize")
    voice: str = Field(default="af_heart", description="Voice identifier")
    speed: float = Field(default=1.0, ge=0.25, le=4.0, description="Speech rate multiplier")
    audio_format: AudioFormat = Field(default_factory=AudioFormat)


class TTSResult(BaseModel):
    """Complete synthesized audio payload."""
    audio_bytes: bytes = Field(..., description="Synthesized audio bytes")
    audio_format: AudioFormat = Field(default_factory=AudioFormat)
    duration_sec: float = Field(default=0.0, ge=0.0)
    chunk_count: int = Field(default=1, ge=1)
    provider: str = Field(default="kokoro")
    latency_ms: float = Field(default=0.0, ge=0.0)


class VoiceRequest(BaseModel):
    """Normalized voice request sent to the Agent Runtime."""
    session_id: str = Field(default_factory=lambda: f"vses_{uuid.uuid4().hex[:12]}")
    correlation_id: str = Field(default_factory=lambda: f"vcorr_{uuid.uuid4().hex[:12]}")
    transcript: Transcript = Field(..., description="Transcribed user speech")
    language: str = Field(default="en")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    audio_metadata: Optional[AudioMetadata] = Field(default=None)
    user_id: str = Field(default="default_user")
    created_at: float = Field(default_factory=time.time)

    @property
    def text(self) -> str:
        return self.transcript.text


class VoiceResponse(BaseModel):
    """Normalized voice response returned from the Voice Pipeline."""
    session_id: str
    correlation_id: str
    text: str = Field(..., description="Final textual answer")
    audio_metadata: Optional[AudioMetadata] = Field(default=None)
    agent_status: str = Field(default="completed")
    duration_sec: float = Field(default=0.0, ge=0.0)
    created_at: float = Field(default_factory=time.time)
