"""Performance and latency benchmarks for Voice & Audio pipeline components."""

import time
import pytest
from jarvis.voice.audio.base import (
    calculate_pcm_rms,
    generate_sine_wave,
    pcm_to_wav,
    wav_to_pcm,
)
from jarvis.voice.models import AudioChunk, AudioFormat, STTRequest
from jarvis.voice.stt.mock import MockSTTProvider
from jarvis.voice.stt.router import STTRouter
from jarvis.voice.vad.energy import EnergyVAD


def test_energy_vad_latency_benchmark():
    vad = EnergyVAD()
    chunk = AudioChunk(data=b"\x10\x00" * 320)  # 20ms frame at 16kHz

    # Measure execution time across 500 frames
    t0 = time.perf_counter()
    for _ in range(500):
        vad.process_chunk(chunk)
    elapsed_total_ms = (time.perf_counter() - t0) * 1000.0
    avg_per_frame_ms = elapsed_total_ms / 500.0

    # VAD must process faster than 0.5ms per 20ms frame to maintain real-time safety
    assert avg_per_frame_ms < 0.5, f"VAD latency too high: {avg_per_frame_ms:.3f}ms per frame"


def test_pcm_wav_conversion_throughput():
    fmt = AudioFormat(sample_rate=16000)
    pcm_1s = generate_sine_wave(duration_sec=1.0, sample_rate=16000)

    t0 = time.perf_counter()
    for _ in range(50):
        wav = pcm_to_wav(pcm_1s, fmt)
        rec_pcm, _ = wav_to_pcm(wav)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    avg_per_roundtrip_ms = elapsed_ms / 50.0

    # Conversion should take under 2ms per 1-second audio buffer
    assert avg_per_roundtrip_ms < 2.0


@pytest.mark.asyncio
async def test_stt_router_decision_latency():
    mock_fast = MockSTTProvider(provider_name="vosk")
    mock_acc = MockSTTProvider(provider_name="whisper")
    router = STTRouter(
        providers={"vosk": mock_fast, "whisper": mock_acc},
        fastpath_provider="vosk",
        accurate_provider="whisper",
    )

    req = STTRequest(audio_bytes=b"\x00" * 3200, audio_format=AudioFormat())

    t0 = time.perf_counter()
    res = await router.transcribe(req)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 50.0  # In-memory router overhead should be negligible
    assert res.text == mock_fast.default_text
