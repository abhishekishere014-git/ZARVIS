"""Tests enforcing resource limits, timeouts, and loop prevention in voice pipeline."""

import asyncio
import time
import pytest
from jarvis.voice.audio.capture import AudioCapture
from jarvis.voice.audio.virtual import VirtualAudioCapture
from jarvis.voice.errors import VoiceTimeoutError
from jarvis.voice.models import AudioChunk, AudioFormat
from jarvis.voice.session import VoiceSession
from jarvis.voice.vad.base import VADSegmenter
from jarvis.voice.vad.mock import MockVAD


@pytest.mark.asyncio
async def test_audio_capture_duration_limit():
    fmt = AudioFormat(sample_rate=16000)
    virtual = VirtualAudioCapture(fmt)
    # Set max duration to 0.05 seconds
    capture = AudioCapture(audio_format=fmt, virtual_backend=virtual, max_duration_sec=0.05)

    await capture.start()
    # Feed continuous chunks
    chunk = AudioChunk(data=b"\x00" * 320)
    await virtual.feed_chunk(chunk)

    # Wait until duration expires
    await asyncio.sleep(0.08)

    with pytest.raises(VoiceTimeoutError):
        await capture.read_chunk()


def test_vad_segmenter_max_duration_prevents_infinite_recording():
    mock_vad = MockVAD(default_speech=True)  # Indefinite speech
    fmt = AudioFormat(sample_rate=16000)

    segmenter = VADSegmenter(
        vad_provider=mock_vad,
        audio_format=fmt,
        max_utterance_duration_sec=0.1,  # Short upper bound
    )

    chunk = AudioChunk(data=b"\x01\x00" * 160)

    # Feed chunks until forced finalize occurs
    start = time.time()
    forced_done = False
    speech_data = None

    while time.time() - start < 0.3:
        done, speech = segmenter.process_chunk(chunk)
        if done:
            forced_done = True
            speech_data = speech
            break
        time.sleep(0.02)

    assert forced_done is True
    assert speech_data is not None


@pytest.mark.asyncio
async def test_session_isolation_under_concurrency():
    session1 = VoiceSession(session_id="ses_1")
    session2 = VoiceSession(session_id="ses_2")

    session1.start_listening()
    assert session1.state.value == "LISTENING"
    assert session2.state.value == "IDLE"

    session2.start_listening()
    session2.start_processing()
    assert session1.state.value == "LISTENING"
    assert session2.state.value == "PROCESSING"
