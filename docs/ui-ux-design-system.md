# ZARVIS — Premium Windows Desktop UI/UX System Specification

## 1. Executive Summary & Design Philosophy

**ZARVIS** is a local-first, intelligent Windows desktop companion engineered for high-performance natural voice interaction, autonomous multi-agent task execution, visual screen grounding, and native operating system automation.

The UI/UX design fuses the best architectural qualities of the two canonical visual references:
* **From Reference B (The Structural Foundation):** Clean composition, disciplined 4/8/12/16/24/32px spacing hierarchy, restrained typography, elegant central assistant presence, and calm, uncrowded desktop canvas.
* **From Reference A (The Functional Richness):** Live system telemetry panel, comprehensive activity feed, versatile multi-state floating HUD, Windows system tray integration, and deep settings/voice control panels.

### Visual Identity Principles:
1. **Desktop Native, Not Web/Mobile:** Engineered with Windows 11 design tenets (Mica/Acrylic subtle translucency, 1px borders, crisp geometry, native system tray, discrete window controls).
2. **Subtle Technical Futuristic:** Electric-blue primary accent (`#0A84FF` / `#0078D4`), deep charcoal/navy background canvas (`#0A0E17`), and functional state illumination rather than gratuitous neon/glow.
3. **Voice-First Primacy:** The central microphone is the undisputed hero control, offering instantaneous dual-mode interaction: **Tap-to-Speak** and **Hold-to-Speak (Push-to-Talk)** with fluid waveform feedback.
4. **Transparency & Trust:** Multi-agent workflows, tool executions, and file operations show real provenance without exposing intimidating stack traces or fake decorative charts.

---

## 2. Design System Tokens & Color Palette

### 2.1 Surfaces & Canvas (Dark-First Foundation)
```css
--zarvis-bg-base:        #0B0F19; /* Deep Obsidian Charcoal (Desktop Root) */
--zarvis-bg-sidebar:     #080C14; /* Recessed Navigation Sidebar */
--zarvis-bg-surface-1:   #111827; /* Standard Container / Card Surface */
--zarvis-bg-surface-2:   #1A2234; /* Elevated Control / Active Element */
--zarvis-bg-surface-hud: rgba(14, 20, 32, 0.88); /* Acrylic Glass for Floating HUD */

--zarvis-border-subtle:  rgba(255, 255, 255, 0.06); /* 1px standard border */
--zarvis-border-focus:   rgba(10, 132, 255, 0.50);  /* Active focus ring */
--zarvis-border-card:    rgba(255, 255, 255, 0.08); /* Card separation */
```

### 2.2 Functional State Palette (State-Driven Illumination)
```css
--state-idle:        #94A3B8; /* Slate Neutral - System Standby */
--state-listening:   #10B981; /* Emerald Green - Microphone Active */
--state-thinking:    #0A84FF; /* Electric ZARVIS Blue - Multi-Agent Reasoning */
--state-speaking:    #38BDF8; /* Sky Blue - Neural TTS Audio Playback */
--state-warning:     #F59E0B; /* Amber - High Risk / Approval Required */
--state-error:       #EF4444; /* Crimson Red - Execution Fault / Disconnection */
--state-offline:     #64748B; /* Muted Charcoal - Service Unreachable */
```

### 2.3 Typography
* **Primary Font Stack:** `Segoe UI Variable Text`, `Inter`, -apple-system, sans-serif.
* **Monospace Stack (for paths, tools, tokens):** `Cascadia Code`, `Consolas`, monospace.
* **Hierarchy:**
  * Title / Greeting: 24px, Semibold (Weight 600)
  * Section Headers: 14px, Medium (Weight 500), uppercase tracking +0.05em
  * Primary Body / Commands: 14px, Regular (Weight 400), line-height 1.5
  * Metadata & Status Badges: 12px, Medium (Weight 500)
  * Micro Labels: 11px, Regular (Weight 400)

---

## 3. Dual-Mode Architecture

ZARVIS seamlessly shifts between two interconnected presentation modes:

```
┌────────────────────────────────────────────────────────┐
│  MODE A: COMPACT FLOATING HUD                          │
│  [ (Z)  ● Ready  │  🎙️ Tap/Hold  │  👁️  │  📌  │  ⛶  ]  │
└───────────────────────────┬────────────────────────────┘
                            │  Click "⛶" or Global Hotkey (Win+J)
┌───────────────────────────▼────────────────────────────┐
│  MODE B: FULL DESKTOP WORKSPACE                        │
│  ┌──────────┬──────────────────────────┬─────────────┐ │
│  │ SIDEBAR  │ CENTRAL ASSISTANT CANVAS │ ACTIVITY &  │ │
│  │  - Nav   │  - Hero Voice Controller │ CONVERSATION│ │
│  │  - Status│  - Quick Actions         │  - Agents   │ │
│  │          │  - Command Composer      │  - Tool Logs│ │
│  └──────────┴──────────────────────────┴─────────────┘ │
└────────────────────────────────────────────────────────┘
```

### Mode A: Compact Floating HUD
* **Target Footprint:** 320px $\times$ 48px floating capsule or 240px circular widget.
* **Positioning:** Fixed to bottom-right (or user-dragged location); stays discreetly above VS Code, Office, and browsers when pinned (`📌`).
* **Controls:**
  1. ZARVIS Identifier Icon + Live Status Dot (`● Ready`).
  2. Hero Voice Button (Interactive for Tap and Hold).
  3. Vision Screen Capture Trigger (`👁️`).
  4. Pin / Always-on-Top Toggle (`📌`).
  5. Expand to Full Workspace Button (`⛶`).
  6. Minimize to Windows System Tray (`✕`).

### Mode B: Full Desktop Workspace
* **Window Size:** Default 1280 $\times$ 800px; responsive down to 1024 $\times$ 640px and up to 4K displays.
* **Structure:**
  * **Compact Left Sidebar (220px):** Logo, Navigation items (Home, Chat, Activity, Agents, Memory, Settings), and real-time System Status indicators.
  * **Central Assistant Workspace:** Personalized greeting, interactive ZARVIS Core Orb, Hero Microphone with dual Tap/Hold interaction, Quick Actions, and desktop Command Composer.
  * **Right Auxiliary Panel (340px, Collapsible):** Contextual conversation stream, multi-agent plan execution steps, or detailed activity history.

---

## 4. Hero Voice Interaction (The Central Experience)

Voice interaction is the primary modality of ZARVIS. The central microphone control supports **both Tap-to-Speak and Push-to-Talk** intuitively:

### 4.1 Tap-to-Speak Flow
1. **Single Click:** Microphone activates instantly; ring lights up Emerald Green (`--state-listening`).
2. **Audio Streaming:** Live waveform ripple animates below the button. Recognized speech appears in real-time beneath the microphone:
   > *"Open Visual Studio Code and create a new project..."*
3. **Completion:** When user stops speaking (detected by local VAD) or taps the microphone again, recording ends.
4. **Transition:** State switches to Blue (`--state-thinking`) while multi-agent planning occurs, then to Sky Blue (`--state-speaking`) as Kokoro ONNX reads the answer.

### 4.2 Hold-to-Speak (Push-to-Talk) Flow
1. **Press & Hold (Mouse Down / Spacebar Hold):** Micro-vibration / scale-down animation (0.96 scale). State transitions instantly to Listening.
2. **Held State Feedback:** Helper text displays *"Listening · Release to send"*.
3. **Release (Mouse Up):** Instantly terminates audio capture, commits buffer to Vosk/Whisper STT router, and begins task execution.

### 4.3 Barge-In Capability
If ZARVIS is actively speaking (`--state-speaking`) and the user taps or holds the microphone, TTS playback halts immediately with zero orphaned audio tasks, and ZARVIS resumes listening.

---

## 5. Comprehensive Screen Inventory (All 21 States)

1. **Home / Main Dashboard:** Clean central assistant with Hero Mic, greeting, quick action cards, and recent activity summary.
2. **Compact Floating HUD:** Minimal pill widget floating over Windows workspace.
3. **Listening (Tap Mode):** Green glowing ring, live audio waveform, live transcription preview.
4. **Listening (Hold Mode):** Scaled press feedback with "Release to send" indicator.
5. **Thinking / Processing:** Electric-blue rotating pulse, displaying active agent step ("Planner analyzing dependencies...").
6. **Speaking:** Sky-blue ripple, displaying spoken response text and an instant "Stop / Barge-in" button.
7. **Conversation / Chat:** Chronological interaction view showing user commands, assistant responses, and inline tool execution cards.
8. **Task Running:** Multi-agent pipeline view (Planner $\to$ Coder $\to$ Verifier) with real progress indicators and prominent Stop button.
9. **Safety Approval Dialog:** Modal overlay requiring explicit User Approval for high-risk operations (e.g., deleting files, submitting forms, modifying registry).
10. **Activity / History Screen:** Filterable chronologically sorted audit log with category chips (`All`, `Commands`, `Tools`, `Agents`, `Vision`, `System`).
11. **Multi-Agent Inspector:** Real-time visibility into the 10 specialized agent roles showing status, latency, and verified artifacts.
12. **Memory Inspector:** User-controllable memory manager showing Recent Context, Preferences, Facts, and Saved Artifacts with Edit/Delete controls.
13. **Voice Settings Panel:** Microphone input device dropdown, live input gain level meter, speaker output selection, Kokoro voice model chooser, and barge-in toggle.
14. **General Settings Panel:** Windows startup toggle, start minimized, close to tray behavior, always-on-top, and customizable global hotkey (`Ctrl + Space` / `Win + J`).
15. **AI Settings Panel:** Model provider selection (Gemini, Claude, GPT, local Ollama), capability matrix, and automated fallback chains.
16. **Privacy Settings Panel:** Local-only processing toggles, conversation retention duration, secret redaction preview, and database wipe action.
17. **System Diagnostics Panel:** Real-time IPC telemetry, memory database footprint, audio latency metrics, and component health.
18. **First Run Setup Wizard:** 5-step onboarding: Welcome $\to$ Audio Setup $\to$ AI Provider $\to$ Preferences $\to$ Ready.
19. **Windows System Tray Menu:** Native Windows taskbar right-click menu with quick actions, mute toggle, and system restarts.
20. **Desktop Notification Toast:** Subtle Windows 11 style notification card for long-running task completions and safety alerts.
21. **Offline / Error State:** Graceful degradation indicator when Python Core or Node Gateway drops, showing auto-reconnect countdown.
