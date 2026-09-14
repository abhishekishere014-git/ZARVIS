"""Base protocols and audio conversion utilities for JARVIS Voice & Audio."""

import io
import math
import struct
import wave
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from jarvis.voice.errors import AudioCaptureError, AudioPlaybackError, UnsupportedAudioFormatError
from jarvis.voice.models import AudioChunk, AudioFormat


class BaseAudioCapture(ABC):
    """Abstract interface for audio capture sources."""

    @abstractmethod
    async def start(self) -> None:
        """Starts capturing audio stream."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stops capturing audio stream."""
        pass

    @abstractmethod
    async def read_chunk(self, timeout_sec: float = 1.0) -> Optional[AudioChunk]:
        """Reads the next available audio chunk from the buffer."""
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Returns True if the capture stream is running."""
        pass


class BaseAudioPlayback(ABC):
    """Abstract interface for audio playback sinks."""

    @abstractmethod
    async def start(self) -> None:
        """Initializes playback stream."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stops playback immediately and drains buffers."""
        pass

    @abstractmethod
    async def play_chunk(self, chunk: AudioChunk) -> None:
        """Plays a discrete audio chunk."""
        pass

    @abstractmethod
    async def drain(self) -> None:
        """Waits for queued audio to complete playback."""
        pass

    @abstractmethod
    def is_playing(self) -> bool:
        """Returns True if audio is actively playing."""
        pass


def calculate_pcm_rms(pcm_bytes: bytes, sample_width: int = 2) -> float:
    """Calculates root-mean-square (RMS) energy of 16-bit PCM bytes using pure standard library."""
    if not pcm_bytes or len(pcm_bytes) < sample_width:
        return 0.0

    if sample_width != 2:
        # Fallback for non-16-bit
        return 0.0

    num_samples = len(pcm_bytes) // 2
    format_str = f"<{num_samples}h"
    try:
        samples = struct.unpack(format_str, pcm_bytes[: num_samples * 2])
    except struct.error:
        return 0.0

    sum_squares = sum(s * s for s in samples)
    mean_square = sum_squares / max(1, num_samples)
    return math.sqrt(mean_square)


def pcm_to_wav(pcm_bytes: bytes, audio_format: AudioFormat) -> bytes:
    """Encapsulates raw PCM byte stream inside a standard WAV container."""
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wav_file:
        wav_file.setnchannels(audio_format.channels)
        wav_file.setsampwidth(audio_format.sample_width)
        wav_file.setframerate(audio_format.sample_rate)
        wav_file.writeframes(pcm_bytes)
    return wav_io.getvalue()


def wav_to_pcm(wav_bytes: bytes) -> tuple[bytes, AudioFormat]:
    """Extracts raw PCM frames and AudioFormat from a standard WAV container."""
    wav_io = io.BytesIO(wav_bytes)
    try:
        with wave.open(wav_io, "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())
            fmt = AudioFormat(
                sample_rate=sample_rate,
                channels=channels,
                sample_width=sample_width,
            )
            return frames, fmt
    except wave.Error as exc:
        raise UnsupportedAudioFormatError(f"Malformed or unsupported WAV data: {exc}")


def generate_sine_wave(
    frequency_hz: float = 440.0,
    duration_sec: float = 1.0,
    sample_rate: int = 16000,
    amplitude: float = 0.5,
) -> bytes:
    """Generates synthetic 16-bit PCM sine wave bytes for testing."""
    num_samples = int(duration_sec * sample_rate)
    max_amp = 32767.0 * min(1.0, max(0.0, amplitude))
    samples = []
    for i in range(num_samples):
        val = int(max_amp * math.sin(2.0 * math.pi * frequency_hz * i / sample_rate))
        samples.append(val)
    return struct.pack(f"<{num_samples}h", *samples)
