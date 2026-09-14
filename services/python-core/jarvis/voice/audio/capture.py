"""High-level audio capture controller with buffering and limit enforcement."""

import asyncio
import logging
import time
from typing import Optional
from jarvis.voice.audio.base import BaseAudioCapture
from jarvis.voice.audio.device import AudioDeviceManager
from jarvis.voice.audio.virtual import VirtualAudioCapture
from jarvis.voice.errors import AudioCaptureError, VoiceTimeoutError
from jarvis.voice.models import AudioChunk, AudioFormat, AudioMetadata

logger = logging.getLogger("jarvis.voice.audio.capture")


class AudioCapture:
    """Controls microphone or virtual audio stream capture."""

    def __init__(
        self,
        audio_format: Optional[AudioFormat] = None,
        device_manager: Optional[AudioDeviceManager] = None,
        max_duration_sec: float = 30.0,
        virtual_backend: Optional[BaseAudioCapture] = None,
    ) -> None:
        self.audio_format = audio_format or AudioFormat()
        self.device_manager = device_manager or AudioDeviceManager()
        self.max_duration_sec = max_duration_sec
        self._backend: BaseAudioCapture = virtual_backend or VirtualAudioCapture(self.audio_format)
        self._start_time: float = 0.0
        self._total_bytes_captured = 0
        self._is_capturing = False

    @property
    def backend(self) -> BaseAudioCapture:
        return self._backend

    def set_backend(self, backend: BaseAudioCapture) -> None:
        self._backend = backend

    async def start(self) -> None:
        """Starts the capture session."""
        self._start_time = time.time()
        self._total_bytes_captured = 0
        self._is_capturing = True
        await self._backend.start()

    async def stop(self) -> None:
        """Stops the capture session."""
        self._is_capturing = False
        await self._backend.stop()

    def is_capturing(self) -> bool:
        return self._is_capturing and self._backend.is_active()

    async def read_chunk(self, timeout_sec: float = 1.0) -> Optional[AudioChunk]:
        """Reads the next audio chunk while enforcing duration limits."""
        if not self._is_capturing:
            return None

        # Check duration limit
        elapsed = time.time() - self._start_time
        if elapsed > self.max_duration_sec:
            logger.warning("Capture exceeded maximum duration of %.1fs", self.max_duration_sec)
            await self.stop()
            raise VoiceTimeoutError(
                f"Audio recording exceeded maximum duration limit of {self.max_duration_sec}s",
                details={"elapsed_sec": elapsed, "max_sec": self.max_duration_sec},
            )

        chunk = await self._backend.read_chunk(timeout_sec)
        if chunk:
            self._total_bytes_captured += len(chunk.data)
        return chunk

    def get_metadata(self) -> AudioMetadata:
        """Constructs AudioMetadata for the current/most recent recording."""
        duration = 0.0
        if self._start_time > 0:
            duration = time.time() - self._start_time
        bytes_per_sec = self.audio_format.bytes_per_second
        if bytes_per_sec > 0 and self._total_bytes_captured > 0:
            duration = self._total_bytes_captured / bytes_per_sec

        frame_count = (
            self._total_bytes_captured // self.audio_format.frame_size
            if self.audio_format.frame_size > 0
            else 0
        )
        return AudioMetadata(
            duration_sec=duration,
            frame_count=frame_count,
            sample_rate=self.audio_format.sample_rate,
            channels=self.audio_format.channels,
            sample_width=self.audio_format.sample_width,
            file_size_bytes=self._total_bytes_captured,
            created_at=self._start_time or time.time(),
        )
