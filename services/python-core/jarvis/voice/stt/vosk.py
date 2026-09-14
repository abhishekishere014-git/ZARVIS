"""Vosk lightweight fast-path offline speech recognition provider."""

import json
import logging
import time
from pathlib import Path
from typing import List, Optional
from jarvis.voice.errors import STTError, STTProviderUnavailableError
from jarvis.voice.models import STTRequest, STTResult, TranscriptSegment
from jarvis.voice.stt.base import STTProvider

logger = logging.getLogger("jarvis.voice.stt.vosk")


class VoskSTTProvider(STTProvider):
    """Local, low-latency speech recognition using Vosk."""

    def __init__(self, model_path: Optional[Path] = None) -> None:
        self.model_path = model_path
        self._model = None
        self._vosk_module = None
        self._initialized = False
        self._probe_module()

    def _probe_module(self) -> None:
        try:
            import vosk  # type: ignore
            self._vosk_module = vosk
            vosk.SetLogLevel(-1)  # Quiet Vosk C-logs
        except ImportError:
            self._vosk_module = None

    @property
    def name(self) -> str:
        return "vosk"

    def is_available(self) -> bool:
        if not self._vosk_module:
            return False
        if not self.model_path or not self.model_path.exists():
            return False
        return True

    def _ensure_model_loaded(self) -> None:
        if self._initialized:
            return
        if not self.is_available():
            raise STTProviderUnavailableError(
                f"Vosk provider unavailable: vosk_installed={bool(self._vosk_module)}, model_exists={bool(self.model_path and self.model_path.exists())}"
            )
        try:
            self._model = self._vosk_module.Model(str(self.model_path))
            self._initialized = True
        except Exception as exc:
            raise STTError(f"Failed to load Vosk model from '{self.model_path}': {exc}")

    async def transcribe(self, request: STTRequest) -> STTResult:
        """Transcribes raw PCM or WAV data using Vosk Kaldi recognizer."""
        self._ensure_model_loaded()
        start_time = time.perf_counter()

        try:
            sample_rate = float(request.audio_format.sample_rate)
            rec = self._vosk_module.KaldiRecognizer(self._model, sample_rate)
            rec.SetWords(True)

            # Vosk accepts PCM stream
            rec.AcceptWaveform(request.audio_bytes)
            raw_res = rec.FinalResult()
            parsed = json.loads(raw_res)

            text = parsed.get("text", "").strip()
            segments: List[TranscriptSegment] = []
            words = parsed.get("result", [])
            total_conf = 0.0

            for word_info in words:
                word_conf = float(word_info.get("conf", 1.0))
                total_conf += word_conf
                segments.append(
                    TranscriptSegment(
                        text=word_info.get("word", ""),
                        start_sec=float(word_info.get("start", 0.0)),
                        end_sec=float(word_info.get("end", 0.0)),
                        confidence=word_conf,
                    )
                )

            avg_conf = total_conf / max(1, len(words)) if words else (0.9 if text else 0.0)
            latency = (time.perf_counter() - start_time) * 1000.0

            return STTResult(
                text=text,
                segments=segments,
                language="en",
                confidence=avg_conf,
                is_final=True,
                provider=self.name,
                latency_ms=latency,
            )
        except Exception as exc:
            raise STTError(f"Vosk recognition failed: {exc}")
