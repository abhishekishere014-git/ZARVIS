# JARVIS Tool Subsystem Security & Threat Model

## 1. Security Architecture Principles

1. **Untrusted Model Output:** LLMs are prone to hallucinations, prompt injections, and adversarial output generation. Tool arguments are strictly treated as untrusted user input and must pass schema and policy validation.
2. **Zero Arbitrary Execution:** No arbitrary shell commands, `shell=True`, `eval()`, or `exec()` exist within the execution pipeline. Tools are discrete, typed, compiled Python functions.
3. **Defense in Depth:** Security is validated at three consecutive layers:
   * Layer 1: Pydantic Schema Validation (type safety and required argument enforcement).
   * Layer 2: Tool Policy Engine (permission verification, risk assessment, human approval gates).
   * Layer 3: FileSystem Sandbox (canonical path resolution, traversal prevention, null-byte checks).

---

## 2. Threat Analysis & Mitigations

| # | Threat Vector | Risk Level | Architectural Mitigation |
| :-: | :--- | :---: | :--- |
| **1** | **Prompt Injection & Tool Hallucination** | HIGH | Tool calls must resolve to explicit IDs registered in `ToolRegistry`. Unknown or unregistered tools fail immediately. Arguments must strictly match generated JSON Schema. |
| **2** | **Directory Traversal (`../` or `..\`)** | CRITICAL | `FileSystemSandbox.resolve_safe_path()` checks for `..` tokens, resolves canonical paths via `.resolve()`, and raises `SandboxViolationError` if the path does not reside within `workspace_root`. |
| **3** | **Absolute Path Escape (`C:\Windows\...`)** | CRITICAL | Absolute paths are inspected against `workspace_root`. Any path resolving outside the workspace boundary is rejected. |
| **4** | **Symlink Jailbreak** | HIGH | `os.path.realpath()` is evaluated to ensure symlinks dereference exclusively to targets inside the sandbox workspace. |
| **5** | **Null Byte & Alternate Data Stream Injection** | HIGH | `sanitize_filename()` rejects null bytes (`\x00`), colons (`:`), pipe symbols (`|`), and illegal Windows filesystem characters. |
| **6** | **Denial of Service via Unbounded Generation** | MEDIUM | `OfficeLimits` enforces hard limits on file generation: max 50MB file size, max 10,000 table rows, max 200 columns, max 100 slides, max 200 PDF pages. |
| **7** | **Secret Leakage in Error Traces & Audits** | HIGH | `scrub_secrets()` recursively scans audit payloads and redacts API keys (`sk-...`), bearer tokens, passwords, and authorization headers before recording. |
| **8** | **Unauthorized Operation & Privilege Escalation** | CRITICAL | `SecurityProfile` specifies caller-granted permissions (`READ`, `WRITE`, `EXECUTE`, `NETWORK`, `SYSTEM`). Missing permissions result in immediate `ToolPolicyDecision(allowed=False)`. |
| **9** | **Indefinite Hangs & Zombie Coroutines** | MEDIUM | `ToolExecutor` wraps handler execution in `asyncio.wait_for()` with strict timeouts (`timeout_seconds`, default 30s). Timed-out tasks are cancelled. |
| **10** | **Corrupt Artifact Generation** | LOW | Tools actively verify generated artifacts (e.g. reopening DOCX, XLSX, PPTX, and inspecting PDF binary headers) before reporting success. |

---

## 3. Permission Model

```
                    TOOL PERMISSIONS
                           │
       ┌───────────┬───────┴───────┬───────────┐
       │           │               │           │
     READ        WRITE          NETWORK      SYSTEM
 (Inspect data) (Create files) (External)   (OS hooks)
                                               │
                                            EXECUTE
                                        (Subprocesses)
```

### Risk Tiers
* **LOW:** Safe, read-only operations or sandboxed office document generation (`AUTO_APPROVE`).
* **MEDIUM:** Modifying files inside sandbox, extensive local computations (`AUTO_APPROVE` if profile permits).
* **HIGH:** Write operations touching external directories or network interactions (`USER_APPROVAL`).
* **CRITICAL:** Process execution or OS configuration changes (`ALWAYS_DENY` or mandatory explicit user authorization).
