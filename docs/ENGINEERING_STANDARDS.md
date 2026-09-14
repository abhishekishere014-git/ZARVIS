# JARVIS Engineering & Quality Governance Standards

> **Core Philosophy:** *Requirements first. Design second. Code third. Verification always.*

This document codifies the mandatory Software Development Lifecycle (SDLC) and Quality Gates governing every phase of the JARVIS platform build. No phase is declared complete, and no subsequent phase may begin, without strictly satisfying every quality gate defined herein.

---

## 1. The Phase Execution Lifecycle

Every development phase follows an unbroken 12-step engineering cycle:

```text
1. REQUIREMENTS ENGINEERING
        ↓
2. SYSTEM ANALYSIS & CAPABILITY AUDIT
        ↓
3. ARCHITECTURE & CONTRACT DESIGN
        ↓
4. IMPLEMENTATION (CLEAN & MODULAR)
        ↓
5. CODE REVIEW & STATIC ANALYSIS
        ↓
6. UNIT TESTING (HAPPY PATH & EDGE CASES)
        ↓
7. INTEGRATION & CONTRACT TESTING
        ↓
8. SECURITY & THREAT REVIEW
        ↓
9. PERFORMANCE & RESOURCE AUDIT
        ↓
10. DOCUMENTATION UPDATE
        ↓
11. BUILD & RUNTIME VALIDATION
        ↓
12. PHASE ACCEPTANCE GATE
```

---

## 2. Mandatory Quality Gates

A phase achieves **ACCEPTANCE** only when all 10 gates pass verified validation:

| # | Quality Gate | Requirement & Validation Standard |
| :-: | :--- | :--- |
| **1** | **Requirements** | Exact functional scope, non-functional requirements (NFRs), explicit acceptance criteria, and out-of-scope boundaries documented. |
| **2** | **Design** | Module boundaries, typed protocols/contracts, data flow diagrams, dependency analysis, and threat models drafted before code modification. |
| **3** | **Implementation** | SOLID principles, DRY, strict type annotations, small cohesive modules, no god objects, no dead code, and zero unnecessary abstraction. |
| **4** | **Unit Tests** | High test coverage for individual functions and classes. Every unit test must test real behavior with zero mocks where local primitives exist. |
| **5** | **Integration Tests**| End-to-end service coordination, protocol schema validation, IPC boundaries, and cross-runtime integration verified. |
| **6** | **Security Review** | Least-privilege defaults, zero hardcoded secrets, input sanitization via strict schemas, no `shell=True`/`eval()`, and secret isolation via OS Keyring. |
| **7** | **Performance Check**| Concurrency validation (no thread-blocking I/O in async loops), low latency overhead, memory footprint sanity, and clean resource cleanup. |
| **8** | **Documentation** | Updated `README.md`, technical architecture docs, API/protocol docstrings, and inline architectural comments. |
| **9** | **Build Validation** | Clean compilation across all runtimes (`tsc`, `pytest`, `pip`, `npm`), zero linter/type errors, and reproducible build scripts. |
| **10**| **Acceptance Criteria**| Every user requirement for the phase verified through automated tests or live runtime checks. Zero test failures permitted. |

---

## 3. Strict Rules of Engagement

### 1. Build $\to$ Test $\to$ Audit $\to$ Fix $\to$ Retest
* AI-generated code is **never assumed to be correct**.
* Every module must be compiled, executed, tested, and audited in the real environment.
* If any test fails, **advancement to the next phase is strictly halted**. The failure must be analyzed, resolved, and re-tested until 100% green.

### 2. Capability Extraction, Never Blind Copy-Paste
* When learning from reference repositories (such as `codewithbro95`, `kishanrajput23`, `JoelShine`, `Aryan-0001`, `aerele`, `sharith45`, `Arnav3241`), we extract the **underlying architectural capability** (e.g., Vosk low-latency STT, Office doc synthesis, tool registries).
* We strictly **reject and discard** reference anti-patterns:
  * ❌ No monolithic scripts
  * ❌ No obsolete rule-based pattern matching (AIML)
  * ❌ No unsafe subprocess strings (`shell=True`, `os.system`)
  * ❌ No plaintext API keys committed to disk
  * ❌ No unrestricted or unconfirmed computer control
  * ❌ No blocking audio loops (`engine.runAndWait()`)
  * ❌ No hardcoded provider implementations or vendor lock-in
  * ❌ No tightly coupled UI and business logic

### 3. Local-First and Secure Defaults
* All network listeners default to loopback (`127.0.0.1` / `localhost`). Binding to `0.0.0.0` is blocked at the schema validation level.
* Credentials and keys must reside strictly in the OS Credential Vault (`keyring`) and never travel over network IPC or touch frontend state.

---

## 4. Phase Acceptance Audit Matrix

Every completed phase report must publish its formal audit matrix:

```text
[✓] Requirements Engineering   Passed — Scope, NFRs, Acceptance Criteria defined
[✓] Design & Contracts         Passed — Interfaces, Protocols, Architecture verified
[✓] Clean Implementation       Passed — Typed, modular, decoupled
[✓] Unit Tests                 Passed — 100% test pass rate
[✓] Integration Tests          Passed — Multi-service & protocol validation clean
[✓] Security Review            Passed — Least privilege, credential isolation verified
[✓] Performance Check          Passed — Async non-blocking concurrency confirmed
[✓] Documentation              Passed — README and architecture docs updated
[✓] Build / Packaging          Passed — Monorepo scripts and builds green
[✓] Quality Gate Acceptance    Phase Accepted — Authorized to advance
```
