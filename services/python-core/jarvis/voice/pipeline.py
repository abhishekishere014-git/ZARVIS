"""End-to-end Voice & Audio Pipeline integrating Audio, VAD, STT, Agents, Memory, and TTS."""

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, Optional
from jarvis.agents.orchestrator import AgentOrchestrator
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent
from jarvis.voice.audio.capture import AudioCapture
from jarvis.voice.audio.playback import AudioPlayback
from jarvis.voice.config import VoiceConfig
from jarvis.voice.errors import VoiceError, VoiceInterruptedError, VoiceTimeoutError
from jarvis.voice.models import (
    AudioChunk,
    AudioFormat,
    AudioMetadata,
    STTRequest,
    Transcript,
    TTSRequest,
    VoiceRequest,
    VoiceResponse,
    VoiceSessionState,
)
from jarvis.voice.security.manager import AudioSecurityManager
from jarvis.voice.session import VoiceSession
from jarvis.voice.stt.router import STTRouter
from jarvis.voice.tts.base import TTSProvider
from jarvis.voice.vad.base import VADSegmenter

logger = logging.getLogger("jarvis.voice.pipeline")


class VoicePipeline:
    """Orchestrates audio capture, VAD segmentation, STT transcription,

    agent reasoning, TTS synthesis, and audio playback.
    """

    def __init__(
        self,
        config: VoiceConfig,
        capture: AudioCapture,
        playback: AudioPlayback,
        vad_segmenter: VADSegmenter,
        stt_router: STTRouter,
        tts_provider: TTSProvider,
        orchestrator: Optional[AgentOrchestrator] = None,
        event_bus: Optional[AsyncEventBus] = None,
        security_manager: Optional[AudioSecurityManager] = None,
    ) -> None:
        self.config = config
        self.capture = capture
        self.playback = playback
        self.vad_segmenter = vad_segmenter
        self.stt_router = stt_router
        self.tts_provider = tts_provider
        self.orchestrator = orchestrator
        self.event_bus = event_bus
        self.security = security_manager or AudioSecurityManager(
            temp_dir=config.temp_dir,
            max_recording_duration_sec=config.max_recording_duration_sec,
            max_audio_size_bytes=config.max_audio_size_bytes,
            persist_raw_audio=config.persist_raw_audio,
        )

    async def _emit_event(
        self,
        event_type: str,
        session_id: str,
        correlation_id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emits correlated voice lifecycle event to AsyncEventBus."""
        if not self.event_bus or not self.event_bus.is_running:
            return

        raw_payload = {
            "session_id": session_id,
            "correlation_id": correlation_id,
            "timestamp": time.time(),
            **(payload or {}),
        }
        # Guarantee no raw audio bytes or secrets leak into event payloads
        safe_payload = self.security.scrub_telemetry_payload(raw_payload)

        event = JarvisEvent(
            id=f"evt_voice_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}",
            type=event_type,
            correlation_id=correlation_id,
            payload=safe_payload,
        )
        try:
            await self.event_bus.publish(event)
        except Exception as exc:
            logger.warning("Failed to publish voice event '%s': %s", event_type, exc)

    async def listen_once(
        self,
        session: VoiceSession,
        timeout_sec: float = 10.0,
    ) -> Optional[bytes]:
        """Captures audio until an utterance completes via VAD or timeout."""
        correlation_id = f"vcorr_{uuid.uuid4().hex[:12]}"
        await self._emit_event("voice.listening.started", session.session_id, correlation_id)
        session.start_listening()
        self.vad_segmenter.reset()

        await self.capture.start()
        start_time = time.time()
        try:
            while time.time() - start_time < timeout_sec:
                chunk = await self.capture.read_chunk(timeout_sec=0.2)
                if not chunk:
                    continue

                is_complete, speech_bytes = self.vad_segmenter.process_chunk(chunk)
                if is_complete:
                    await self._emit_event(
                        "voice.listening.stopped",
                        session.session_id,
                        correlation_id,
                        {"speech_detected": bool(speech_bytes), "duration_sec": time.time() - start_time},
                    )
                    return speech_bytes

            # Timeout without speech
            await self._emit_event(
                "voice.listening.stopped",
                session.session_id,
                correlation_id,
                {"speech_detected": False, "timed_out": True},
            )
            return None
        finally:
            await self.capture.stop()

    async def transcribe(
        self,
        audio_bytes: bytes,
        audio_format: Optional[AudioFormat] = None,
        session_id: str = "default_session",
        correlation_id: str = "default_corr",
    ) -> Transcript:
        """Transcribes audio bytes using the intelligent STT router."""
        self.security.validate_audio_size(audio_bytes)
        fmt = audio_format or self.capture.audio_format
        self.security.validate_audio_format(fmt)

        await self._emit_event(
            "voice.transcription.started",
            session_id,
            correlation_id,
            {"bytes": len(audio_bytes), "format": fmt.encoding.value},
        )
        t0 = time.perf_counter()
        req = STTRequest(audio_bytes=audio_bytes, audio_format=fmt)
        result = await self.stt_router.transcribe(req)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        await self._emit_event(
            "voice.transcription.completed",
            session_id,
            correlation_id,
            {
                "text": result.text,
                "confidence": result.confidence,
                "provider": result.provider,
                "latency_ms": latency_ms,
            },
        )
        return result.to_transcript()

    async def synthesize_and_play(
        self,
        text: str,
        session: VoiceSession,
        correlation_id: str,
    ) -> AudioMetadata:
        """Synthesizes text to speech and plays audio, supporting barge-in interruptions."""
        await self._emit_event(
            "voice.tts.started",
            session.session_id,
            correlation_id,
            {"text_length": len(text), "provider": self.tts_provider.name},
        )
        t0 = time.perf_counter()
        tts_req = TTSRequest(
            text=text,
            voice=self.config.tts_voice,
            speed=self.config.tts_speed,
            audio_format=self.capture.audio_format,
        )
        tts_res = await self.tts_provider.synthesize(tts_req)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        await self._emit_event(
            "voice.tts.completed",
            session.session_id,
            correlation_id,
            {
                "duration_sec": tts_res.duration_sec,
                "latency_ms": latency_ms,
                "provider": tts_res.provider,
            },
        )

        metadata = AudioMetadata(
            duration_sec=tts_res.duration_sec,
            frame_count=len(tts_res.audio_bytes) // max(1, tts_res.audio_format.frame_size),
            sample_rate=tts_res.audio_format.sample_rate,
            channels=tts_res.audio_format.channels,
            sample_width=tts_res.audio_format.sample_width,
            file_size_bytes=len(tts_res.audio_bytes),
        )

        # Launch playback task inside session so it can be interrupted
        play_task = asyncio.create_task(self.playback.play_bytes(tts_res.audio_bytes))
        session.start_speaking(play_task)

        try:
            await play_task
        except asyncio.CancelledError:
            logger.info("Playback cancelled via barge-in")
            await self.playback.stop()
            await self._emit_event("voice.interrupted", session.session_id, correlation_id)
            raise VoiceInterruptedError("Voice playback interrupted by user")

        return metadata

    async def process_speech(
        self,
        audio_bytes: bytes,
        session: Optional[VoiceSession] = None,
        correlation_id: Optional[str] = None,
    ) -> VoiceResponse:
        """Processes recorded speech through STT, Agent Runtime, and TTS."""
        active_session = session or VoiceSession()
        corr_id = correlation_id or f"vcorr_{uuid.uuid4().hex[:12]}"
        start_turn_time = time.time()

        await self._emit_event("voice.session.started", active_session.session_id, corr_id)

        try:
            # 1. Transcribe audio
            transcript = await self.transcribe(
                audio_bytes,
                self.capture.audio_format,
                session_id=active_session.session_id,
                correlation_id=corr_id,
            )

            if not transcript.text.strip():
                # Empty speech detected
                resp = VoiceResponse(
                    session_id=active_session.session_id,
                    correlation_id=corr_id,
                    text="I did not catch that.",
                    agent_status="completed",
                    duration_sec=time.time() - start_turn_time,
                )
                active_session.reset()
                return resp

            # 2. Construct VoiceRequest
            v_req = VoiceRequest(
                session_id=active_session.session_id,
                correlation_id=corr_id,
                transcript=transcript,
                language=transcript.language,
                confidence=transcript.confidence,
                created_at=time.time(),
            )

            # 3. Agent Runtime Processing
            active_session.start_processing()
            await self._emit_event(
                "voice.processing.started",
                active_session.session_id,
                corr_id,
                {"prompt": v_req.text},
            )

            if self.orchestrator:
                agent_res = await self.orchestrator.run(v_req.text)
                final_text = getattr(agent_res, "summary", None) or getattr(agent_res, "answer", str(agent_res))
                status_val = getattr(agent_res, "status", None)
                is_completed = (str(status_val).lower() == "completed" or getattr(status_val, "value", "").lower() == "completed") or getattr(agent_res, "verified", False)
                agent_status = "completed" if is_completed else "unverified"
            else:
                # Direct fallback when orchestrator is omitted in focused tests
                final_text = f"Received: {v_req.text}"
                agent_status = "completed"

            await self._emit_event(
                "voice.processing.completed",
                active_session.session_id,
                corr_id,
                {"status": agent_status},
            )

            # 4. TTS Synthesis and Playback
            meta = await self.synthesize_and_play(final_text, active_session, corr_id)

            resp = VoiceResponse(
                session_id=active_session.session_id,
                correlation_id=corr_id,
                text=final_text,
                audio_metadata=meta,
                agent_status=agent_status,
                duration_sec=time.time() - start_turn_time,
            )
            active_session.complete_turn(v_req, resp)
            return resp

        except VoiceInterruptedError:
            active_session.interrupt()
            raise
        except Exception as exc:
            active_session.fail(str(exc))
            await self._emit_event(
                "voice.failed",
                active_session.session_id,
                corr_id,
                {"error": str(exc)},
            )
            raise
