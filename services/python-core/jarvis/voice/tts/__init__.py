"""Text-to-Speech (TTS) module."""

from jarvis.voice.tts.base import TTSProvider
from jarvis.voice.tts.kokoro import KokoroTTSProvider
from jarvis.voice.tts.mock import MockTTSProvider

__all__ = [
    "TTSProvider",
    "KokoroTTSProvider",
    "MockTTSProvider",
]
