"""Speech-to-Text (STT) package."""

from jarvis.voice.stt.base import STTProvider
from jarvis.voice.stt.mock import MockSTTProvider
from jarvis.voice.stt.router import STTRouter
from jarvis.voice.stt.vosk import VoskSTTProvider
from jarvis.voice.stt.whisper import FasterWhisperSTTProvider

__all__ = [
    "STTProvider",
    "VoskSTTProvider",
    "FasterWhisperSTTProvider",
    "MockSTTProvider",
    "STTRouter",
]
