"""Unit tests for Kokoro ONNX TTS provider."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest
from jarvis.voice.errors import TTSProviderUnavailableError
from jarvis.voice.models import TTSRequest
from jarvis.voice.tts.kokoro import KokoroTTSProvider


def test_kokoro_unavailability():
    provider = KokoroTTSProvider(model_path=Path("non_existent_kokoro.onnx"))
    assert provider.name == "kokoro"
    assert provider.is_available() is False


@pytest.mark.asyncio
async def test_kokoro_raises_when_unavailable():
    provider = KokoroTTSProvider(model_path=Path("non_existent_kokoro.onnx"))
    req = TTSRequest(text="Hello world")
    with pytest.raises(TTSProviderUnavailableError):
        await provider.synthesize(req)


def test_kokoro_sentence_splitting():
    provider = KokoroTTSProvider()
    text = "First sentence. Second sentence! Third one? And fourth."
    sentences = provider._split_into_sentences(text)
    assert len(sentences) == 4
    assert sentences[0] == "First sentence."
    assert sentences[1] == "Second sentence!"


@pytest.mark.asyncio
async def test_kokoro_mocked_synthesize(monkeypatch):
    provider = KokoroTTSProvider(model_path=Path("dummy.onnx"))
    monkeypatch.setattr(Path, "exists", lambda self: True)

    mock_kokoro_instance = MagicMock()
    # Return 1600 float samples at 16000Hz (0.1s)
    mock_samples = [0.1] * 1600
    mock_kokoro_instance.create.return_value = (mock_samples, 16000)

    mock_module = MagicMock()
    mock_module.Kokoro.return_value = mock_kokoro_instance

    provider._kokoro_module = mock_module
    assert provider.is_available() is True

    req = TTSRequest(text="Hello from mocked Kokoro")
    result = await provider.synthesize(req)

    assert result.duration_sec > 0.0
    assert result.provider == "kokoro"
    assert len(result.audio_bytes) == 1600 * 2  # 16-bit
