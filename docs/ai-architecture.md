# JARVIS Platform — AI Provider Architecture & Specification (Phase 03)

## 1. Requirements Engineering

### 1.1 Objective & Scope
The objective of Phase 03 is to construct a **model-agnostic, resilient, asynchronous AI Provider Layer** within `services/python-core/jarvis/ai/`.
JARVIS must communicate with any supported AI model through one standardized internal contract. The orchestration core must be completely insulated from vendor-specific payload shapes, authentication schemes, streaming mechanisms, tool-use formats, and exception hierarchies.

### 1.2 Functional Requirements (FR)

| ID | Requirement | Description |
| :--- | :--- | :--- |
| **FR-01** | Unified AI Provider Interface | Standardized `AIProvider` Protocol exposing `generate()`, `stream()`, `capabilities()`, and `health()`. |
| **FR-02** | Text Generation | Standard non-streaming completion returning a normalized `LLMResponse`. |
| **FR-03** | Streaming Responses | Asynchronous token and tool-call delta streaming returning `AsyncIterator[AIStreamEvent]`. |
| **FR-04** | Provider/Model Metadata | Detailed capability flags (`ModelCapabilities`) per model (tools, vision, streaming, json, context window). |
| **FR-05** | Standardized Chat Messages | Canonical `ChatMessage` model supporting `system`, `user`, `assistant`, `tool`, and multimodal content placeholders. |
| **FR-06** | Standardized Tool Definitions | Provider-independent `ToolDefinition` with valid JSON Schema parameter validation. |
| **FR-07** | Normalized Tool Calls | Symmetrical bi-directional translation of tool calls (OpenAI, Anthropic, Gemini, Ollama) into `ToolCall`. |
| **FR-08** | Dynamic Router | `AIRouter` to resolve optimal provider and model based on task requirements, availability, and priority. |
| **FR-09** | Controlled Fallback | Automated failover to configured secondary/tertiary providers upon infrastructure or capacity faults. |
| **FR-10** | Normalized Error Hierarchy | Typed domain exceptions (`AIError`, `RateLimitError`, `AuthenticationError`, `AITimeoutError`, etc.). |
| **FR-11** | Local Ollama Integration | Offline local inference support over loopback REST API with zero external cloud dependencies. |
| **FR-12** | Extensibility | Adding a new provider adapter requires zero changes to core routing or orchestration logic. |
| **FR-13** | Credential Isolation | API keys fetched in-memory strictly from `SecretVault` (OS Keyring); never logged or exposed to IPC. |
| **FR-14** | Cancellation & Barge-In | Streaming generators cleanly abort and release sockets upon `asyncio.CancelledError`. |
| **FR-15** | Strict Timeout Enforcement | Granular connection and read timeouts on all upstream provider requests. |

### 1.3 Non-Functional Requirements (NFR)
* **Asynchronous & Non-blocking:** 100% async I/O (`httpx.AsyncClient` with connection pooling); zero thread-blocking calls.
* **Type Safety:** Strict Python 3.12+ type hints and Pydantic v2 validation across all messages, requests, and responses.
* **Testability:** Full unit testability with mockable HTTP transports; zero live API keys required for automated CI tests.
* **Resilience:** Bounded exponential backoff with jitter for transient 429/503 errors; no infinite retry storms.
* **Security:** Loopback defaults for local runtimes; strict credential masking in structured logs.

---

## 2. Reference Capability Analysis

We audited how the reference repositories handled AI providers to retain valuable ideas and discard flaws:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 REFERENCE CAPABILITY AUDIT                             │
├───────────────────────┬──────────────────────────────────┬─────────────────────────────┤
│ Repository            │ Adoptable Concepts               │ Anti-Patterns Discarded     │
├───────────────────────┼──────────────────────────────────┼─────────────────────────────┤
│ codewithbro95/J.A.R.V.│ Local Ollama REST/NDJSON parsing;│ Hardcoded model strings in  │
│ I.S                   │ Multimodal vision readiness.     │ .env; raw string matching   │
│                       │                                  │ for function calling.       │
├───────────────────────┼──────────────────────────────────┼─────────────────────────────┤
│ aerele/jarvis         │ Dynamic tool metadata cataloging;│ Monolithic ERP coupling;    │
│                       │ Structured schema validation.    │ Synchronous blocking calls. │
├───────────────────────┼──────────────────────────────────┼─────────────────────────────┤
│ JoelShine / Aryan /   │ None (Obsolete AIML / brittle    │ Monolithic scripts; no      │
│ kishanrajput / Arnav  │ prompt strings).                 │ fallback; no error handling.│
└───────────────────────┴──────────────────────────────────┴─────────────────────────────┘
```

---

## 3. System Architecture & Component Design

```
                       ┌─────────────────────────────────────┐
                       │          JARVIS CORE / AGENT        │
                       └──────────────────┬──────────────────┘
                                          │ LLMRequest
                       ┌──────────────────▼──────────────────┐
                       │              AI ROUTER              │
                       │   (jarvis/ai/router.py)             │
                       │                                     │
                       │   - Selects Provider & Model        │
                       │   - Enforces Fallback Policy        │
                       │   - Governs Retry / Backoff Loop    │
                       └─────────┬─────────────────┬─────────┘
                                 │                 │
              Fallback Candidate │                 │ Primary Candidate
                                 ▼                 ▼
                       ┌─────────────────────────────────────┐
                       │          PROVIDER REGISTRY          │
                       │   (jarvis/ai/registry.py)           │
                       └──────────────────┬──────────────────┘
                                          │ AIProvider Protocol
                 ┌────────────────────────┼────────────────────────┐
                 ▼                        ▼                        ▼
       ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
       │ OpenAI Adapter   │     │ Anthropic Adapter│     │ Gemini Adapter   │ ... [Ollama]
       │ (openai.py)      │     │ (anthropic.py)   │     │ (gemini.py)      │
       └─────────┬────────┘     └─────────┬────────┘     └─────────┬────────┘
                 │                        │                        │
                 ▼                        ▼                        ▼
       [OpenAI v1/chat]          [Anthropic v1/messages]  [Gemini v1beta/models]
```

### Module Boundaries (`services/python-core/jarvis/ai/`)
* **`models.py`:** Core data contracts (`ChatMessage`, `LLMRequest`, `LLMResponse`, `ToolDefinition`, `ToolCall`, `AIStreamEvent`, `TokenUsage`).
* **`capabilities.py`:** `ModelCapabilities` and default capability matrix for known models.
* **`errors.py`:** Normalized exception taxonomy (`AIError`, `RateLimitError`, `AuthenticationError`, `AITimeoutError`, etc.).
* **`base.py`:** The `AIProvider` Protocol and `BaseAIProvider` template class.
* **`registry.py`:** Thread-safe provider registration and lookup service.
* **`retry.py`:** Configurable exponential backoff policy with jitter and cancellation awareness.
* **`router.py`:** Deterministic, capability-aware router with transparent failover.
* **`providers/`:** Concrete, isolated adapters for OpenAI, Anthropic, Gemini, and Ollama using pooled `httpx.AsyncClient`.

---

## 4. Normalized Core Contracts

### 4.1 Chat Message Model
```python
class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class ChatMessage(BaseModel):
    role: Role
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### 4.2 Tool Calling & Definition
```python
class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]  # Strict JSON Schema

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]
```

### 4.3 Streaming Event Model
```python
class StreamEventType(str, Enum):
    TEXT_DELTA = "text_delta"
    TOOL_CALL_DELTA = "tool_call_delta"
    REASONING_DELTA = "reasoning_delta"
    USAGE = "usage"
    COMPLETED = "completed"
    ERROR = "error"

class AIStreamEvent(BaseModel):
    type: StreamEventType
    text: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    usage: Optional[TokenUsage] = None
    error: Optional[str] = None
    finish_reason: Optional[str] = None
```

### 4.4 Normalized Error Taxonomy
* `AIError` (Base domain exception)
  * `AuthenticationError` (401/403 - Invalid API Key, Non-retryable)
  * `InvalidRequestError` (400 - Bad Schema/Prompt, Non-retryable)
  * `ModelNotFoundError` (404 - Unknown Model, Non-retryable)
  * `CapabilityNotSupportedError` (Requesting tools on non-tool model, Non-retryable)
  * `AICancelledError` (User cancelled request, Non-retryable)
  * `RateLimitError` (429 - Quota/TPM exceeded, Retryable with backoff)
  * `ProviderUnavailableError` (500/502/503/504, Connection refused, Retryable / Fallback)
  * `AITimeoutError` (Request timed out, Retryable / Fallback)
  * `AIStreamError` (Stream interrupted mid-generation, Fallback)

---

## 5. Security & Threat Considerations
1. **Zero Secret Leakage:** Keys are injected from `SecretVault` directly into adapter headers (`Authorization: Bearer ...`) and wiped from memory during shutdown. Never stored in request logs or error messages.
2. **Loopback Protection:** Ollama adapter connects to `http://127.0.0.1:11434` by default; prevents accidental requests to untrusted external endpoints.
3. **Payload Sanitization:** Exception logging truncates raw prompt payloads to prevent confidential user data from persisting to disk.
