"""Voice Activity Detection (VAD) protocols and segmentation engine."""

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from jarvis.voice.errors import VADError, VoiceTimeoutError
from jarvis.voice.models import AudioChunk, AudioFormat, VADResult

logger = logging.getLogger("jarvis.voice.vad.base")


class VADProvider(ABC):
    """Abstract interface for Voice Activity Detection algorithms."""

    @abstractmethod
    def process_chunk(self, chunk: AudioChunk) -> VADResult:
        """Evaluates whether an audio chunk contains human speech."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets internal filters, hangover counters, and noise estimates."""
        pass


class VADSegmenter:
    """Stateful stream processor segmenting speech utterances between silence boundaries."""

    def __init__(
        self,
        vad_provider: VADProvider,
        audio_format: Optional[AudioFormat] = None,
        silence_timeout_sec: float = 1.2,
        min_speech_duration_sec: float = 0.3,
        max_utterance_duration_sec: float = 30.0,
        pre_speech_padding_chunks: int = 4,
    ) -> None:
        self.vad = vad_provider
        self.audio_format = audio_format or AudioFormat()
        self.silence_timeout_sec = silence_timeout_sec
        self.min_speech_duration_sec = min_speech_duration_sec
        self.max_utterance_duration_sec = max_utterance_duration_sec
        self.pre_speech_padding_chunks = pre_speech_padding_chunks

        self._pre_speech_buffer: List[AudioChunk] = []
        self._speech_buffer: List[AudioChunk] = []
        self._speech_detected = False
        self._speech_start_time: Optional[float] = None
        self._last_speech_time: Optional[float] = None
        self._utterance_start_time: Optional[float] = None

    def reset(self) -> None:
        """Resets segmenter state for a new utterance."""
        self.vad.reset()
        self._pre_speech_buffer.clear()
        self._speech_buffer.clear()
        self._speech_detected = False
        self._speech_start_time = None
        self._last_speech_time = None
        self._utterance_start_time = None

    @property
    def is_in_speech(self) -> bool:
        return self._speech_detected

    def process_chunk(self, chunk: AudioChunk) -> Tuple[bool, Optional[bytes]]:
        """Processes an incoming audio chunk.
        
        Returns:
            (is_complete, speech_bytes_or_none)
            - is_complete: True when an utterance has completed (or max duration reached)
            - speech_bytes: The complete contiguous PCM byte buffer if complete, else None.
        """
        now = time.time()
        if self._utterance_start_time is None:
            self._utterance_start_time = now

        vad_result = self.vad.process_chunk(chunk)
        chunk.is_speech = vad_result.is_speech

        # Enforce hard upper bound on total session recording duration
        if now - self._utterance_start_time > self.max_utterance_duration_sec:
            logger.warning("Utterance exceeded maximum duration limit of %.1fs", self.max_utterance_duration_sec)
            return self._finalize(forced=True)

        if vad_result.is_speech:
            if not self._speech_detected:
                # Speech onset detected!
                self._speech_detected = True
                self._speech_start_time = now
                logger.debug("VAD: Speech onset detected")
                # Prepend pre-speech padding buffer so word starts aren't clipped
                self._speech_buffer.extend(self._pre_speech_buffer)
                self._pre_speech_buffer.clear()

            self._last_speech_time = now
            self._speech_buffer.append(chunk)
            return False, None

        else:
            # Silence or non-speech chunk
            if not self._speech_detected:
                # Keep rolling pre-speech padding buffer
                self._pre_speech_buffer.append(chunk)
                if len(self._pre_speech_buffer) > self.pre_speech_padding_chunks:
                    self._pre_speech_buffer.pop(0)
                return False, None

            # Speech was ongoing, now encountering silence
            self._speech_buffer.append(chunk)
            silence_duration = now - (self._last_speech_time or now)
            if silence_duration >= self.silence_timeout_sec:
                logger.debug("VAD: Speech end detected (silence duration %.2fs)", silence_duration)
                return self._finalize(forced=False)

            return False, None

    def _finalize(self, forced: bool = False) -> Tuple[bool, Optional[bytes]]:
        """Finalizes the accumulated speech utterance."""
        if not self._speech_buffer:
            self.reset()
            return True, b""

        # Calculate total speech duration
        total_bytes = sum(len(c.data) for c in self._speech_buffer)
        bytes_per_sec = self.audio_format.bytes_per_second
        duration_sec = total_bytes / bytes_per_sec if bytes_per_sec > 0 else 0.0

        if not forced and duration_sec < self.min_speech_duration_sec:
            logger.debug("Discarding utterance below minimum duration (%.2fs < %.2fs)", duration_sec, self.min_speech_duration_sec)
            self.reset()
            return False, None

        full_pcm = b"".join(c.data for c in self._speech_buffer)
        self.reset()
        return True, full_pcm
