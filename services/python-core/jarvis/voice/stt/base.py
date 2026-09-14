"""Speech-to-Text (STT) base protocols and contracts."""

from abc import ABC, abstractmethod
from typing import Optional
from jarvis.voice.models import STTRequest, STTResult


class STTProvider(ABC):
    """Abstract protocol for speech recognition engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier of the STT provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider dependencies and models are ready for inference."""
        pass

    @abstractmethod
    async def transcribe(self, request: STTRequest) -> STTResult:
        """Transcribes the given audio request into normalized text and metadata."""
        pass
