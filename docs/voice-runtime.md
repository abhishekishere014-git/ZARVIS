# JARVIS Voice & Audio Runtime Guide

## 1. Configuration Reference

The voice pipeline is configured via environment variables with prefix `JARVIS_` or central `JarvisSettings`:

```ini
# Voice General
JARVIS_VOICE_ENABLED=true
JARVIS_VOICE_SAMPLE_RATE=16000
JARVIS_VOICE_CHANNELS=1
JARVIS_VOICE_SAMPLE_WIDTH=2

# STT Providers
JARVIS_VOICE_STT_PROVIDER=router          # 'router', 'vosk', 'whisper', 'mock'
JARVIS_VOICE_VOSK_MODEL_PATH=models/vosk   # Path to local Vosk model directory
JARVIS_VOICE_WHISPER_MODEL=base            # 'tiny', 'base', 'small', 'medium'
JARVIS_VOICE_WHISPER_DEVICE=cpu           # 'cpu' or 'cuda'
JARVIS_VOICE_WHISPER_COMPUTE_TYPE=int8    # 'int8', 'float16', 'float32'

# Voice Activity Detection (VAD)
JARVIS_VOICE_VAD_PROVIDER=energy          # 'energy', 'mock'
JARVIS_VOICE_VAD_ENERGY_THRESHOLD=500.0   # RMS energy threshold
JARVIS_VOICE_VAD_SILENCE_TIMEOUT_SEC=1.2  # Trailing silence detection timeout
JARVIS_VOICE_VAD_MIN_SPEECH_SEC=0.3       # Minimum duration of speech

# Limits & Storage
JARVIS_VOICE_MAX_RECORDING_DURATION_SEC=30.0
JARVIS_VOICE_MAX_AUDIO_SIZE_BYTES=26214400 # 25MB

# Text-to-Speech (TTS)
JARVIS_VOICE_TTS_PROVIDER=kokoro          # 'kokoro', 'mock'
JARVIS_VOICE_KOKORO_MODEL_PATH=models/kokoro/kokoro-v0_19.onnx
JARVIS_VOICE_TTS_VOICE=af_heart           # 'af_heart', 'am_adam', etc.
JARVIS_VOICE_TTS_SPEED=1.0                # 0.5 to 2.0
```

---

## 2. Event Bus Lifecycle Events

The voice subsystem publishes 11 standardized telemetry events to `AsyncEventBus`:

1. `voice.session.started`
2. `voice.listening.started`
3. `voice.listening.stopped`
4. `voice.transcription.started`
5. `voice.transcription.completed`
6. `voice.processing.started`
7. `voice.processing.completed`
8. `voice.tts.started`
9. `voice.tts.completed`
10. `voice.interrupted`
11. `voice.failed`

All event payloads include `session_id`, `correlation_id`, and timestamps. Raw audio bytes and secrets are never published.

---

## 3. Programmatic Usage

```python
import asyncio
from jarvis.config.settings import JarvisSettings
from jarvis.voice.factory import build_voice_pipeline
from jarvis.voice.session import VoiceSession

async def main():
    settings = JarvisSettings()
    pipeline = build_voice_pipeline(settings=settings)
    session = VoiceSession()

    # Capture and process turn
    response = await pipeline.process_speech(audio_bytes=raw_pcm, session=session)
    print(f"JARVIS: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
```
