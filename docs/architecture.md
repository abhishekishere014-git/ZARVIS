# JARVIS Platform — Hybrid Architecture Specification

## 1. Architectural Philosophy

JARVIS is engineered as a **hybrid multi-runtime platform**, assigning computational responsibilities strictly according to runtime strengths:

```
                          ┌───────────────────────────────┐
                          │         JARVIS CLIENTS        │
                          │   (Desktop, Web, Tray, CLI)   │
                          └───────────────┬───────────────┘
                                          │ WebSocket / HTTP
                          ┌───────────────▼───────────────┐
                          │          NODE GATEWAY         │
                          │      (@jarvis/node-gateway)   │
                          │                               │
                          │  - Client WebSockets & State  │
                          │  - Protocol Validation (Zod)  │
                          │  - Realtime Event Streaming   │
                          │  - UI & Web API Surface       │
                          └───────────────┬───────────────┘
                                          │ Loopback IPC (v1.0 Protocol)
                          ┌───────────────▼───────────────┐
                          │          PYTHON CORE          │
                          │    (jarvis-python-core)       │
                          │                               │
                          │  - Model-Agnostic AI Engines  │
                          │  - Planner/Executor/Verifier  │
                          │  - Local STT/TTS Pipelines    │
                          │  - Multi-Tiered Memory        │
                          │  - OS Desktop Automation      │
                          │  - Sandboxed Tool System      │
                          │  - OS Keyring Secret Vault    │
                          └───────────────────────────────┘
```

---

## 2. Separation of Concerns

### Python Core (`services/python-core/`)
* **Core Competencies:** AI model orchestration, autonomous agent execution loops, low-latency audio processing (Vosk, Faster-Whisper, Kokoro TTS), computer vision, semantic memory (`sqlite-vec`), Windows OS control (`pywin32`, `mss`), Office document synthesis (`python-docx`, `openpyxl`, `python-pptx`), and security-sensitive execution.
* **Architecture Pattern:** Layered micro-kernel with an asynchronous, fault-isolated in-process event bus (`AsyncEventBus`), service lifecycle supervisor (`JarvisEngine`), and Pydantic v2 settings.
* **Security:** Operates the `SecretVault` via Windows Credential Manager (`keyring`). Raw API keys never leave Python memory or touch the frontend network transport.

### Node Gateway (`services/node-gateway/`)
* **Core Competencies:** High-concurrency client multiplexing, bi-directional WebSocket session management, JSON-RPC routing, and UI-facing REST endpoints.
* **Architecture Pattern:** Lightweight asynchronous gateway using native Node.js HTTP + WebSocket server, runtime configuration validation via Zod, and structured JSON telemetry.
* **Rule:** Node does not duplicate agent reasoning, AI provider logic, or desktop automation.

### Shared Protocol (`packages/protocol/`)
* **Standard:** Versioned protocol contracts (`v1.0`) defining:
  * `JarvisRequest`: Client-to-core invocations with typed payloads.
  * `JarvisResponse`: Explicit success/error contracts with standard error codes.
  * `JarvisEvent`: Realtime pub/sub notifications with correlation IDs.
* **Type Symmetry:** Maintained symmetrically across TypeScript (Zod schemas) and Python (Pydantic v2 models).

---

## 3. Security & Isolation Model

1. **Loopback-Only Network Binding:** Both Python Core (`127.0.0.1:8765`) and Node Gateway (`127.0.0.1:3000`) strictly refuse non-loopback bindings (such as `0.0.0.0`). Public exposure is forbidden by default.
2. **Secret Isolation:** Provider credentials (OpenAI, Anthropic, Gemini, etc.) reside in the host OS credential manager via `keyring`. They are never passed over WebSocket IPC or rendered into client-side UI states.
3. **Fault Isolation:** The asynchronous event bus executes subscribers inside individual supervised tasks. A crash or unhandled exception in one listener does not destabilize the bus or other subscribers.
4. **Clean Teardown:** Both runtimes support structured graceful shutdowns, draining in-flight requests and event dispatches before process termination.
5. **Sandboxed Tool Execution Boundary:** All tool execution is mediated by `ToolPolicyEngine`, enforcing permission checks, risk assessment, and workspace confinement via `FileSystemSandbox`. AI output is treated as untrusted input; arbitrary shell execution (`shell=True`, `eval`, `exec`) is strictly prohibited.

---

## 4. Subsystems

### AI Provider Layer (`jarvis.ai`)
* Model-agnostic abstraction for OpenAI, Anthropic, Gemini, and Ollama.
* Capability-based routing, retries with jittered exponential backoff, and fallback chains.

### Sandboxed Tool Registry & Office Generation (`jarvis.tools`)
* Automated schema generation from typed Python functions using `@tool`.
* Strict filesystem confinement rooted in `data/workspace/`.
* Native office generation suite: DOCX (`python-docx`), XLSX (`openpyxl`), PPTX (`python-pptx`), PDF (`reportlab`) with post-generation artifact verification.
* Structured, secret-scrubbed audit logging and lifecycle event publishing.

### Autonomous Multi-Agent Runtime & Orchestration (`jarvis.agents`)
* Master orchestrator with DAG-based plan decomposition, Kahn's algorithm cycle detection, and wave-based execution.
* 10 specialized built-in agents (Planner, Research, Reasoning, Coding, Security, Testing, Review, Verifier, Recovery, Synthesis).
* Evidence-based verification inspecting physical artifacts and tool results.
* Bounded recovery engine managing retries and replans without infinite loops.
* Single coherent answer synthesis delivering verified responses to users.

### Tri-Tier Memory Engine (`jarvis.memory`)
* **Tier 1 (Working Memory):** Sliding window buffer in RAM with token and message count constraints, priority eviction, overflow summarization, and memory snapshots.
* **Tier 2 (Structured Store):** Persistent SQLite store (`data/memory/jarvis-memory.db`) with Write-Ahead Logging (WAL), automated migration runner, indexed relational schemas (`conversations`, `messages`, `memories`, `facts`, `preferences`, `tasks`, `artifacts`, `memory_events`, `summaries`), and audit provenance.
* **Tier 3 (Semantic Retrieval):** Hardware-accelerated KNN vector search via `sqlite-vec` (v0.1.9) with pure-Python cosine similarity fallback, pluggable `EmbeddingProvider` protocols, and dense vector index.
* **Security & Guardrails:** Recursive secret redaction (keys, bearer tokens, passwords, null bytes), prompt injection heuristics, trust classification (`USER_VERIFIED` vs `MODEL_GENERATED`), passive reference context isolation, and strict cross-project isolation.
* **Hybrid 6-Factor Ranking:** Deterministic retrieval ranker combining semantic similarity, temporal recency decay, importance, confidence, scope matching, and task affinity.
* **Multi-Agent Memory Integration:** Native hooks into `AgentContext` and `AgentExecutor` for persistent memory access and context enrichment across agent task waves.



