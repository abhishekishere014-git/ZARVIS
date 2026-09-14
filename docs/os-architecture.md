# Phase 08 — Controlled Windows OS Automation Architecture

## 1. Overview
Phase 08 introduces a secure, auditable, provider-agnostic Windows OS Automation subsystem allowing JARVIS to interact with the desktop via mouse, keyboard, window control, screen capture, clipboard, and system telemetry under the strict supervision of Phase 04 Security and Policy Engines.

## 2. Core Architecture

```
                  +-----------------------------------+
                  |  Multi-Agent Runtime (Phase 05)   |
                  |     Voice Pipeline (Phase 07)     |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------------------------+
                  |      ToolRegistry (Phase 04)      |
                  |      ToolExecutor / Policies      |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------------------------+
                  |       OSAutomationManager         |
                  +-----------------+-----------------+
                                    |
     +--------------+---------------+---------------+--------------+
     |              |               |               |              |
     v              v               v               v              v
[ScreenCapture] [MouseMgr]    [KeyboardMgr]    [WindowMgr]   [ClipboardMgr]
     |              |               |               |              |
     +--------------+---------------+---------------+--------------+
                                    |
                                    v
                         +---------------------+
                         | OSSecurityManager   |
                         | Boundaries & Privacy|
                         +----------+----------+
                                    |
                                    v
                         +---------------------+
                         |   OSProvider API    |
                         +----------+----------+
                                    |
               +--------------------+--------------------+
               |                                         |
               v                                         v
     [WindowsOSProvider]                        [MockOSProvider]
     (Win32/User32/Gdi32)                    (Virtual Canvas/History)
```

## 3. Subsystem Breakdown

### 3.1 Screen Capture & Display Geometry (`jarvis.os.screen`)
- **`ScreenCaptureManager`**: Captures screen buffers bounded strictly to temporary sandboxed paths (`data/workspace/temp/screens/`).
- **`MonitorManager`**: Discovers monitor geometry, DPI scaling factors, virtual desktop coordinates.

### 3.2 Input Dispatch (`jarvis.os.input`)
- **`MouseManager`**: Coordinates relative and absolute cursor movements across `SCREEN`, `MONITOR`, and `WINDOW` coordinate frames. Single, double, and right click execution. Wheel scrolling. Destructive clicks require explicit authorization (`ApprovalMode.USER_APPROVAL`).
- **`KeyboardManager`**: Types unicode text with per-character pacing. Dispatches allowlisted keys (`ENTER`, `TAB`, `ESC`, `F1-F12`, etc.) and hotkey sequences (`CTRL+C`, `ALT+TAB`). Flags and enforces approval on sensitive texts (passwords, tokens).

### 3.3 Window Management (`jarvis.os.window`)
- **`WindowManager`**: Enumerates top-level visible windows, process IDs, and bounding rectangles. Resolves windows deterministically; raises `WindowAmbiguityError` if multiple candidate matches exist to prevent misdirected input. Supports `FOCUS`, `MINIMIZE`, `MAXIMIZE`, `RESTORE`.

### 3.4 Clipboard Management (`jarvis.os.clipboard`)
- **`ClipboardManager`**: Reads and writes plain text to system clipboard. Privacy controls ensure written strings are never echoed back in execution results or EventBus events.

### 3.5 System Telemetry (`jarvis.os.system`)
- **`SystemInfoManager`**: Non-invasive, read-only system telemetry (OS version, architecture, CPU count, RAM totals, active foreground window).

### 3.6 Post-Action Verification (`jarvis.os.verification`)
- **`OSActionVerifier`**: Confirms state changes following execution (e.g. mouse cursor reached target, window gained foreground focus, clipboard contains expected value).

### 3.7 Provider Abstraction (`jarvis.os.providers`)
- **`OSProvider` (Protocol)**: Clean contract defining all low-level OS operations.
- **`WindowsOSProvider`**: Native implementation leveraging standard library `ctypes` (`user32.dll`, `gdi32.dll`, `kernel32.dll`) and `PIL.Image`. Zero third-party C extensions required.
- **`MockOSProvider`**: High-fidelity virtual desktop canvas for headless, continuous integration testing without physical hardware dependencies.
