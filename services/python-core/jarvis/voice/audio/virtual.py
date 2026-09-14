"""Virtual, memory-backed audio capture and playback for testing and headless runtimes."""

import asyncio
import time
from typing import List, Optional
from jarvis.voice.audio.base import BaseAudioCapture, BaseAudioPlayback
from jarvis.voice.models import AudioChunk, AudioFormat


class VirtualAudioCapture(BaseAudioCapture):
    """Feeds pre-configured or dynamically queued audio chunks into the capture pipeline."""

    def __init__(self, audio_format: Optional[AudioFormat] = None) -> None:
        self.audio_format = audio_format or AudioFormat()
        self._queue: asyncio.Queue[Optional[AudioChunk]] = asyncio.Queue()
        self._active = False
        self._seq = 0

    async def start(self) -> None:
        self._active = True

    async def stop(self) -> None:
        self._active = False
        # Push None sentinel to unblock any pending read
        await self._queue.put(None)

    def is_active(self) -> bool:
        return self._active

    async def read_chunk(self, timeout_sec: float = 1.0) -> Optional[AudioChunk]:
        if not self._active and self._queue.empty():
            return None
        try:
            chunk = await asyncio.wait_for(self._queue.get(), timeout=timeout_sec)
            return chunk
        except asyncio.TimeoutError:
            return None

    async def feed_pcm_data(self, pcm_bytes: bytes, chunk_duration_sec: float = 0.05) -> None:
        """Splits raw PCM bytes into timed chunks and enqueues them."""
        bytes_per_sec = self.audio_format.bytes_per_second
        chunk_size = int(bytes_per_sec * chunk_duration_sec)
        # Ensure even alignment
        chunk_size = chunk_size - (chunk_size % self.audio_format.frame_size)
        if chunk_size <= 0:
            chunk_size = self.audio_format.frame_size

        for i in range(0, len(pcm_bytes), chunk_size):
            slice_bytes = pcm_bytes[i : i + chunk_size]
            actual_duration = len(slice_bytes) / bytes_per_sec
            chunk = AudioChunk(
                data=slice_bytes,
                sequence=self._seq,
                timestamp=time.time(),
                duration_sec=actual_duration,
            )
            self._seq += 1
            await self._queue.put(chunk)

    async def feed_chunk(self, chunk: AudioChunk) -> None:
        """Enqueues a single audio chunk directly."""
        await self._queue.put(chunk)


class VirtualAudioPlayback(BaseAudioPlayback):
    """Accumulates played audio chunks into memory for test verification."""

    def __init__(self) -> None:
        self._played_chunks: List[AudioChunk] = []
        self._is_playing = False
        self._interrupted = False

    async def start(self) -> None:
        self._is_playing = True
        self._interrupted = False

    async def stop(self) -> None:
        self._is_playing = False
        self._interrupted = True

    async def play_chunk(self, chunk: AudioChunk) -> None:
        if self._interrupted:
            return
        self._played_chunks.append(chunk)

    async def drain(self) -> None:
        self._is_playing = False

    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def played_bytes(self) -> bytes:
        return b"".join(c.data for c in self._played_chunks)

    @property
    def total_chunks_played(self) -> int:
        return len(self._played_chunks)

    def reset(self) -> None:
        self._played_chunks.clear()
        self._is_playing = False
        self._interrupted = False
