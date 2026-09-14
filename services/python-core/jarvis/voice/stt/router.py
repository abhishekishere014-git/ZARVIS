"""Intelligent STT Router implementing Vosk fast-path and Whisper escalation."""

import logging
from typing import Dict, List, Optional
from jarvis.voice.errors import STTError, STTProviderUnavailableError
from jarvis.voice.models import STTRequest, STTResult
from jarvis.voice.stt.base import STTProvider

logger = logging.getLogger("jarvis.voice.stt.router")


class STTRouter:
    """Routes speech transcription requests between low-latency and high-accuracy engines."""

    def __init__(
        self,
        providers: Dict[str, STTProvider],
        fastpath_provider: str = "vosk",
        accurate_provider: str = "whisper",
        confidence_threshold: float = 0.75,
        fastpath_max_duration_sec: float = 5.0,
    ) -> None:
        self.providers = providers
        self.fastpath_provider = fastpath_provider
        self.accurate_provider = accurate_provider
        self.confidence_threshold = confidence_threshold
        self.fastpath_max_duration_sec = fastpath_max_duration_sec

    def get_available_providers(self) -> List[str]:
        return [name for name, p in self.providers.items() if p.is_available()]

    async def transcribe(self, request: STTRequest) -> STTResult:
        """Executes smart routing with fallback and confidence escalation."""
        # Calculate duration of the audio
        bytes_per_sec = request.audio_format.bytes_per_second
        duration_sec = len(request.audio_bytes) / bytes_per_sec if bytes_per_sec > 0 else 0.0

        fast = self.providers.get(self.fastpath_provider)
        accurate = self.providers.get(self.accurate_provider)

        # 1. Check if eligible for fast-path
        eligible_for_fastpath = (
            fast is not None
            and fast.is_available()
            and duration_sec <= self.fastpath_max_duration_sec
        )

        if eligible_for_fastpath:
            try:
                logger.debug("Routing to STT fast-path provider '%s' (duration: %.2fs)", self.fastpath_provider, duration_sec)
                fast_result = await fast.transcribe(request)

                # If fast-path yielded satisfactory confidence, return immediately
                if fast_result.confidence >= self.confidence_threshold and fast_result.text.strip():
                    logger.debug("Fast-path succeeded with confidence %.2f", fast_result.confidence)
                    return fast_result

                logger.info(
                    "Fast-path confidence (%.2f) below threshold (%.2f) or empty. Escalating to accurate provider '%s'.",
                    fast_result.confidence,
                    self.confidence_threshold,
                    self.accurate_provider,
                )
            except Exception as exc:
                logger.warning("Fast-path provider '%s' failed: %s. Escalating to accurate provider.", self.fastpath_provider, exc)

        # 2. Accurate provider path (e.g. Whisper)
        if accurate is not None and accurate.is_available():
            try:
                logger.debug("Routing to accurate STT provider '%s'", self.accurate_provider)
                return await accurate.transcribe(request)
            except Exception as exc:
                logger.warning("Accurate provider '%s' failed: %s", self.accurate_provider, exc)

        # 3. Fallback to any other available provider
        for name, provider in self.providers.items():
            if name not in (self.fastpath_provider, self.accurate_provider) and provider.is_available():
                try:
                    logger.info("Falling back to auxiliary STT provider '%s'", name)
                    return await provider.transcribe(request)
                except Exception as exc:
                    logger.warning("Auxiliary provider '%s' failed: %s", name, exc)

        # 4. If all failed, raise deterministic error
        raise STTProviderUnavailableError(
            "No STT provider was available or able to transcribe the audio payload.",
            details={"configured_providers": list(self.providers.keys()), "duration_sec": duration_sec},
        )
