# ZARVIS v0.1.0 — Production Release Notes

**Release Date:** September 16, 2026  
**Target Platform:** Windows 10 & 11 (x64)  
**Status:** Complete & Verified (475 / 475 Tests Passing)

---

## 🚀 Overview

**ZARVIS** (Zero-latency Adaptive Real-time Voice & Intelligence System) is a local-first Windows desktop AI assistant. It brings together local speech processing, autonomous multi-agent task execution, screen vision grounding, and Windows OS automation into a glassmorphic desktop workspace and compact floating HUD.

---

## 📦 Release Assets & Checksums

| Asset | Size | SHA-256 Checksum |
| :--- | :--- | :--- |
| **`ZARVIS-Setup-0.1.0.exe`** | 80,705,198 bytes (~76.9 MB) | `DC080760C2604BFAABC48AFC029EC9E18FA3DB90CDC7C671A73E8C82DF22E208` |
| **`SHA256SUMS.txt`** | 87 bytes | `037ba3fafe3990e1fceebcbf9754ecad1e0b04a9197c36a6e7c7e5cb5b2633bf` |

### Checksum Verification
In Windows PowerShell:
```powershell
(Get-FileHash .\ZARVIS-Setup-0.1.0.exe -Algorithm SHA256).Hash
# Expected: DC080760C2604BFAABC48AFC029EC9E18FA3DB90CDC7C671A73E8C82DF22E208
```

---

## ⚡ Key Capabilities

1. **Local-First Neural Voice Pipeline:**
   - **Tap-to-Speak** & **Hold-to-Speak (PTT)** input modes.
   - Sub-100ms Vosk fast-path STT escalating to Whisper for complex queries.
   - Natural speech synthesis via Kokoro ONNX.
   - Real-time VAD noise filtering and instantaneous barge-in interruption.

2. **Autonomous Multi-Agent Runtime:**
   - ReAct planning loop decomposing goals into DAG waves (Planner $\to$ Executor $\to$ Verifier).
   - Sandboxed Office document generation (`.docx`, `.xlsx`, `.pptx`, `.pdf`).
   - Structural byte validation of generated outputs.

3. **Screen Understanding & Visual Grounding:**
   - Multi-monitor screenshot capture, DPI scaling normalization, and UI element locator.
   - OCR and coordinate mapping without granting direct arbitrary execution rights.

4. **Windows OS Automation & Safety:**
   - Controlled Win32 mouse, keyboard, and window controls.
   - Strict Safety Policy gating sensitive or destructive actions behind mandatory user approval.

5. **Desktop Workspace & Floating HUD:**
   - Full glassmorphic workspace (1280×800) and compact pill HUD (380×64).
   - System Tray integration with 9 verified lifecycle controls.
   - Global hotkey (`Ctrl + Space`) for instant activation.

---

## 🛡️ Security & Privacy

- **Signing Status:** Unsigned / Community Release Build (Commercial EV Authenticode certificate not attached).
- **Loopback Confinement:** All IPC and WebSocket traffic binds exclusively to `127.0.0.1`.
- **Preload Isolation:** `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, explicit Content Security Policy (CSP).
- **Secret Isolation:** API keys are secured via Windows Credential Manager (`keyring`); never written in plaintext.
- **Zero Arbitrary Execution:** Direct shell commands (`shell=True`, `eval()`, `exec()`) are strictly forbidden.

---

## 📥 Installation

1. Download **`ZARVIS-Setup-0.1.0.exe`**.
2. Run the installer. *(Note: As an open-source community release without an expensive commercial EV certificate, Windows Defender SmartScreen may display an unknown publisher notification. Click **"More info"** $\to$ **"Run anyway"**).*
3. Launch ZARVIS from your Desktop or Start Menu.

---

## ⚠️ Known Limitations & Operational Notes

1. **Windows SmartScreen Notice:** Because this build is not signed with a paid commercial EV certificate, Windows SmartScreen may show an initial unknown publisher notice.
2. **Audio Hardware Permissions:** Live speech recognition and synthesis require granting microphone access in Windows Privacy Settings.
3. **Local Loopback Firewall Dialog:** Windows Firewall may prompt on first launch to allow local loopback socket traffic (`127.0.0.1:8765`).
4. **Upstream Dependency Advisory:** The application is packaged with Electron 33.x. Upstream Chromium/Electron advisories reported by `npm audit` are mitigated via application architecture (Chromium sandbox, context isolation, strict CSP, navigation lockdown, and loopback confinement). Major migration to Electron 44+ is deferred to avoid breaking changes.

