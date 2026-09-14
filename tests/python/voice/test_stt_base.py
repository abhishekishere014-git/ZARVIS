"""Unit tests for STTProvider base contracts and MockSTTProvider."""

import pytest
from jarvis.voice.errors import STTError
from jarvis.voice.models import AudioFormat, STTRequest, STTResult
from jarvis.voice.stt.mock import MockSTTProvider


@pytest.mark.asyncio
async def test_mock_stt_basic_transcription():
    provider = MockSTTProvider(default_text="Create a presentation", confidence=0.98)
    assert provider.name == "mock"
    assert provider.is_available() is True

    req = STTRequest(
        audio_bytes=b"\x00" * 3200,
        audio_format=AudioFormat(sample_rate=16000),
    )
    result = await provider.transcribe(req)
    assert result.text == "Create a presentation"
    assert result.confidence == 0.98
    assert result.provider == "mock"
    assert len(result.segments) == 1
    assert provider.transcribe_count == 1


@pytest.mark.asyncio
async def test_mock_stt_scripted_and_error():
    provider = MockSTTProvider()
    custom_res = STTResult(text="Scripted text", confidence=0.88, provider="mock")
    provider.script_result(custom_res)

    req = STTRequest(audio_bytes=b"\x00" * 160, audio_format=AudioFormat())
    res1 = await provider.transcribe(req)
    assert res1.text == "Scripted text"

    # Inject error
    provider.set_error(STTError("Hardware failure"))
    with pytest.raises(STTError, match="Hardware failure"):
        await provider.transcribe(req)
