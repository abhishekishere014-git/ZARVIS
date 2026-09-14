# JARVIS Agent Runtime Security & Threat Model

## 1. Security Architecture Principles

1. **AI Output is Data, Never Code:** Model output is treated as untrusted data. Under no circumstances is model output evaluated via `eval()`, `exec()`, or passed to dynamic shell processes (`shell=True`).
2. **Deterministic Governance:** All tool execution is strictly routed through the Phase 04 `ToolExecutor`. Agents cannot self-authorize, grant themselves permissions, or bypass `ToolPolicyEngine`.
3. **Sandbox Confinement:** File writing is jailed to `data/workspace/` by the `FileSystemSandbox`. Path traversal (`../`), null bytes (`\x00`), and symlinks escaping the workspace raise immediate `SandboxViolationError`.
4. **Evidence-Based Verification:** The `AgentVerifier` verifies physical file existence, file size, format headers, and exit statuses before any task is certified as `PASSED`.

---

## 2. Threat Analysis & Mitigations

| Threat Vector | Severity | Mitigation Strategy |
| :--- | :---: | :--- |
| **Circular Plan Attack / Infinite Loops** | HIGH | `PlanValidator` uses Kahn's algorithm for DAG cycle detection before execution. Cycles raise `PlanValidationError`. |
| **Unbounded Step Exhaustion** | MEDIUM | `PlanValidator` enforces `max_steps` (default 20). Excessive steps reject the plan immediately. |
| **Infinite Failure Retries** | MEDIUM | `RecoveryEngine` enforces bounded step retries (`max_step_retries=2`) and replans (`max_replans=2`). |
| **Privilege Escalation** | CRITICAL | Agents declare explicit `allowed_tools`. Invocations outside this set are rejected with status `denied`. |
| **Disabled Agent Invocation** | MEDIUM | `PlanValidator` validates that assigned agents exist in `AgentRegistry` and are `enabled`. |
| **Hallucinated Task Success** | HIGH | `AgentVerifier` independently checks physical disk artifacts and tool result flags. Fabricated successes fail verification. |
| **Secret Leakage in Observations & Audits** | HIGH | Phase 04 `scrub_secrets` redacts API keys (`sk-...`), bearer tokens, and credentials from all observations and audit events. |
| **Zombie Coroutines & Process Hangs** | MEDIUM | Individual tasks enforce strict timeouts (`timeout_seconds`, default 60s). `asyncio.wait_for()` cancels hanging tasks. |
| **Uncontrolled Agent-to-Agent Messaging** | MEDIUM | Inter-agent communication is mediated via structured, validated `AgentMessage` schemas. Unrestricted free-form execution is prevented. |

---

## 3. Dangerous Pattern Static Code Audit
The entire codebase was scanned and verified free of the following prohibited patterns:
* `shell=True`: **Zero occurrences**
* `eval(`: **Zero occurrences**
* `exec(`: **Zero occurrences**
* `os.system(`: **Zero occurrences**
* `subprocess.Popen(`: **Zero occurrences**
* `subprocess.run(`: **Zero occurrences**
