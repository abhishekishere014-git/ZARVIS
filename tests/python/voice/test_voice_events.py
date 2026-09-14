"""Unit tests for Voice lifecycle event emission on AsyncEventBus."""

import asyncio
from typing import List
import pytest
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent
from jarvis.voice.audio.capture import AudioCapture
from jarvis.voice.audio.playback import AudioPlayback
from jarvis.voice.audio.virtual import VirtualAudioCapture, VirtualAudioPlayback
from jarvis.voice.config import VoiceConfig
from jarvis.voice.models import AudioFormat
from jarvis.voice.pipeline import VoicePipeline
from jarvis.voice.session import VoiceSession
from jarvis.voice.stt.mock import MockSTTProvider
from jarvis.voice.stt.router import STTRouter
from jarvis.voice.tts.mock import MockTTSProvider
from jarvis.voice.vad.base import VADSegmenter
from jarvis.voice.vad.mock import MockVAD


@pytest.mark.asyncio
async def test_voice_lifecycle_events_emission():
    bus = AsyncEventBus()
    await bus.start()

    captured_events: List[JarvisEvent] = []

    async def event_collector(event: JarvisEvent) -> None:
        if event.type.startswith("voice."):
            captured_events.append(event)

    bus.subscribe("*", event_collector)

    fmt = AudioFormat()
    capture = AudioCapture(audio_format=fmt, virtual_backend=VirtualAudioCapture(fmt))
    playback = AudioPlayback(audio_format=fmt, virtual_backend=VirtualAudioPlayback())

    vad = MockVAD()
    segmenter = VADSegmenter(vad_provider=vad, audio_format=fmt)

    stt = MockSTTProvider(default_text="System status check")
    router = STTRouter(providers={"mock": stt}, fastpath_provider="mock", accurate_provider="mock")
    tts = MockTTSProvider()

    config = VoiceConfig()
    pipeline = VoicePipeline(
        config=config,
        capture=capture,
        playback=playback,
        vad_segmenter=segmenter,
        stt_router=router,
        tts_provider=tts,
        event_bus=bus,
    )

    session = VoiceSession()
    await pipeline.process_speech(audio_bytes=b"\x00" * 1600, session=session)

    # Allow event loop to dispatch
    await asyncio.sleep(0.05)
    await bus.stop()

    event_types = [e.type for e in captured_events]
    assert "voice.session.started" in event_types
    assert "voice.transcription.started" in event_types
    assert "voice.transcription.completed" in event_types
    assert "voice.processing.started" in event_types
    assert "voice.processing.completed" in event_types
    assert "voice.tts.started" in event_types
    assert "voice.tts.completed" in event_types

    # Ensure no raw audio or secrets in any payload
    for evt in captured_events:
        assert "audio_bytes" not in evt.payload
        assert "pcm_bytes" not in evt.payload
        assert evt.correlation_id is not None
