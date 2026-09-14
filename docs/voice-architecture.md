# JARVIS Voice & Audio Architecture Specification

## 1. Architectural Overview

Phase 07 transforms JARVIS into a voice-first conversational AI assistant through a hardware-agnostic, low-latency Voice & Audio Pipeline.

```
                     ┌───────────────────────────────┐
                     │          MICROPHONE           │
                     │  (Hardware / Virtual Stream)  │
                     └───────────────┬───────────────┘
                                     │ PCM 16-bit 16kHz
                     ┌───────────────▼───────────────┐
                     │         AUDIO CAPTURE         │
                     │    (jarvis.voice.audio)       │
                     └───────────────┬───────────────┘
                                     │ AudioChunk
                     ┌───────────────▼───────────────┐
                     │       VAD & SEGMENTATION      │
                     │      (jarvis.voice.vad)       │
                     │  - Adaptive RMS energy        │
                     │  - Hangover frame bridge      │
                     │  - Silence timeout boundary   │
                     └───────────────┬───────────────┘
                                     │ Contiguous Speech Utterance
                     ┌───────────────▼───────────────┐
                     │          STT ROUTER           │
                     │      (jarvis.voice.stt)       │
                     │                               │
                     │  Fast-Path? ──► Vosk Engine   │
                     │       │         (low-latency) │
                     │   Confidence < 0.75 or Long?  │
                     │       ▼                       │
                     │  Escalate  ──► Faster-Whisper │
                     │                (high-accuracy)│
                     └───────────────┬───────────────┘
                                     │ Normalized VoiceRequest
                     ┌───────────────▼───────────────┐
                     │     PHASE 05 AGENT RUNTIME    │
                     │   - Goal Planner (DAG)        │
                     │   - Supervised Executor       │
                     │   - Phase 04 Tool Sandboxing  │
                     │   - Phase 06 Tri-Tier Memory  │
                     │   - Verifier & Recovery       │
                     │   - Single Answer Synthesis   │
                     └───────────────┬───────────────┘
                                     │ Verified Final Text Answer
                     ┌───────────────▼───────────────┐
                     │          TTS ENGINE           │
                     │      (jarvis.voice.tts)       │
                     │  - Kokoro ONNX local model    │
                     │  - Streaming sentence chunks  │
                     │  - Configurable voices & rate │
                     └───────────────┬───────────────┘
                                     │ Synthesized Audio PCM
                     ┌───────────────▼───────────────┐
                     │        AUDIO PLAYBACK         │
                     │  - Chunk streaming            │
                     │  - Barge-in listener          │
                     │  - Immediate cancellation     │
                     └───────────────┬───────────────┘
                                     │
                     ┌───────────────▼───────────────┐
                     │            SPEAKER            │
                     └───────────────────────────────┘
```

---

## 2. Core Subsystems

### 2.1 Audio Abstraction (`jarvis.voice.audio`)
* **Hardware Independence:** Decouples the application from physical audio drivers (`sounddevice` / `pyaudio`) via `BaseAudioCapture` and `BaseAudioPlayback` protocols.
* **Standard Representation:** Enforces 16-bit little-endian PCM at 16,000 Hz mono as the default voice contract, with pure standard library WAV conversion (`wave`, `struct`).
* **Virtual Backends:** Complete in-memory drivers (`VirtualAudioCapture`, `VirtualAudioPlayback`) enabling headless test automation and deterministic simulation.

### 2.2 Voice Activity Detection (`jarvis.voice.vad`)
* **Standard-Library RMS VAD:** Pure-Python energy calculation with background noise tracking, adaptive multipliers, and hangover frame buffering.
* **VADSegmenter:** Manages utterance boundaries, drops sub-threshold acoustic transients (< 0.3s), and bounds maximum utterance duration (30.0s) to prevent infinite recording.

### 2.3 Intelligent STT Routing (`jarvis.voice.stt`)
* **Vosk Fast-Path:** Lightweight local recognition for short commands (< 5.0s) delivering single-turn latency under 100ms.
* **Faster-Whisper Escalation:** High-accuracy multilingual model (English, Hindi, Hinglish) invoked when Vosk confidence falls below 0.75, when audio exceeds 5.0s, or on fast-path failure.
* **Resiliency Fallback:** Guaranteed deterministic escalation preventing infinite loops or unhandled crashes.

### 2.4 Voice State Machine (`jarvis.voice.state`)
* Explicit deterministic states: `IDLE`, `LISTENING`, `PROCESSING`, `SPEAKING`, `INTERRUPTED`, `ERROR`.
* Rejects illegal state transitions with typed `VoiceStateError`.

### 2.5 Text-to-Speech (`jarvis.voice.tts`)
* **Kokoro ONNX Engine:** Offline neural speech synthesis with customizable voices (`af_heart`) and variable playback speeds.
* **Streaming Chunks:** Sentence-level regex segmentation allowing streaming audio generation without waiting for long completions.

### 2.6 Agent & Memory Integration
* Transcribed voice requests are normalized into `VoiceRequest` and passed directly into `AgentOrchestrator.run(goal)`.
* Employs Phase 06 `MemoryManager` through `AgentContext` for context recall and user preference adherence.
* Delivers the verified final synthesized answer through the TTS engine.
