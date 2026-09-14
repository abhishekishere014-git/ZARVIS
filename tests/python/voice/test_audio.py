"""Unit tests for audio capture, playback, and conversion abstractions."""

import pytest
from jarvis.voice.audio.base import (
    calculate_pcm_rms,
    generate_sine_wave,
    pcm_to_wav,
    wav_to_pcm,
)
from jarvis.voice.audio.capture import AudioCapture
from jarvis.voice.audio.device import AudioDeviceManager
from jarvis.voice.audio.playback import AudioPlayback
from jarvis.voice.audio.virtual import VirtualAudioCapture, VirtualAudioPlayback
from jarvis.voice.models import AudioFormat


def test_calculate_pcm_rms():
    # Silence: all zeros
    silence = b"\x00\x00" * 800
    assert calculate_pcm_rms(silence) == 0.0

    # Sine wave
    sine = generate_sine_wave(frequency_hz=440.0, duration_sec=0.1, sample_rate=16000, amplitude=0.5)
    rms = calculate_pcm_rms(sine)
    assert rms > 5000.0  # Should have strong measurable energy


def test_pcm_and_wav_roundtrip():
    fmt = AudioFormat(sample_rate=16000, channels=1, sample_width=2)
    original_pcm = generate_sine_wave(frequency_hz=300.0, duration_sec=0.2, sample_rate=16000)

    wav_bytes = pcm_to_wav(original_pcm, fmt)
    assert wav_bytes.startswith(b"RIFF")
    assert b"WAVE" in wav_bytes

    recovered_pcm, recovered_fmt = wav_to_pcm(wav_bytes)
    assert recovered_pcm == original_pcm
    assert recovered_fmt.sample_rate == fmt.sample_rate
    assert recovered_fmt.channels == fmt.channels
    assert recovered_fmt.sample_width == fmt.sample_width


def test_device_manager_fallback():
    mgr = AudioDeviceManager()
    inputs = mgr.list_input_devices()
    outputs = mgr.list_output_devices()
    assert len(inputs) >= 1
    assert len(outputs) >= 1

    default_in = mgr.get_default_input_device()
    default_out = mgr.get_default_output_device()
    assert default_in is not None
    assert default_out is not None


@pytest.mark.asyncio
async def test_virtual_audio_capture_and_playback():
    fmt = AudioFormat(sample_rate=16000, channels=1, sample_width=2)
    virtual_capture = VirtualAudioCapture(fmt)
    virtual_playback = VirtualAudioPlayback()

    capture = AudioCapture(audio_format=fmt, virtual_backend=virtual_capture)
    playback = AudioPlayback(audio_format=fmt, virtual_backend=virtual_playback)

    # Feed synthetic data into virtual capture
    test_pcm = generate_sine_wave(duration_sec=0.1, sample_rate=16000)
    await virtual_capture.feed_pcm_data(test_pcm, chunk_duration_sec=0.05)

    await capture.start()
    chunk1 = await capture.read_chunk(timeout_sec=0.5)
    assert chunk1 is not None
    assert len(chunk1.data) > 0

    chunk2 = await capture.read_chunk(timeout_sec=0.5)
    assert chunk2 is not None

    await capture.stop()
    meta = capture.get_metadata()
    assert meta.frame_count > 0

    # Test playback
    await playback.play_bytes(test_pcm, chunk_duration_sec=0.05)
    assert virtual_playback.total_chunks_played >= 2
    assert virtual_playback.played_bytes == test_pcm
