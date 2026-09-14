"""Unit tests for Vosk fast-path STT provider."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest
from jarvis.voice.errors import STTProviderUnavailableError
from jarvis.voice.models import AudioFormat, STTRequest
from jarvis.voice.stt.vosk import VoskSTTProvider


def test_vosk_unavailability_when_missing_model():
    provider = VoskSTTProvider(model_path=Path("non_existent_vosk_model"))
    assert provider.name == "vosk"
    assert provider.is_available() is False


@pytest.mark.asyncio
async def test_vosk_raises_when_unavailable():
    provider = VoskSTTProvider(model_path=Path("non_existent_vosk_model"))
    req = STTRequest(audio_bytes=b"\x00" * 320, audio_format=AudioFormat())
    with pytest.raises(STTProviderUnavailableError):
        await provider.transcribe(req)


@pytest.mark.asyncio
async def test_vosk_mocked_transcription(monkeypatch):
    provider = VoskSTTProvider(model_path=Path("dummy_model"))
    # Fake model directory existence
    monkeypatch.setattr(Path, "exists", lambda self: True)

    mock_vosk = MagicMock()
    mock_rec = MagicMock()
    mock_rec.FinalResult.return_value = '{"text": "open excel", "result": [{"word": "open", "start": 0.0, "end": 0.3, "conf": 0.95}, {"word": "excel", "start": 0.3, "end": 0.7, "conf": 0.92}]}'
    mock_vosk.KaldiRecognizer.return_value = mock_rec
    mock_vosk.Model.return_value = MagicMock()

    provider._vosk_module = mock_vosk
    assert provider.is_available() is True

    req = STTRequest(audio_bytes=b"\x00" * 1600, audio_format=AudioFormat())
    result = await provider.transcribe(req)
    assert result.text == "open excel"
    assert len(result.segments) == 2
    assert result.confidence > 0.9
    assert result.provider == "vosk"
