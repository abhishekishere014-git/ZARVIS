"""Scriptable Mock Voice Activity Detector for testing."""

import time
from typing import List
from jarvis.voice.models import AudioChunk, VADResult
from jarvis.voice.vad.base import VADProvider


class MockVAD(VADProvider):
    """Predictable VAD provider that returns scripted speech decisions."""

    def __init__(self, default_speech: bool = False) -> None:
        self.default_speech = default_speech
        self._scripted_sequence: List[bool] = []
        self._call_count = 0

    def script_decisions(self, decisions: List[bool]) -> None:
        """Sets a sequence of boolean decisions returned on sequential chunks."""
        self._scripted_sequence = list(decisions)
        self._call_count = 0

    def reset(self) -> None:
        self._call_count = 0

    def process_chunk(self, chunk: AudioChunk) -> VADResult:
        if self._call_count < len(self._scripted_sequence):
            is_speech = self._scripted_sequence[self._call_count]
        else:
            is_speech = self.default_speech
        self._call_count += 1

        return VADResult(
            is_speech=is_speech,
            confidence=1.0 if is_speech else 0.0,
            energy=1000.0 if is_speech else 50.0,
            timestamp=time.time(),
        )
