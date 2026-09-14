"""Faster-Whisper high-accuracy local speech recognition provider."""

import io
import logging
import time
from typing import List, Optional
from jarvis.voice.audio.base import pcm_to_wav
from jarvis.voice.errors import STTError, STTProviderUnavailableError
from jarvis.voice.models import AudioEncoding, STTRequest, STTResult, TranscriptSegment
from jarvis.voice.stt.base import STTProvider

logger = logging.getLogger("jarvis.voice.stt.whisper")


class FasterWhisperSTTProvider(STTProvider):
    """High-accuracy multi-lingual speech recognition using Faster-Whisper."""

    def __init__(
        self,
        model_size_or_path: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_size_or_path = model_size_or_path
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._whisper_module = None
        self._initialized = False
        self._probe_module()

    def _probe_module(self) -> None:
        try:
            import faster_whisper  # type: ignore
            self._whisper_module = faster_whisper
        except ImportError:
            self._whisper_module = None

    @property
    def name(self) -> str:
        return "whisper"

    def is_available(self) -> bool:
        return self._whisper_module is not None

    def _ensure_model_loaded(self) -> None:
        if self._initialized:
            return
        if not self.is_available():
            raise STTProviderUnavailableError(
                "Faster-Whisper provider unavailable: faster_whisper package is not installed."
            )
        try:
            self._model = self._whisper_module.WhisperModel(
                self.model_size_or_path,
                device=self.device,
                compute_type=self.compute_type,
            )
            self._initialized = True
        except Exception as exc:
            raise STTError(f"Failed to load Faster-Whisper model '{self.model_size_or_path}': {exc}")

    async def transcribe(self, request: STTRequest) -> STTResult:
        """Transcribes audio using Faster-Whisper CT2 engine."""
        self._ensure_model_loaded()
        start_time = time.perf_counter()

        try:
            # Faster-whisper accepts file-like binary stream of WAV audio
            wav_bytes = (
                request.audio_bytes
                if request.audio_format.encoding == AudioEncoding.WAV
                else pcm_to_wav(request.audio_bytes, request.audio_format)
            )
            wav_stream = io.BytesIO(wav_bytes)

            segments_iter, info = self._model.transcribe(
                wav_stream,
                language=request.language,
                initial_prompt=request.prompt,
                beam_size=5,
            )

            segments: List[TranscriptSegment] = []
            text_parts = []
            total_prob = 0.0

            for seg in segments_iter:
                seg_text = seg.text.strip()
                text_parts.append(seg_text)
                seg_prob = float(getattr(seg, "avg_logprob", -0.2))
                # Map logprob to 0.0-1.0 confidence approximation
                confidence = max(0.1, min(1.0, 1.0 + seg_prob / 3.0))
                total_prob += confidence
                segments.append(
                    TranscriptSegment(
                        text=seg_text,
                        start_sec=float(seg.start),
                        end_sec=float(seg.end),
                        confidence=confidence,
                        language=info.language,
                    )
                )

            full_text = " ".join(text_parts).strip()
            detected_lang = getattr(info, "language", "en") or "en"
            avg_conf = total_prob / max(1, len(segments)) if segments else 0.8
            latency = (time.perf_counter() - start_time) * 1000.0

            return STTResult(
                text=full_text,
                segments=segments,
                language=detected_lang,
                confidence=avg_conf,
                is_final=True,
                provider=self.name,
                latency_ms=latency,
            )
        except Exception as exc:
            raise STTError(f"Faster-Whisper transcription failed: {exc}")
