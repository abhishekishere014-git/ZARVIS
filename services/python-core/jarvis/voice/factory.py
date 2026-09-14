"""Factory for assembling and dependency-injecting the JARVIS Voice & Audio Pipeline."""

from typing import Optional
from jarvis.agents.orchestrator import AgentOrchestrator
from jarvis.config.settings import JarvisSettings
from jarvis.core.bus import AsyncEventBus
from jarvis.voice.audio.capture import AudioCapture
from jarvis.voice.audio.device import AudioDeviceManager
from jarvis.voice.audio.playback import AudioPlayback
from jarvis.voice.config import VoiceConfig
from jarvis.voice.models import AudioFormat
from jarvis.voice.pipeline import VoicePipeline
from jarvis.voice.security.manager import AudioSecurityManager
from jarvis.voice.stt.mock import MockSTTProvider
from jarvis.voice.stt.router import STTRouter
from jarvis.voice.stt.vosk import VoskSTTProvider
from jarvis.voice.stt.whisper import FasterWhisperSTTProvider
from jarvis.voice.tts.kokoro import KokoroTTSProvider
from jarvis.voice.tts.mock import MockTTSProvider
from jarvis.voice.vad.energy import EnergyVAD
from jarvis.voice.vad.mock import MockVAD
from jarvis.voice.vad.base import VADSegmenter


def build_voice_pipeline(
    settings: Optional[JarvisSettings] = None,
    orchestrator: Optional[AgentOrchestrator] = None,
    event_bus: Optional[AsyncEventBus] = None,
    use_mock_audio: bool = True,
    use_mock_models: bool = True,
) -> VoicePipeline:
    """Constructs and wires the complete Voice & Audio Pipeline."""
    effective_settings = settings or JarvisSettings()
    config = VoiceConfig.from_settings(effective_settings)

    audio_format = AudioFormat(
        sample_rate=config.sample_rate,
        channels=config.channels,
        sample_width=config.sample_width,
    )

    device_manager = AudioDeviceManager()

    # Capture & Playback
    capture = AudioCapture(
        audio_format=audio_format,
        device_manager=device_manager,
        max_duration_sec=config.max_recording_duration_sec,
    )
    playback = AudioPlayback(
        audio_format=audio_format,
        device_manager=device_manager,
    )

    # VAD
    if use_mock_models or config.vad_provider == "mock":
        vad_provider = MockVAD(default_speech=False)
    else:
        vad_provider = EnergyVAD(
            energy_threshold=config.vad_energy_threshold,
            adaptive_noise_floor=True,
        )

    vad_segmenter = VADSegmenter(
        vad_provider=vad_provider,
        audio_format=audio_format,
        silence_timeout_sec=config.vad_silence_timeout_sec,
        min_speech_duration_sec=config.vad_min_speech_sec,
        max_utterance_duration_sec=config.max_recording_duration_sec,
    )

    # STT Providers & Router
    mock_stt = MockSTTProvider(default_text="Hello Jarvis", confidence=0.95)
    vosk_stt = VoskSTTProvider(model_path=config.vosk_model_path)
    whisper_stt = FasterWhisperSTTProvider(
        model_size_or_path=config.whisper_model,
        device=config.whisper_device,
        compute_type=config.whisper_compute_type,
    )

    providers = {
        "mock": mock_stt,
        "vosk": vosk_stt,
        "whisper": whisper_stt,
    }

    if use_mock_models:
        fastpath_key = "mock"
        accurate_key = "mock"
    else:
        fastpath_key = "vosk" if vosk_stt.is_available() else "mock"
        accurate_key = "whisper" if whisper_stt.is_available() else "mock"

    stt_router = STTRouter(
        providers=providers,
        fastpath_provider=fastpath_key,
        accurate_provider=accurate_key,
        confidence_threshold=config.stt_fastpath_confidence_threshold,
        fastpath_max_duration_sec=config.stt_fastpath_max_duration_sec,
    )

    # TTS
    if use_mock_models or config.tts_provider == "mock":
        tts_provider = MockTTSProvider(default_voice=config.tts_voice)
    else:
        kokoro_tts = KokoroTTSProvider(
            model_path=config.kokoro_model_path,
            default_voice=config.tts_voice,
            default_speed=config.tts_speed,
        )
        tts_provider = kokoro_tts if kokoro_tts.is_available() else MockTTSProvider(default_voice=config.tts_voice)

    # Security Manager
    security_manager = AudioSecurityManager(
        temp_dir=config.temp_dir,
        max_recording_duration_sec=config.max_recording_duration_sec,
        max_audio_size_bytes=config.max_audio_size_bytes,
        persist_raw_audio=config.persist_raw_audio,
    )

    return VoicePipeline(
        config=config,
        capture=capture,
        playback=playback,
        vad_segmenter=vad_segmenter,
        stt_router=stt_router,
        tts_provider=tts_provider,
        orchestrator=orchestrator,
        event_bus=event_bus,
        security_manager=security_manager,
    )
