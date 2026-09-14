"""End-to-end integration tests for JARVIS Voice & Audio Pipeline."""

import asyncio
import pytest
from jarvis.config.settings import JarvisSettings
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent
from jarvis.voice.audio.base import generate_sine_wave
from jarvis.voice.audio.virtual import VirtualAudioCapture, VirtualAudioPlayback
from jarvis.voice.factory import build_voice_pipeline
from jarvis.voice.session import VoiceSession
from jarvis.voice.vad.mock import MockVAD


@pytest.mark.asyncio
async def test_end_to_end_voice_turn():
    bus = AsyncEventBus()
    await bus.start()

    received_events = []

    async def log_event(e: JarvisEvent):
        received_events.append(e.type)

    bus.subscribe("*", log_event)

    settings = JarvisSettings()
    pipeline = build_voice_pipeline(
        settings=settings,
        event_bus=bus,
        use_mock_audio=True,
        use_mock_models=True,
    )

    # Set virtual audio backends
    virtual_capture = VirtualAudioCapture(pipeline.capture.audio_format)
    virtual_playback = VirtualAudioPlayback()
    pipeline.capture.set_backend(virtual_capture)
    pipeline.playback.set_backend(virtual_playback)

    session = VoiceSession()

    # Process speech turn
    audio_pcm = generate_sine_wave(duration_sec=0.2, sample_rate=16000)
    response = await pipeline.process_speech(audio_bytes=audio_pcm, session=session)

    assert response is not None
    assert response.session_id == session.session_id
    assert "Hello Jarvis" in response.text
    assert response.audio_metadata is not None
    assert response.audio_metadata.duration_sec > 0.0

    # Ensure virtual playback received audio chunks
    assert virtual_playback.total_chunks_played >= 1
    assert len(virtual_playback.played_bytes) > 0

    await asyncio.sleep(0.05)
    await bus.stop()

    assert "voice.session.started" in received_events
    assert "voice.transcription.completed" in received_events
    assert "voice.tts.completed" in received_events
