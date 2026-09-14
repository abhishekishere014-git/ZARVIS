"""Text-to-Speech (TTS) base protocol and chunk streaming contracts."""

from abc import ABC, abstractmethod
from typing import AsyncIterator
from jarvis.voice.models import AudioChunk, TTSRequest, TTSResult


class TTSProvider(ABC):
    """Abstract protocol for text-to-speech synthesis engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier of the TTS provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider dependencies and models are ready for synthesis."""
        pass

    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> TTSResult:
        """Synthesizes text into a single contiguous audio buffer."""
        pass

    @abstractmethod
    async def synthesize_stream(self, request: TTSRequest) -> AsyncIterator[AudioChunk]:
        """Synthesizes text incrementally and yields sequential audio chunks."""
        pass
