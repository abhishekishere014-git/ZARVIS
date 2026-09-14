"""Scriptable Mock STT provider for deterministic testing."""

import time
from typing import List, Optional
from jarvis.voice.errors import STTError
from jarvis.voice.models import STTRequest, STTResult, TranscriptSegment
from jarvis.voice.stt.base import STTProvider


class MockSTTProvider(STTProvider):
    """Predictable STT provider for unit tests and offline pipelines."""

    def __init__(
        self,
        default_text: str = "Hello Jarvis",
        confidence: float = 0.95,
        language: str = "en",
        provider_name: str = "mock",
    ) -> None:
        self.default_text = default_text
        self.confidence = confidence
        self.language = language
        self._provider_name = provider_name
        self._available = True
        self._scripted_results: List[STTResult] = []
        self._raise_error: Optional[Exception] = None
        self.transcribe_count = 0

    @property
    def name(self) -> str:
        return self._provider_name

    def set_available(self, available: bool) -> None:
        self._available = available

    def set_error(self, error: Optional[Exception]) -> None:
        self._raise_error = error

    def script_result(self, result: STTResult) -> None:
        self._scripted_results.append(result)

    def is_available(self) -> bool:
        return self._available

    async def transcribe(self, request: STTRequest) -> STTResult:
        self.transcribe_count += 1
        if self._raise_error:
            raise self._raise_error

        if self._scripted_results:
            return self._scripted_results.pop(0)

        # Estimate duration from bytes
        duration = 1.0
        if request.audio_format.bytes_per_second > 0:
            duration = len(request.audio_bytes) / request.audio_format.bytes_per_second

        return STTResult(
            text=self.default_text,
            segments=[
                TranscriptSegment(
                    text=self.default_text,
                    start_sec=0.0,
                    end_sec=duration,
                    confidence=self.confidence,
                    language=request.language or self.language,
                )
            ],
            language=request.language or self.language,
            confidence=self.confidence,
            is_final=True,
            provider=self.name,
            latency_ms=10.0,
        )
