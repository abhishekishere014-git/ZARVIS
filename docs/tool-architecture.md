# JARVIS Tool Subsystem Architecture

## 1. Architectural Philosophy
In the JARVIS platform, AI models are treated as **untrusted planners**. Model-generated tool calls represent intent, not authority. The tool subsystem acts as an isolated, supervised boundary that guarantees:
1. **Zero Arbitrary Execution:** No arbitrary shell commands, `shell=True`, `eval()`, or `exec()`.
2. **Deterministic Governance:** Strict schema validation, permission checks, risk assessment, and approval enforcement before execution.
3. **Workspace Confinement:** All filesystem tools operate strictly within an authorized sandbox jail (`data/workspace/`).
4. **Structured Auditability:** Every tool invocation produces secret-scrubbed audit records and correlated events over the asynchronous event bus.

---

## 2. Core Execution Pipeline

```
                     AI MODEL / AGENT LOOP
                                │
                      Normalized ToolCall
                                │
                        ┌───────▼───────┐
                        │ AIToolBridge  │
                        └───────┬───────┘
                                │
                        ToolRequest Model
                                │
                        ┌───────▼───────┐
                        │ ToolExecutor  │
                        └───────┬───────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
      ┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
      │ ToolRegistry  │ │ PolicyEngine  │ │ FileSystem    │
      │ • Resolution  │ │ • Permissions │ │ Sandbox       │
      │ • Schema Valid│ │ • Risk Level  │ │ • Confinement │
      └───────────────┘ │ • Approval    │ │ • Sanitization│
                        └───────────────┘ └───────────────┘
                                │
                        ┌───────▼───────┐
                        │ Execution     │ (Timeout supervised)
                        │ Handler       │ (Context injected)
                        └───────┬───────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
      ┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
      │ Artifact      │ │ AsyncEventBus │ │ AuditLogger   │
      │ Verification  │ │ tool.* events │ │ Secret Scrub  │
      └───────────────┘ └───────────────┘ └───────────────┘
                                │
                        ┌───────▼───────┐
                        │  ToolResult   │
                        └───────────────┘
```

---

## 3. Module Hierarchy & Responsibilities

| Module | File | Core Responsibility |
| :--- | :--- | :--- |
| **Contracts** | `jarvis/tools/models.py` | Immutable Pydantic models: `ToolDefinition`, `ToolRequest`, `ToolResult`, `ToolExecutionContext`, `ToolPolicyDecision`, `ToolAuditEvent`. |
| **Errors** | `jarvis/tools/errors.py` | Typed exception taxonomy (`SandboxViolationError`, `ToolExecutionTimeoutError`, `ResourceLimitExceededError`, etc.). |
| **Permissions** | `jarvis/tools/permissions.py` | Granular permission enum (`READ`, `WRITE`, `EXECUTE`, `NETWORK`, `SYSTEM`) and `SecurityProfile`. |
| **Sandbox** | `jarvis/tools/sandbox.py` | `FileSystemSandbox`: Path resolution, null-byte checks, directory traversal blocking, safe filename sanitization. |
| **Policy** | `jarvis/tools/policy.py` | `ToolPolicyEngine`: Evaluates tool requests against caller permissions, risk tiers, and sandbox constraints. |
| **Decorator** | `jarvis/tools/decorator.py` | `@tool` decorator with automated schema generation via Python typing inspection and docstring parsing. |
| **Registry** | `jarvis/tools/registry.py` | `ToolRegistry`: Discovery, registration, duplicate checks, capability filtering, and AI schema export. |
| **Executor** | `jarvis/tools/executor.py` | `ToolExecutor`: Supervised execution pipeline enforcing timeouts, event dispatch, and audit emission. |
| **Audit** | `jarvis/tools/audit.py` | `AuditLogger` and `scrub_secrets`: Recursive regex redaction of API keys, tokens, and passwords. |
| **Bridge** | `jarvis/tools/bridge.py` | `AIToolBridge`: Converts Phase 03 `ToolCall` into `ToolRequest` and formats return `ChatMessage.tool`. |
| **Built-ins** | `jarvis/tools/builtins/` | Native Office Generation Suite (`DOCX`, `XLSX`, `PPTX`, `PDF`). |

---

## 4. Automatic Schema Introspection
Tools are declared using the `@tool` decorator on typed async Python functions:

```python
@tool(
    tool_id="office.create_docx",
    description="Generate a professional Word document",
    category="office",
    permissions={ToolPermission.WRITE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=30.0,
)
async def create_docx(
    filename: str,
    title: str,
    sections: List[Dict[str, Any]],
    subtitle: Optional[str] = None,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    ...
```

The decorator automatically:
1. Omits injected runtime dependencies (e.g. `context: ToolExecutionContext`).
2. Translates Python types (`str`, `int`, `float`, `bool`, `List`, `Dict`, `Optional`) into standard JSON Schema properties.
3. Parses Sphinx/Google style docstrings to populate property descriptions.
4. Categorizes optional parameters (with defaults or `Optional`) vs required parameters.
5. Produces an immutable `ToolDefinition` instance attached to the function.

---

## 5. Event Bus Integration & Correlation
The `ToolExecutor` publishes lifecycle events over the shared `AsyncEventBus` while preserving distributed tracing correlation:
* `tool.requested`: Dispatched when an execution request is received.
* `tool.authorized`: Dispatched when policy engine approves execution.
* `tool.denied`: Dispatched when permissions, risk, or sandbox rules reject execution.
* `tool.started`: Dispatched immediately prior to handler invocation.
* `tool.timeout`: Dispatched when execution exceeds `timeout_seconds`.
* `tool.completed`: Dispatched upon successful output validation.
* `tool.failed`: Dispatched if an unhandled error or structural verification failure occurs.
