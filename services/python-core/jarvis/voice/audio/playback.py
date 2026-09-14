"""High-level audio playback controller supporting cancellation and barge-in."""

import asyncio
import logging
from typing import Optional
from jarvis.voice.audio.base import BaseAudioPlayback
from jarvis.voice.audio.device import AudioDeviceManager
from jarvis.voice.audio.virtual import VirtualAudioPlayback
from jarvis.voice.errors import AudioPlaybackError
from jarvis.voice.models import AudioChunk, AudioFormat

logger = logging.getLogger("jarvis.voice.audio.playback")


class AudioPlayback:
    """Controls speaker or virtual audio stream playback."""

    def __init__(
        self,
        audio_format: Optional[AudioFormat] = None,
        device_manager: Optional[AudioDeviceManager] = None,
        virtual_backend: Optional[BaseAudioPlayback] = None,
    ) -> None:
        self.audio_format = audio_format or AudioFormat()
        self.device_manager = device_manager or AudioDeviceManager()
        self._backend: BaseAudioPlayback = virtual_backend or VirtualAudioPlayback()
        self._interrupted = False
        self._is_playing = False

    @property
    def backend(self) -> BaseAudioPlayback:
        return self._backend

    def set_backend(self, backend: BaseAudioPlayback) -> None:
        self._backend = backend

    async def start(self) -> None:
        """Starts the playback sink."""
        self._interrupted = False
        self._is_playing = True
        await self._backend.start()

    async def stop(self) -> None:
        """Immediately interrupts playback and drains active buffers."""
        self._interrupted = True
        self._is_playing = False
        await self._backend.stop()

    def is_playing(self) -> bool:
        return self._is_playing and self._backend.is_playing()

    async def play_chunk(self, chunk: AudioChunk) -> None:
        """Plays an individual audio chunk unless interrupted."""
        if self._interrupted or not self._is_playing:
            return
        await self._backend.play_chunk(chunk)

    async def play_bytes(self, pcm_bytes: bytes, chunk_duration_sec: float = 0.05) -> None:
        """Plays an entire PCM buffer as timed chunks, checking for interruption between chunks."""
        await self.start()
        bytes_per_sec = self.audio_format.bytes_per_second
        chunk_size = int(bytes_per_sec * chunk_duration_sec)
        chunk_size = chunk_size - (chunk_size % self.audio_format.frame_size)
        if chunk_size <= 0:
            chunk_size = self.audio_format.frame_size

        try:
            seq = 0
            for i in range(0, len(pcm_bytes), chunk_size):
                if self._interrupted:
                    logger.info("Playback interrupted during play_bytes")
                    break
                chunk_data = pcm_bytes[i : i + chunk_size]
                chunk = AudioChunk(
                    data=chunk_data,
                    sequence=seq,
                    duration_sec=len(chunk_data) / bytes_per_sec,
                )
                seq += 1
                await self._backend.play_chunk(chunk)
                # Yield control to event loop so cancellation or barge-in can be processed
                await asyncio.sleep(0.001)

            if not self._interrupted:
                await self._backend.drain()
        finally:
            self._is_playing = False
