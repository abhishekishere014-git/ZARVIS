# JARVIS — Modular Hybrid AI Assistant Platform

JARVIS is a long-term, modular AI desktop assistant platform combining conversational AI, voice pipelines, computer control, automation, memory, developer tools, and autonomous agent loops.

---

## Engineering Discipline & Governance

JARVIS is built under strict **Software Development Lifecycle (SDLC) governance**:
> **"Requirements first. Design second. Code third. Verification always."**

Every phase adheres to the **10 Mandatory Quality Gates** codified in [ENGINEERING_STANDARDS.md](file:///c:/ZARVIS/docs/ENGINEERING_STANDARDS.md). Code is never assumed correct without automated verification, security audits, and real runtime execution.

---

## Architecture Overview

JARVIS is built on a **Hybrid Architecture**:

```
                         JARVIS PLATFORM
                               │
            ┌──────────────────┴──────────────────┐
            │                                     │
       PYTHON CORE                           NODE GATEWAY
   (services/python-core)              (services/node-gateway)
            │                                     │
   • AI & Agent Orchestration           • Realtime WebSocket API
   • STT / TTS Voice Pipelines          • Client Session State
   • Computer Vision                    • Protocol Validation
   • Multi-Tier Memory                  • UI / Dashboard Hosting
   • OS Automation & Tools              • External Integrations
   • Secret Vault (Keyring)                       │
            │                                     │
            └──────────────────┬──────────────────┘
                               │
                        SHARED PROTOCOL
                     (packages/protocol)
                               │
                   Versioned JSON-RPC / IPC
```

### Runtime Roles

* **Python Core (`services/python-core/`):** Python 3.12+ micro-kernel supervising AI models, agent loops (Planner $\to$ Executor $\to$ Verifier), local voice models, desktop automation, and sandboxed tool execution.
* **Node Gateway (`services/node-gateway/`):** Node.js + TypeScript service managing high-concurrency client connections, WebSocket streams, and UI communication.
* **Shared Protocol (`packages/protocol/`):** Universal, versioned (v1.0) message schemas (`JarvisRequest`, `JarvisResponse`, `JarvisEvent`) enforced symmetrically in TypeScript (Zod) and Python (Pydantic v2).

---

## Monorepo Layout

```
c:/ZARVIS/
├── apps/                        # Future client applications (desktop, web)
│   ├── desktop/
│   └── web/
├── services/                    # Backend micro-services
│   ├── python-core/             # Python runtime (AI, memory, voice, OS tools)
│   └── node-gateway/            # Node.js gateway (WebSocket, HTTP health)
├── packages/                    # Shared libraries and contracts
│   ├── protocol/                # Versioned protocol definitions (TS + JSON)
│   └── shared-types/            # Shared cross-runtime types
├── tests/                       # Test suites
│   └── python/                  # Python pytest test cases
├── docs/                        # Architectural documentation
│   └── architecture.md
├── .env.example                 # Environment configuration template
├── package.json                 # Monorepo orchestration & npm workspaces
└── pyproject.toml               # Python packaging in services/python-core
```

---

## Quick Start & Setup

### Prerequisites
* **Python 3.11+** (Detected: 3.12.10)
* **Node.js 20+** (Detected: v22.23.2)
* **npm 10+** (Detected: 10.9.8)

### 1. Install Dependencies
```bash
# Setup Python virtualenv and install python-core in editable mode
python -m venv .venv
.venv\Scripts\pip install -e "services/python-core[dev]"

# Install Node monorepo packages
npm install
npm run build
```

### 2. Run Test Suites
```bash
# Run all automated tests (Protocol + Node Gateway + Python Core)
npm test

# Run individual test suites
npm run test:protocol   # Shared protocol contract tests
npm run test:gateway    # Node Gateway tests
npm run test:python     # Python Core pytest suite
```

### 3. Start Services (Locally)
```bash
# Start Python Core Daemon
npm run start:python

# Start Node Gateway (in another terminal)
npm run start:gateway
```

Health endpoint: `http://127.0.0.1:3000/health`  
WebSocket gateway: `ws://127.0.0.1:3000/ws`

---

## Security Architecture

* **Loopback Enforcement:** All network endpoints bind to `127.0.0.1` by default and reject public interfaces (`0.0.0.0`).
* **Secret Isolation:** Secrets and API keys are managed exclusively via the OS Credential Manager (`keyring`) in Python Core. Secrets are never stored in plaintext or exposed over network IPC.
* **Fault Isolation:** The asynchronous event bus isolates subscriber errors, preventing individual plugin or tool faults from terminating the engine.

---

## Phased Roadmap

* [x] **Phase 01:** Architecture Audit & Multi-Repository Analysis
* [x] **Phase 02:** Hybrid Core Foundation (Python Core, Node Gateway, Shared Protocol)
* [x] **Phase 03:** Model-Agnostic AI Provider Layer (OpenAI, Anthropic, Gemini, Ollama, Routing & Fallbacks)
* [x] **Phase 04:** Sandboxed Tool Registry & Native Office Generation Suite (DOCX, XLSX, PPTX, PDF)
* [x] **Phase 05:** Autonomous Multi-Agent Runtime & Orchestration (Planner $\to$ Executor $\to$ Verifier)
* [x] **Phase 06:** Tri-Tier Memory Engine (Sliding Window + SQLite + `sqlite-vec`)
* [x] **Phase 07:** Voice Pipeline (Vosk Fast-Path + Faster-Whisper + Kokoro ONNX)
* [x] **Phase 08:** Controlled Windows OS Automation & Computer Interaction Layer
* [x] **Phase 09:** Vision, Screen Understanding & Visual Grounding Layer
* [ ] **Phase 10:** Headless IPC Bridge (Python <-> Node Gateway link)
* [ ] **Phase 11:** Desktop Client & System Tray UI
* [ ] **Phase 12:** Hardening, E2E Testing & Release

---

## Phase 03: AI Provider Layer

The AI Provider Layer (`services/python-core/jarvis/ai/`) provides a model-agnostic, zero-leakage LLM abstraction supporting dynamic provider switching, capability routing, automatic retries with jittered exponential backoff, and seamless fallback chains.

### Key Capabilities
* **Universal Normalized Contracts:** `AIProvider` protocol with typed `ChatMessage`, `LLMRequest`, `LLMResponse`, `AIStreamEvent`, and `ToolDefinition`.
* **Zero Vendor Leakage:** Native async HTTP adapters (`httpx.AsyncClient`) avoiding heavy proprietary SDKs.
* **Supported Adapters:**
  * **OpenAI Adapter:** `gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini` (SSE streaming + function calling).
  * **Anthropic Adapter:** `claude-3-5-sonnet-20241022`, `claude-3-haiku` (Messages API streaming + tool use blocks).
  * **Google Gemini Adapter:** `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash` (v1beta REST API with tool declarations).
  * **Ollama Adapter:** Local offline execution (`llama3`, `mistral`, `qwen2.5`) with NDJSON streaming and tag discovery.
* **AIRouter & Resiliency:**
  * Capability checking (e.g. rejects tools or vision if provider lacks support before network egress).
  * `RetryPolicy`: exponential backoff with full jitter for rate limits (429) and network timeouts.
  * Fallback chains: seamless handoff to alternative models or local Ollama on cloud failure.
* **Secret Management:** Seamlessly pulls credentials from `SecretVault` (Windows Credential Manager via `keyring`) or environment variables.

---

## Phase 04: Sandboxed Tool Registry & Native Office Generation Suite

The Tool Subsystem (`services/python-core/jarvis/tools/`) provides a supervised, permission-governed, and sandboxed execution engine for tools invoked by autonomous agents and AI models.

### Key Capabilities
* **Untrusted Model Output:** AI output is treated strictly as intent. Direct shell execution (`shell=True`, `eval()`, `exec()`) is completely forbidden.
* **Automatic Schema Introspection:** `@tool` decorator inspects typed Python functions, parameter defaults, and docstrings to automatically generate JSON Schema definitions.
* **Granular Permission & Risk Model:** Enforces `READ`, `WRITE`, `EXECUTE`, `NETWORK`, `SYSTEM` permissions and `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` risk tiers with approval workflows (`AUTO_APPROVE`, `USER_APPROVAL`, `ALWAYS_DENY`).
* **FileSystem Sandbox:** Confinement strictly inside `data/workspace/` with canonical path resolution, symlink escape checks, null byte blocking, and filename sanitization.
* **Native Office Generation Suite:**
  * **DOCX (`office.create_docx`):** Microsoft Word document creation via `python-docx` with titles, headings, bullet lists, and tables.
  * **XLSX (`office.create_xlsx`):** Multi-sheet Excel workbook creation via `openpyxl` with styled headers and auto-adjusted columns.
  * **PPTX (`office.create_pptx`):** PowerPoint presentation creation via `python-pptx` with title and content slide layouts.
  * **PDF (`office.create_pdf`):** Formatted PDF report creation via `reportlab` with flowable paragraphs, tables, and page breaks.
* **Artifact Structural Verification:** Every generator reopens and verifies the structural integrity of the generated artifact before returning success.
* **Secret-Scrubbed Audit Logging:** Execution records and error traces are scrubbed of API keys, bearer tokens, and credentials before logging or event publishing.
* **AI ToolCall Bridge:** Translates normalized Phase 03 `ToolCall` objects into `ToolRequest` instances and produces conforming `ChatMessage.tool` responses.

---

## Phase 05: Autonomous Multi-Agent Runtime & Orchestration

The Autonomous Multi-Agent Runtime (`services/python-core/jarvis/agents/`) provides a supervised, bounded state machine for decomposing complex user goals into DAG execution plans, delegating to specialized agents, coordinating tools through Phase 04, independently verifying outputs, and synthesizing a single authoritative answer.

### Key Capabilities
* **Master Orchestrator State Machine:** Strict lifecycle (`IDLE` -> `PLANNING` -> `READY` -> `RUNNING` -> `VERIFYING` -> `COMPLETED`).
* **DAG Plan Decomposition & Validation:** `PlanValidator` prevents infinite loops, duplicate tasks, missing dependencies, and enforces cycle detection via Kahn's algorithm before execution.
* **Specialized Agent Roles (10 Built-in Agents):**
  * `PlannerAgent`: Goal decomposition into concurrent DAG waves.
  * `ResearchAgent`: Information gathering and structured evidence formulation.
  * `ReasoningAgent`: Logical trade-off evaluation and deduction.
  * `CodingAgent`: Code planning and coordination of Phase 04 Office generation tools.
  * `SecurityAgent`: Pre-execution security audits, permissions, and threat modeling.
  * `TestingAgent`: Test strategy, validation modes, and regression analysis.
  * `ReviewAgent`: Quality, consistency, and constraint audits.
  * `VerifierAgent`: Independent verification of artifacts, tool statuses, and observations.
  * `RecoveryAgent`: Failure classification and bounded retry/replan strategies.
  * `SynthesisAgent`: Compiles intermediate task outputs into a cohesive narrative.
* **Evidence-Based Verification:** Tasks are verified through physical artifact inspection (existence, non-zero bytes, structure) and tool result verification rather than blind trust.
* **Bounded Failure Recovery:** Automatic step retries (`max_step_retries=2`) and replans (`max_replans=2`) prevent infinite execution loops.
* **Checkpointing & Lifecycle Control:** Lightweight run serialization (`data/checkpoints/`) supporting `pause_run()`, `resume_run()`, and `cancel_run()`.
* **Single Authoritative JARVIS Response:** `FinalSynthesizer` consolidates all verified results, task metrics, and artifact paths into one clean response, hiding unnecessary internal chain-of-thought.

---

## Phase 06: Tri-Tier Memory Engine

The Tri-Tier Memory Engine (`services/python-core/jarvis/memory/`) provides a multi-layer, security-hardened memory system combining low-latency in-memory conversation tracking, durable relational event storage, and semantic vector retrieval.

### Key Capabilities
* **Tier 1 — Working Memory (Fast RAM Window):**
  * Sliding message window bounded by both token budget and message count with priority-based eviction.
  * Preserves critical system instructions and task context across evictions.
  * Overflow summarization preserving context continuity without unbounded token growth.
  * Memory snapshots (`MemorySnapshot`) for pause/resume state management.
* **Tier 2 — Structured Persistent Store (SQLite WAL):**
  * Persistent storage in `data/memory/jarvis-memory.db` configured with Write-Ahead Logging (WAL) and synchronous normal mode for high-concurrency read/write operations.
  * Transactional migration engine (`001_initial_memory_schema`, `002_add_indexes`) with automated version tracking.
  * Comprehensive schemas: `conversations`, `messages`, `memories`, `facts`, `preferences`, `tasks`, `artifacts`, `memory_events`, `summaries`.
  * Deduplication and upsert semantics for user preferences and facts.
  * Complete audit provenance tracking (`source_type`, `source_id`, `trust_level`, timestamps).
* **Tier 3 — Semantic Vector Retrieval (`sqlite-vec` + Cosine Fallback):**
  * Dense vector indexing with dimension verification (default 384-d).
  * Native hardware-accelerated KNN search via `sqlite-vec` extension with automatic graceful fallback to pure-Python cosine similarity.
  * `EmbeddingProvider` protocol with pluggable providers (`HashEmbeddingProvider` for fast local testing, mock provider for determinism).
* **Security & Memory Guardrails:**
  * **Recursive Secret Redaction:** Scrubbing of API keys (OpenAI, Anthropic, Gemini, HuggingFace, GitHub), Bearer tokens, passwords, and null bytes before persistence or retrieval.
  * **Prompt Injection Defense:** Strict heuristic classifier detecting override attempts (`ignore previous instructions`, `system prompt:`, `new instructions:`).
  * **Trust Classification:** Distinction between `USER_VERIFIED` and `MODEL_GENERATED` inputs. Suspicious or untrusted inputs are quarantined to lower trust tiers.
  * **Passive Context Isolation:** All retrieved memories injected into agent context are explicitly framed as passive reference data, never executable instructions.
  * **Scope Boundary Enforcement:** Strict isolation across `SESSION`, `CONVERSATION`, `USER`, `PROJECT`, and `GLOBAL` scopes. Cross-project memory retrieval is strictly prohibited.
* **6-Factor Hybrid Ranking:**
  * Deterministic scoring combining semantic similarity, temporal recency decay, memory importance, confidence rating, scope alignment, and task relevance:
    $$\text{final\_score} = \frac{w_{\text{sem}} S_{\text{sem}} + w_{\text{rec}} S_{\text{rec}} + w_{\text{imp}} S_{\text{imp}} + w_{\text{conf}} S_{\text{conf}} + w_{\text{scope}} S_{\text{scope}} + w_{\text{task}} S_{\text{task}}}{\sum w}$$
* **Multi-Agent Runtime Integration:**
  * Native memory access in `AgentContext` and `AgentExecutor` with automatic memory retrieval during execution.
  * Built-in agents (`ResearchAgent`, `CodingAgent`, `VerifierAgent`) leverage memory for long-term consistency, fact retention, and artifact tracking.

---

## Phase 07: Voice & Audio Pipeline

The Voice & Audio Pipeline (`services/python-core/jarvis/voice/`) turns ZARVIS into a voice-first assistant through a modular, hardware-agnostic audio processing loop integrated with the multi-agent runtime, memory, and sandboxed tools.

### Key Capabilities
* **Hardware-Agnostic Audio Abstraction:**
  * Abstract interfaces for capture (`BaseAudioCapture`) and playback (`BaseAudioPlayback`) with PCM 16-bit 16kHz standard contracts.
  * Virtual memory-backed audio drivers (`VirtualAudioCapture`, `VirtualAudioPlayback`) guaranteeing complete testability without physical microphones or speakers.
* **Voice Activity Detection (VAD):**
  * Pure standard-library RMS energy calculation with adaptive background noise floor estimation and hangover frame bridging.
  * Utterance boundary segmentation (`VADSegmenter`) enforcing minimum speech duration (0.3s) and hard recording caps (30s) to prevent infinite listening loops.
* **Intelligent STT Routing & Escalation:**
  * **Vosk Fast-Path:** Instant local offline speech recognition for short commands (< 5s) with sub-100ms response times.
  * **Faster-Whisper Escalation:** High-accuracy multilingual model (English, Hindi, Hinglish) invoked for complex utterances, low fast-path confidence (< 0.75), or on fast-path failures.
  * **Bounded Fallback:** Deterministic provider handoff preventing unbounded retry loops.
* **State Machine & Barge-In:**
  * Explicit conversation states (`IDLE`, `LISTENING`, `PROCESSING`, `SPEAKING`, `INTERRUPTED`, `ERROR`).
  * Barge-in interruption: detecting user speech during TTS playback cancels active audio playback tasks immediately with zero orphaned background tasks.
* **Local Neural TTS:**
  * Offline speech synthesis via Kokoro ONNX with configurable voices (`af_heart`) and variable speeds.
  * Streaming sentence chunking allowing incremental synthesis.
* **Agent & Memory Integration:**
  * Normalizes transcribed utterances into typed `VoiceRequest` objects delivered to Phase 05 `AgentOrchestrator`.
  * Preserves Phase 06 memory boundaries and security rules with zero raw microphone persistence by default.
* **Audio Security & Sandbox:**
  * Enforces maximum duration (30s) and payload size (25MB) limits.
  * Confines temporary audio files strictly within `data/workspace/temp/audio/` with path traversal defense and symlink blocking.
  * Scrubs telemetry payloads to guarantee raw audio bytes and API credentials are never logged or emitted over the event bus.
---

## Phase 08: Controlled Windows OS Automation Layer

The Windows OS Automation subsystem (`services/python-core/jarvis/os/`) enables safe, auditable, provider-agnostic computer interaction across display capture, monitor geometry, mouse, keyboard, window lifecycle, system clipboard, and host telemetry.

### Key Capabilities
* **Zero Arbitrary Execution Guarantee:**
  * No `shell=True`, `eval()`, `exec()`, `os.system()`, or raw PowerShell/CMD execution.
  * Every OS capability is registered as a strongly-typed tool in Phase 04 `ToolRegistry` governed by `ToolPolicyEngine`.
* **Hardware & OS Provider Abstraction:**
  * `OSProvider` Protocol contract decoupling high-level automation from operating system drivers.
  * `WindowsOSProvider`: Native Win32 driver leveraging `ctypes` (`user32.dll`, `gdi32.dll`, `kernel32.dll`) and `Pillow`. Zero external executable dependencies.
  * `MockOSProvider`: Virtual desktop canvas and input recorder providing deterministic, headless continuous integration without physical displays or input hardware.
* **Bounded Screen Capture & Display Awareness:**
  * Multimonitor discovery with coordinates, dimensions, primary flags, and DPI scaling factors.
  * Captures full displays or sub-regions into temporary sandboxed storage (`data/workspace/temp/screens/`) with path traversal prevention.
* **Controlled Mouse & Keyboard Subsystems:**
  * Relative and absolute cursor movement across `SCREEN`, `MONITOR`, and `WINDOW` coordinate frames with boundary validation against desktop limits.
  * Single, double, and right click execution; mouse wheel delta scrolling.
  * Destructive clicks (`is_destructive=True`) require explicit user authorization (`ApprovalMode.USER_APPROVAL`).
  * Unicode text typing with per-character delay pacing; allowlisted discrete key presses (`SUPPORTED_KEYS`).
  * Sensitive text typing (credentials, passwords, API tokens) automatically flagged and gated on user approval.
* **Deterministic Window Management & Ambiguity Guardrails:**
  * Enumerates top-level visible windows with titles, process IDs, and bounding geometry.
  * Raises `WindowAmbiguityError` when title/process queries match multiple candidates, preventing misdirected keystrokes or clicks.
  * Programmatic state operations: `FOCUS`, `MINIMIZE`, `MAXIMIZE`, `RESTORE`.
* **Privacy-Safe Clipboard & Telemetry:**
  * Plain text read, write, and clear operations bounded by length limits.
  * Strict privacy: clipboard strings and typed secrets are never echoed back in execution results and are automatically scrubbed from `JarvisEvent`s on `AsyncEventBus`.
* **Post-Action State Verification:**
  * `OSActionVerifier` automatically checks outcome states (cursor position, focused window handle, clipboard content) to confirm action success.
* **Full Ecosystem Integration:**
  * Seamlessly accessible to Phase 05 `AgentOrchestrator` via `ToolExecutor` / `AIToolBridge`.
  * Contextual OS state logged into Phase 06 `WorkingBuffer`.
  * Triggerable from Phase 07 Voice pipelines.

---

## Phase 09: Vision, Screen Understanding & Visual Grounding

The Visual Perception subsystem (`services/python-core/jarvis/vision/`) delivers robust, non-intrusive screen understanding and visual element grounding:
* **Perception-Action Separation:** Grounds coordinates and identifies targets without direct execution privileges.
* **Hierarchical Perception Pipeline:** Maps visual hierarchy across windows, regions, and UI elements.
* **Confidence & Ambiguity Guardrails:** Three-tier confidence ratings (`HIGH`, `MEDIUM`, `LOW`) with `TargetAmbiguityError` and `StaleObservationError` protection.
* **Privacy & Telemetry Redaction:** Automated detection and masking of sensitive password/credential input fields.
* **ToolRegistry Integration:** Native tools (`vision.screen.analyze`, `vision.element.find`, `vision.target.resolve`).

---

## Phase 10: Headless IPC Bridge (Python Core ↔ Node Gateway)

Phase 10 connects Python Core and Node.js Gateway via a production-grade, headless loopback IPC bridge:
* **Loopback TCP Transport:** Asynchronous socket communication on `127.0.0.1:8765` using standard library `asyncio` and `node:net` with zero external dependencies.
* **Newline-Delimited JSON-RPC:** Strict v1.0 protocol conformance (`JarvisRequest`, `JarvisResponse`, `JarvisEvent`) bounded to 10MB frames.
* **Mandatory Handshake:** Protocol negotiation via `ipc.handshake` before accepting commands.
* **Fault Tolerance & Heartbeats:** 10-second keepalive heartbeats, automatic state degradation, and jittered exponential backoff reconnection.
* **Bidirectional Event Streaming:** Seamlessly forwards Python Core `AsyncEventBus` notifications to Node Gateway and active WebSocket clients.
* **Enterprise Security & Observability:** Strict loopback binding, sensitive data scrubbing, timeout controls, concurrency caps, and live metrics via `system.diagnostics`.



