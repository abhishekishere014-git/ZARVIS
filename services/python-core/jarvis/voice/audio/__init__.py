"""Audio capture and playback abstraction module."""

from jarvis.voice.audio.base import (
    BaseAudioCapture,
    BaseAudioPlayback,
    calculate_pcm_rms,
    generate_sine_wave,
    pcm_to_wav,
    wav_to_pcm,
)
from jarvis.voice.audio.capture import AudioCapture
from jarvis.voice.audio.device import AudioDeviceInfo, AudioDeviceManager
from jarvis.voice.audio.playback import AudioPlayback
from jarvis.voice.audio.virtual import VirtualAudioCapture, VirtualAudioPlayback

__all__ = [
    "BaseAudioCapture",
    "BaseAudioPlayback",
    "AudioCapture",
    "AudioPlayback",
    "VirtualAudioCapture",
    "VirtualAudioPlayback",
    "AudioDeviceInfo",
    "AudioDeviceManager",
    "calculate_pcm_rms",
    "pcm_to_wav",
    "wav_to_pcm",
    "generate_sine_wave",
]
