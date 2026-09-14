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
* [ ] **Phase 05:** Autonomous Agent Runtime (Planner $\to$ Executor $\to$ Verifier)
* [ ] **Phase 06:** Tri-Tier Memory Engine (Sliding Window + SQLite + `sqlite-vec`)
* [ ] **Phase 07:** Voice Pipeline (Vosk Fast-Path + Faster-Whisper + Kokoro ONNX)
* [ ] **Phase 08:** OS Automation (MSS Screen Capture, Win32 Hooks)
* [ ] **Phase 09:** Background Task & Cron Automation Engine
* [ ] **Phase 10:** Headless IPC Bridge (Python $\leftrightarrow$ Node Gateway link)
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


