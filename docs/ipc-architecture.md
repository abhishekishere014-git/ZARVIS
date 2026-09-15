# JARVIS Platform — Headless IPC Bridge Architecture (Phase 10)

## 1. Overview & Purpose

Phase 10 introduces the high-performance, headless Inter-Process Communication (IPC) bridge between **Python Core** (`127.0.0.1:8765`) and **Node.js Gateway** (`127.0.0.1:3000`).

The bridge establishes a production-grade, asynchronous communication channel that strictly complies with the shared JARVIS v1.0 JSON-RPC specification (`JarvisRequest`, `JarvisResponse`, `JarvisEvent`).

```
┌───────────────────────────────┐                  ┌───────────────────────────────┐
│         NODE GATEWAY          │                  │          PYTHON CORE          │
│   (services/node-gateway)     │                  │    (services/python-core)     │
│                               │  Loopback TCP    │                               │
│  IPCClient                    │  127.0.0.1:8765  │  IPCServer                    │
│  ├── Framing / MessageBuffer  │ ◄══════════════► │  ├── Framing (read/write)     │
│  ├── Pending Requests Map     │                  │  ├── IPCRouter (allowlist)    │
│  ├── Handshake & Reconnection │                  │  ├── Handshake Enforcement    │
│  └── Event Forwarding (WS)    │                  │  └── EventBus Forwarding      │
└───────────────────────────────┘                  └───────────────────────────────┘
```

---

## 2. Core Technical Specifications

| Feature | Specification | Rationale |
| :--- | :--- | :--- |
| **Transport** | Streaming localhost TCP socket (`node:net` / `asyncio`) | Zero external dependencies; high throughput, minimal latency |
| **Network Binding** | Strictly `127.0.0.1` (loopback only) | Non-loopback addresses (`0.0.0.0`, external IPs) strictly rejected |
| **Framing Format** | Newline-delimited JSON-RPC (`\n`) | UTF-8 encoded single-line frames, deterministic boundary recovery |
| **Max Frame Size** | 10 MB default (`10 * 1024 * 1024` bytes) | Protects against memory exhaustion / DOS |
| **Request Timeout** | 30 seconds default | Prevents client hanging on slow/stalled operations |
| **Heartbeat Interval**| 10 seconds | Automated keepalive (`system.ping`) and dead-connection detection |
| **Reconnection Policy**| Exponential backoff with jitter (1s – 10s) | Prevents reconnection thundering herds |
| **Concurrency Guard** | Bounded concurrent tasks (default 100) | Returns `SERVER_BUSY` when saturated |

---

## 3. Communication Lifecycle

### 3.1 Connection & Handshake Negotiation
1. Node `IPCClient` establishes TCP connection to `127.0.0.1:8765`.
2. The very first message MUST be `ipc.handshake` with protocol version `"1.0"`.
3. If any message other than `ipc.handshake` is received first, Python Core returns `HANDSHAKE_REQUIRED` error and terminates the socket.
4. Python Core verifies protocol version compatibility and responds with `HandshakeResponse` containing a unique `session_id`.
5. Upon successful handshake, Node Gateway transitions from `CONNECTING` to `CONNECTED`, resets reconnect counters, and starts periodic heartbeat timers.

### 3.2 Bidirectional Request / Response Flow
1. Client sends a serialized `JarvisRequest` frame containing a unique `id`.
2. Client registers the pending request in an in-memory correlation map with an associated timeout timer.
3. Python `IPCServer` reads the frame, validates schema conformance, checks concurrency limits, and hands execution to `IPCRouter`.
4. `IPCRouter` dispatches to the registered handler (or returns `METHOD_NOT_FOUND`).
5. Exceptions in handlers are caught, scrubbed of sensitive secrets (tokens, keys, passwords), and returned as structured `ProtocolError` objects.
6. The resulting `JarvisResponse` is framed and sent back to the TCP socket.
7. Node `IPCClient` correlates the response by `id`, clears the timeout timer, and resolves the caller's Promise.

### 3.3 Real-Time Event Broadcasting
1. Subsystems in Python Core (Agents, Memory, OS Automation, Audio, Vision) emit events to the internal `AsyncEventBus`.
2. `IPCServer` subscribes to the event bus and broadcasts each `JarvisEvent` to all connected clients over TCP.
3. Node `IPCClient` receives event frames and invokes registered `onEvent` listeners.
4. Node Gateway broadcasts the event to all active client WebSocket connections.

### 3.4 Disconnection & Fault Recovery
1. If the connection drops unexpectedly, Node Gateway transitions to `DEGRADED`.
2. All in-flight requests are immediately rejected with `CONNECTION_CLOSED` errors.
3. The client enters `RECONNECTING` and schedules reconnection attempts using exponential backoff with full jitter.
4. Node Gateway health endpoint `/health` reports `degraded` when Python Core is disconnected and resumes `healthy` immediately upon reconnection.

---

## 4. Security & Safety Guarantees

* **Zero External Dependencies:** Built entirely with Python's standard `asyncio` and Node's standard `node:net`.
* **Zero Arbitrary Execution:** No `eval()`, `exec()`, `os.system()`, or `shell=True`.
* **Loopback Enforcement:** Server and client validation forbids binding to non-loopback network interfaces.
* **Secret Scrubbing:** Router error handling scrubs sensitive keywords (`password`, `token`, `key`, `secret`) to prevent credential leakage in error responses.
* **Schema Validation:** Strictly typed validation in both runtimes (Pydantic v2 in Python, Zod in TypeScript).

---

## 5. Verification Metrics
- 32 new unit and integration tests in Python (`tests/python/ipc/`).
- 7 new unit and integration tests in Node (`services/node-gateway/src/__tests__/ipc.test.ts`).
- 420 total monorepo automated tests passing with 0 regressions.
