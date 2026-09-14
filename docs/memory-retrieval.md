# JARVIS Memory Retrieval & Ranking Specification

## 1. Deterministic 6-Factor Hybrid Formula

To eliminate hallucinations and guarantee reproducible ranking across queries, candidate memories from Working, Structured, and Semantic stores are evaluated using a deterministic composite score:

$$\text{Final Score} = \frac{\sum_{i=1}^6 w_i \cdot S_i}{\sum_{i=1}^6 w_i}$$

Where:
* $S_{\text{sem}}$ (**Semantic Similarity**): Cosine similarity in $[0.0, 1.0]$ between the query vector and candidate embedding.
* $S_{\text{rec}}$ (**Recency Score**): Exponential half-life decay $\exp(-0.693 \cdot \Delta t / t_{1/2})$ where $t_{1/2} = 14\text{ days}$.
* $S_{\text{imp}}$ (**Importance Weight**): Intrinsic record importance in $[0.0, 1.0]$.
* $S_{\text{conf}}$ (**Epistemic Confidence**): Epistemic certainty in $[0.0, 1.0]$.
* $S_{\text{scope}}$ (**Scope Alignment**): Alignment factor (Matching project/scope $= 1.0$, Global $= 0.85$, Unrelated project $= 0.0$).
* $S_{\text{task}}$ (**Task Alignment**): Active task context match ($1.0$ if matching, $0.5$ default).

Default Weights:
$$\begin{aligned}
w_{\text{sem}} &= 0.35 \\
w_{\text{rec}} &= 0.20 \\
w_{\text{imp}} &= 0.15 \\
w_{\text{conf}} &= 0.10 \\
w_{\text{scope}} &= 0.10 \\
w_{\text{task}} &= 0.10
\end{aligned}$$

---

## 2. Context Builder & Token Budgeting

The `MemoryContextBuilder` enforces strict token boundaries (`ContextBudget`):
* `max_total_tokens`: Hard upper bound for all memory-injected sections (default 4,096).
* `reserved_system_tokens`: Invariant system prompt reservation (default 512).
* `max_memory_tokens`: Ceiling for durable and semantic memories (default 1,536).
* `max_working_tokens`: Ceiling for recent conversation history (default 2,048).
