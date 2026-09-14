"""Kokoro ONNX local text-to-speech provider."""

import asyncio
import logging
import re
import struct
import time
from pathlib import Path
from typing import AsyncIterator, List, Optional
from jarvis.voice.errors import TTSError, TTSProviderUnavailableError
from jarvis.voice.models import AudioChunk, AudioFormat, TTSRequest, TTSResult
from jarvis.voice.tts.base import TTSProvider

logger = logging.getLogger("jarvis.voice.tts.kokoro")


class KokoroTTSProvider(TTSProvider):
    """High-quality local speech synthesis using Kokoro ONNX."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        voices_path: Optional[Path] = None,
        default_voice: str = "af_heart",
        default_speed: float = 1.0,
    ) -> None:
        self.model_path = model_path
        self.voices_path = voices_path
        self.default_voice = default_voice
        self.default_speed = default_speed
        self._kokoro = None
        self._kokoro_module = None
        self._initialized = False
        self._probe_module()

    def _probe_module(self) -> None:
        try:
            import kokoro_onnx  # type: ignore
            self._kokoro_module = kokoro_onnx
        except ImportError:
            self._kokoro_module = None

    @property
    def name(self) -> str:
        return "kokoro"

    def is_available(self) -> bool:
        if not self._kokoro_module:
            return False
        if not self.model_path or not self.model_path.exists():
            return False
        return True

    def _ensure_model_loaded(self) -> None:
        if self._initialized:
            return
        if not self.is_available():
            raise TTSProviderUnavailableError(
                f"Kokoro ONNX provider unavailable: module_installed={bool(self._kokoro_module)}, model_exists={bool(self.model_path and self.model_path.exists())}"
            )
        try:
            voices_file = str(self.voices_path) if self.voices_path and self.voices_path.exists() else None
            self._kokoro = self._kokoro_module.Kokoro(str(self.model_path), voices_file)
            self._initialized = True
        except Exception as exc:
            raise TTSError(f"Failed to load Kokoro ONNX model from '{self.model_path}': {exc}")

    def _split_into_sentences(self, text: str) -> List[str]:
        """Splits long text into sentence fragments for streaming synthesis."""
        sentences = re.split(r"(?<=[.?!;:\n])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        """Synthesizes text into contiguous PCM bytes."""
        self._ensure_model_loaded()
        start_time = time.perf_counter()

        voice = request.voice or self.default_voice
        speed = request.speed or self.default_speed

        try:
            # kokoro create returns (samples, sample_rate)
            samples, sample_rate = await asyncio.to_thread(
                self._kokoro.create,
                request.text,
                voice=voice,
                speed=speed,
            )
            # Convert float32 numpy samples to 16-bit PCM bytes
            pcm_data = b""
            if hasattr(samples, "tobytes"):
                import numpy as np  # type: ignore
                int16_samples = (samples * 32767.0).clip(-32768, 32767).astype(np.int16)
                pcm_data = int16_samples.tobytes()
            else:
                # Fallback iteration
                int16_list = [int(max(-32768, min(32767, s * 32767.0))) for s in samples]
                pcm_data = struct.pack(f"<{len(int16_list)}h", *int16_list)

            out_fmt = AudioFormat(sample_rate=sample_rate, channels=1, sample_width=2)
            duration = len(pcm_data) / out_fmt.bytes_per_second if out_fmt.bytes_per_second > 0 else 0.0
            latency = (time.perf_counter() - start_time) * 1000.0

            return TTSResult(
                audio_bytes=pcm_data,
                audio_format=out_fmt,
                duration_sec=duration,
                chunk_count=1,
                provider=self.name,
                latency_ms=latency,
            )
        except Exception as exc:
            raise TTSError(f"Kokoro synthesis failed: {exc}")

    async def synthesize_stream(self, request: TTSRequest) -> AsyncIterator[AudioChunk]:
        """Streams synthesized sentence chunks incrementally."""
        sentences = self._split_into_sentences(request.text)
        if not sentences:
            return

        seq = 0
        for sentence in sentences:
            sentence_req = TTSRequest(
                text=sentence,
                voice=request.voice,
                speed=request.speed,
                audio_format=request.audio_format,
            )
            result = await self.synthesize(sentence_req)
            yield AudioChunk(
                data=result.audio_bytes,
                sequence=seq,
                timestamp=time.time(),
                duration_sec=result.duration_sec,
            )
            seq += 1
