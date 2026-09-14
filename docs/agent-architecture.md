# JARVIS Autonomous Multi-Agent Runtime & Orchestration Architecture

## 1. Architectural Philosophy

In the JARVIS platform, autonomous intelligence is structured as a **supervised multi-agent hierarchy**:
* **User Goal as Input:** High-level, underspecified instructions from the user are analyzed by the `PlannerAgent` and decomposed into a directed acyclic graph (DAG) of actionable tasks.
* **Deterministic Orchestration:** The `AgentOrchestrator` maintains a strict state machine (`IDLE` $\to$ `PLANNING` $\to$ `READY` $\to$ `RUNNING` $\to$ `VERIFYING` $\to$ `COMPLETED`).
* **Specialized Role Isolation:** Tasks are dispatched to single-responsibility agents (`Research`, `Reasoning`, `Coding`, `Security`, `Testing`, `Review`, `Verifier`, `Recovery`, `Synthesis`).
* **Phase 04 Sandbox & Policy Enforcement:** No agent can directly execute shell commands. All tool invocations route through Phase 04 `ToolExecutor` and `ToolPolicyEngine`.
* **Evidence-Based Verification:** No task success is accepted on faith. Artifacts, tool results, and outputs are physically inspected by the `AgentVerifier`.
* **Single Authoritative Synthesis:** Rather than raw internal agent chat logs, JARVIS delivers ONE coherent, user-facing summary with verified artifact paths.

---

## 2. End-to-End Orchestration Workflow

```
                         USER GOAL
                             │
                             ▼
                  ┌─────────────────────┐
                  │ JARVIS ORCHESTRATOR │
                  └──────────┬──────────┘
                             │
                             ▼
                        PlannerAgent
                             │
                    Execution Plan (DAG)
                             │
                             ▼
                      PlanValidator
              (Cycle check, bounds, agents)
                             │
             ┌───────────────┼────────────────┐
             ▼               ▼                ▼
       Research Agent   Reasoning Agent   Coding Agent
             │               │                │
             ▼               ▼                ▼
       Security Agent   Testing Agent    Review Agent
             │               │                │
             └───────────────┼────────────────┘
                             ▼
                     Tool Execution
                             │
                       Phase 04
                     ToolExecutor
                (Policy, Sandbox, Audit)
                             │
                             ▼
                      AgentObservation
                             │
                             ▼
                       AgentVerifier
                    (Evidence Inspection)
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
                 SUCCESS           FAILURE
                    │                 │
                    ▼                 ▼
               Next Step       RecoveryEngine
                                      │
                                Retry / Replan
                                      │
                                      ▼
                              FinalSynthesizer
                                      │
                                      ▼
                              ONE FINAL ANSWER
```

---

## 3. Specialized Built-in Agents

| Agent ID | Class Name | Capability | Core Responsibility |
| :--- | :--- | :--- | :--- |
| `agent.planner` | `PlannerAgent` | `PLANNING` | Decomposes goals into a bounded DAG plan with dependencies. |
| `agent.research` | `ResearchAgent` | `RESEARCH` | Gathers factual data, requirements, and evidence from approved sources. |
| `agent.reasoning` | `ReasoningAgent` | `REASONING` | Analyzes trade-offs, architecture options, and deductive conclusions. |
| `agent.coding` | `CodingAgent` | `CODING` | Formulates code plans and orchestrates Phase 04 Office generation tools. |
| `agent.security` | `SecurityAgent` | `SECURITY` | Pre-execution audits, permission checks, and threat modeling. |
| `agent.testing` | `TestingAgent` | `TESTING` | Formulates test strategies, verification criteria, and quality checks. |
| `agent.review` | `ReviewAgent` | `REVIEW` | Reviews outputs for consistency, formatting, and constraint compliance. |
| `agent.verifier` | `VerifierAgent` | `VERIFICATION` | Independently verifies task outputs, tool status, and artifact files. |
| `agent.recovery` | `RecoveryAgent` | `RECOVERY` | Diagnoses failures and recommends bounded retry or replanning actions. |
| `agent.synthesis` | `SynthesisAgent` | `SYNTHESIS` | Integrates intermediate findings into a cohesive final narrative. |

---

## 4. Layer Integration Contracts

* **Phase 03 (AI Provider Layer):** Agents access configured models via `AIRouter.generate()`. The router guarantees automatic fallback across OpenAI, Anthropic, Gemini, and Ollama.
* **Phase 04 (Tool Execution Layer):** When `CodingAgent` creates documents, it invokes `ToolExecutor.execute()`. This enforces permission checks, risk assessment, path confinement (`FileSystemSandbox`), and secret-scrubbed audit trails.
* **Phase 05 (Agent Layer):** The `AgentOrchestrator` manages multi-agent waves, checkpoints runs to disk/memory, and emits `JarvisEvent` messages across `AsyncEventBus`.
* **Phase 06 (Memory Layer - Upcoming):** Future integration point where sliding-window context and vector embeddings will hook into `AgentContext.prior_observations`.
