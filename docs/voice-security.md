# JARVIS Voice & Audio Security Specification

## 1. Privacy Principles & Privacy-by-Design

The voice subsystem operates under strict privacy and least-privilege standards:

1. **No Raw Audio Persistence by Default:** Raw microphone audio data is processed strictly in-memory. Persistent audio recording to disk is disabled (`persist_raw_audio = False`) by default.
2. **Strict Temporary Audio Sandbox:** When temporary WAV files are generated for speech recognition engines, they are strictly confined inside `data/workspace/temp/audio/`.
3. **Automatic Cleanup:** Temporary audio files are unconditionally deleted immediately after speech recognition completes.
4. **No Secrets or Audio in Telemetry:** Event payloads and log records are scrubbed to ensure raw audio bytes, API credentials (OpenAI, Anthropic, Gemini, GitHub tokens), and bearer headers are never logged or transmitted over event buses.

---

## 2. Audio Boundary Limits & Anti-Abuse

* **Maximum Recording Duration:** Enforces a hard ceiling of 30.0s (`voice_max_recording_duration_sec`). Exceeding this limit immediately terminates capture with `VoiceTimeoutError`.
* **Maximum Payload Size:** Audio payloads are bounded at 25MB (`voice_max_audio_size_bytes`). Oversized buffers are rejected before processing with `VoiceSecurityError`.
* **Format Whitelist:** Only standard audio formats are accepted:
  * Sample rates: 8000, 16000, 22050, 24000, 44100, 48000 Hz.
  * Channels: 1 (mono) or 2 (stereo).
  * Sample widths: 1, 2, or 4 bytes.
* **Path Traversal Defense:** Filenames undergo sanitization removing directory separators (`/`, `\`), null bytes (`\x00`), and parent traversals (`..`). File paths must resolve strictly within `data/workspace/temp/audio/` and reject symlinks.

---

## 3. Threat Model & Mitigations

| Threat | Risk Level | Mitigation Strategy |
| :--- | :--- | :--- |
| **Always-on eavesdropping** | CRITICAL | Voice pipeline records only on explicit triggers (`listen_once`) or bounded push-to-talk. Always-on ambient recording is prohibited. |
| **Microphone memory exhaustion** | HIGH | Hard maximum duration (30s) and payload size limit (25MB) with active buffer truncation. |
| **Prompt injection via transcription** | HIGH | Voice transcripts are treated as untrusted user prompts and submitted to Phase 05 Planner & Security validation before execution. |
| **Barge-in task leakage** | MEDIUM | `VoiceSession.interrupt()` immediately cancels active asyncio playback tasks and prevents orphaned audio loops. |
| **Credential leakage in logs** | HIGH | `AudioSecurityManager.scrub_telemetry_payload()` recursively scrubs secrets and strips raw audio arrays. |
