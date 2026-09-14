"""Unit tests for STTRouter fast-path routing, confidence escalation, and fallback."""

import pytest
from jarvis.voice.errors import STTError, STTProviderUnavailableError
from jarvis.voice.models import AudioFormat, STTRequest, STTResult
from jarvis.voice.stt.mock import MockSTTProvider
from jarvis.voice.stt.router import STTRouter


@pytest.mark.asyncio
async def test_router_fastpath_success():
    fast = MockSTTProvider(default_text="quick command", confidence=0.95, provider_name="vosk")
    accurate = MockSTTProvider(default_text="accurate transcript", confidence=0.99, provider_name="whisper")

    router = STTRouter(
        providers={"vosk": fast, "whisper": accurate},
        fastpath_provider="vosk",
        accurate_provider="whisper",
        confidence_threshold=0.80,
        fastpath_max_duration_sec=5.0,
    )

    # 1 second of audio (16000 samples * 2 bytes = 32000 bytes)
    req = STTRequest(audio_bytes=b"\x00" * 32000, audio_format=AudioFormat(sample_rate=16000))
    res = await router.transcribe(req)

    assert res.provider == "vosk"
    assert res.text == "quick command"
    assert fast.transcribe_count == 1
    assert accurate.transcribe_count == 0


@pytest.mark.asyncio
async def test_router_escalation_on_low_confidence():
    # Fast path returns low confidence (0.60 < 0.80 threshold)
    fast = MockSTTProvider(default_text="garbled", confidence=0.60, provider_name="vosk")
    accurate = MockSTTProvider(default_text="clear sentence", confidence=0.95, provider_name="whisper")

    router = STTRouter(
        providers={"vosk": fast, "whisper": accurate},
        fastpath_provider="vosk",
        accurate_provider="whisper",
        confidence_threshold=0.80,
    )

    req = STTRequest(audio_bytes=b"\x00" * 32000, audio_format=AudioFormat(sample_rate=16000))
    res = await router.transcribe(req)

    assert res.provider == "whisper"
    assert res.text == "clear sentence"
    assert fast.transcribe_count == 1
    assert accurate.transcribe_count == 1


@pytest.mark.asyncio
async def test_router_escalation_on_long_audio():
    fast = MockSTTProvider(default_text="fast", confidence=0.95, provider_name="vosk")
    accurate = MockSTTProvider(default_text="long sentence", confidence=0.95, provider_name="whisper")

    router = STTRouter(
        providers={"vosk": fast, "whisper": accurate},
        fastpath_provider="vosk",
        accurate_provider="whisper",
        fastpath_max_duration_sec=2.0,  # 2s max
    )

    # 3 seconds of audio (96000 bytes)
    req = STTRequest(audio_bytes=b"\x00" * 96000, audio_format=AudioFormat(sample_rate=16000))
    res = await router.transcribe(req)

    # Should skip fast-path directly because duration > 2.0s
    assert res.provider == "whisper"
    assert fast.transcribe_count == 0
    assert accurate.transcribe_count == 1


@pytest.mark.asyncio
async def test_router_fallback_when_fastpath_fails():
    fast = MockSTTProvider(provider_name="vosk")
    fast.set_error(STTError("Vosk crash"))
    accurate = MockSTTProvider(default_text="fallback success", provider_name="whisper")

    router = STTRouter(
        providers={"vosk": fast, "whisper": accurate},
        fastpath_provider="vosk",
        accurate_provider="whisper",
    )

    req = STTRequest(audio_bytes=b"\x00" * 16000, audio_format=AudioFormat())
    res = await router.transcribe(req)

    assert res.provider == "whisper"
    assert res.text == "fallback success"


@pytest.mark.asyncio
async def test_router_raises_when_all_fail():
    fast = MockSTTProvider(provider_name="vosk")
    fast.set_error(STTError("Vosk crash"))
    accurate = MockSTTProvider(provider_name="whisper")
    accurate.set_error(STTError("Whisper crash"))

    router = STTRouter(
        providers={"vosk": fast, "whisper": accurate},
        fastpath_provider="vosk",
        accurate_provider="whisper",
    )

    req = STTRequest(audio_bytes=b"\x00" * 16000, audio_format=AudioFormat())
    with pytest.raises(STTProviderUnavailableError):
        await router.transcribe(req)
