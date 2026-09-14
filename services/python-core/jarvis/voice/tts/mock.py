"""Scriptable Mock TTS provider for deterministic testing."""

import asyncio
import re
import time
from typing import AsyncIterator, List, Optional
from jarvis.voice.audio.base import generate_sine_wave
from jarvis.voice.errors import TTSError
from jarvis.voice.models import AudioChunk, AudioFormat, TTSRequest, TTSResult
from jarvis.voice.tts.base import TTSProvider


class MockTTSProvider(TTSProvider):
    """Predictable TTS provider for testing without external models."""

    def __init__(
        self,
        default_voice: str = "af_heart",
        provider_name: str = "mock",
        duration_per_char_sec: float = 0.01,
    ) -> None:
        self.default_voice = default_voice
        self._provider_name = provider_name
        self.duration_per_char_sec = duration_per_char_sec
        self._available = True
        self._raise_error: Optional[Exception] = None
        self.synthesize_count = 0

    @property
    def name(self) -> str:
        return self._provider_name

    def set_available(self, available: bool) -> None:
        self._available = available

    def set_error(self, error: Optional[Exception]) -> None:
        self._raise_error = error

    def is_available(self) -> bool:
        return self._available

    def _split_into_sentences(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[.?!;:\n])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()] or [text.strip()]

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        self.synthesize_count += 1
        if self._raise_error:
            raise self._raise_error

        fmt = request.audio_format or AudioFormat()
        duration = max(0.2, len(request.text) * self.duration_per_char_sec / max(0.25, request.speed))
        pcm_bytes = generate_sine_wave(
            frequency_hz=440.0,
            duration_sec=duration,
            sample_rate=fmt.sample_rate,
            amplitude=0.3,
        )

        return TTSResult(
            audio_bytes=pcm_bytes,
            audio_format=fmt,
            duration_sec=duration,
            chunk_count=1,
            provider=self.name,
            latency_ms=5.0,
        )

    async def synthesize_stream(self, request: TTSRequest) -> AsyncIterator[AudioChunk]:
        if self._raise_error:
            raise self._raise_error

        sentences = self._split_into_sentences(request.text)
        seq = 0
        fmt = request.audio_format or AudioFormat()

        for sentence in sentences:
            duration = max(0.1, len(sentence) * self.duration_per_char_sec / max(0.25, request.speed))
            pcm_bytes = generate_sine_wave(
                frequency_hz=440.0,
                duration_sec=duration,
                sample_rate=fmt.sample_rate,
                amplitude=0.3,
            )
            yield AudioChunk(
                data=pcm_bytes,
                sequence=seq,
                timestamp=time.time(),
                duration_sec=duration,
            )
            seq += 1
            await asyncio.sleep(0.001)
