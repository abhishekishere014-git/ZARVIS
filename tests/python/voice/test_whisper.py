"""Unit tests for Faster-Whisper STT provider."""

from unittest.mock import MagicMock
import pytest
from jarvis.voice.errors import STTProviderUnavailableError
from jarvis.voice.models import AudioFormat, STTRequest
from jarvis.voice.stt.whisper import FasterWhisperSTTProvider


def test_whisper_availability():
    provider = FasterWhisperSTTProvider()
    assert provider.name == "whisper"
    # Will be False if faster_whisper is not installed in the environment
    if provider._whisper_module is None:
        assert provider.is_available() is False


@pytest.mark.asyncio
async def test_whisper_raises_when_unavailable():
    provider = FasterWhisperSTTProvider()
    provider._whisper_module = None
    req = STTRequest(audio_bytes=b"\x00" * 320, audio_format=AudioFormat())
    with pytest.raises(STTProviderUnavailableError):
        await provider.transcribe(req)


@pytest.mark.asyncio
async def test_whisper_mocked_transcription():
    provider = FasterWhisperSTTProvider()

    mock_whisper_module = MagicMock()
    mock_model = MagicMock()

    mock_seg = MagicMock()
    mock_seg.text = "Create a monthly sales report"
    mock_seg.start = 0.0
    mock_seg.end = 2.1
    mock_seg.avg_logprob = -0.1

    mock_info = MagicMock()
    mock_info.language = "hi-en"

    mock_model.transcribe.return_value = ([mock_seg], mock_info)
    mock_whisper_module.WhisperModel.return_value = mock_model

    provider._whisper_module = mock_whisper_module
    assert provider.is_available() is True

    req = STTRequest(audio_bytes=b"\x00" * 1600, audio_format=AudioFormat())
    result = await provider.transcribe(req)
    assert result.text == "Create a monthly sales report"
    assert result.language == "hi-en"
    assert result.confidence > 0.8
    assert result.provider == "whisper"
