import time
import pytest
from jarvis.voice.audio.base import generate_sine_wave
from jarvis.voice.models import AudioChunk, AudioFormat
from jarvis.voice.vad.base import VADSegmenter
from jarvis.voice.vad.energy import EnergyVAD
from jarvis.voice.vad.mock import MockVAD


def test_energy_vad_discrimination():
    vad = EnergyVAD(energy_threshold=500.0)

    # Silence chunk
    silence_chunk = AudioChunk(data=b"\x00\x00" * 320)
    res_silence = vad.process_chunk(silence_chunk)
    assert res_silence.is_speech is False
    assert res_silence.energy == 0.0

    # Strong speech-like chunk
    sine_pcm = generate_sine_wave(frequency_hz=300.0, duration_sec=0.02, sample_rate=16000, amplitude=0.8)
    speech_chunk = AudioChunk(data=sine_pcm)
    res_speech = vad.process_chunk(speech_chunk)
    assert res_speech.is_speech is True
    assert res_speech.energy > 500.0


def test_mock_vad_scripting():
    mock_vad = MockVAD()
    mock_vad.script_decisions([False, True, True, False])

    dummy_chunk = AudioChunk(data=b"\x00\x00" * 160)
    assert mock_vad.process_chunk(dummy_chunk).is_speech is False
    assert mock_vad.process_chunk(dummy_chunk).is_speech is True
    assert mock_vad.process_chunk(dummy_chunk).is_speech is True
    assert mock_vad.process_chunk(dummy_chunk).is_speech is False


def test_vad_segmenter_utterance_flow():
    mock_vad = MockVAD()
    # 2 silence chunks, 3 speech chunks, 2 silence chunks (silence timeout set to 0.05s)
    mock_vad.script_decisions([False, False, True, True, True, False, False])

    fmt = AudioFormat(sample_rate=16000, channels=1, sample_width=2)
    segmenter = VADSegmenter(
        vad_provider=mock_vad,
        audio_format=fmt,
        silence_timeout_sec=0.01,  # Fast timeout for test
        min_speech_duration_sec=0.001,
        max_utterance_duration_sec=10.0,
    )

    test_pcm = b"\x01\x00" * 320
    chunk = AudioChunk(data=test_pcm)

    # First silence
    done, speech = segmenter.process_chunk(chunk)
    assert not done

    # Second silence
    done, speech = segmenter.process_chunk(chunk)
    assert not done

    # Speech onset
    done, speech = segmenter.process_chunk(chunk)
    assert not done
    assert segmenter.is_in_speech is True

    # Speech continue
    done, speech = segmenter.process_chunk(chunk)
    assert not done

    # Speech continue
    done, speech = segmenter.process_chunk(chunk)
    assert not done

    # Trailing silence after timeout duration
    time.sleep(0.02)
    done, speech = segmenter.process_chunk(chunk)
    assert done is True
    assert speech is not None
    assert len(speech) > 0
