"""Unit tests for TTSProvider base contracts and MockTTSProvider."""

import pytest
from jarvis.voice.errors import TTSError
from jarvis.voice.models import AudioFormat, TTSRequest
from jarvis.voice.tts.mock import MockTTSProvider


@pytest.mark.asyncio
async def test_mock_tts_synthesize():
    provider = MockTTSProvider(default_voice="af_heart")
    assert provider.name == "mock"
    assert provider.is_available() is True

    req = TTSRequest(text="Good morning, Abhishek.", voice="af_heart", speed=1.0)
    result = await provider.synthesize(req)

    assert result.duration_sec > 0.0
    assert len(result.audio_bytes) > 0
    assert result.provider == "mock"
    assert provider.synthesize_count == 1


@pytest.mark.asyncio
async def test_mock_tts_stream():
    provider = MockTTSProvider()
    req = TTSRequest(text="Sentence one. Sentence two! Sentence three?")

    chunks = []
    async for chunk in provider.synthesize_stream(req):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert all(len(c.data) > 0 for c in chunks)


@pytest.mark.asyncio
async def test_mock_tts_error_injection():
    provider = MockTTSProvider()
    provider.set_error(TTSError("Synthesis engine timeout"))

    req = TTSRequest(text="Hello")
    with pytest.raises(TTSError, match="Synthesis engine timeout"):
        await provider.synthesize(req)
