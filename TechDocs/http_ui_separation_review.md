# UI Separation for HTTP/SSE Client — Implications & Task Review

## Goal
Split the app into a Qt client that communicates over HTTP/SSE with a backend server, while keeping existing Qt widgets in D:\_GITN\chatllama\UI. A new UI\pepper_qt._layout.py will own Qt layout/initialization. A new root entry point pepper_qt.py (copy of PEPPER.py) must keep identical CLI arguments but must not import Qt directly and should delegate any Qt-dependent work to pepper_qt._layout.py.

---

## Architectural Implications

### 1) Process Boundary
- Now: Single process (UI + engine + model runtime).
- Target: Two processes:
  - Client (Qt): UI, user input, rendering, cards.
  - Server (HTTP/SSE): Model runtime, MCPs, tool execution, logging, persistence.
- Implication: Move engine-side responsibilities behind HTTP APIs.

### 2) State & Lifecycle
- Model loading, chat sessions, tool state, and logging move to server.
- Client becomes stateless except for UI state (pane sizes, last view).
- Introduce session IDs and reconnect logic in client.

### 3) Streaming (SSE)
- Chat tokens, tool-call events, and card updates must stream via SSE.
- Need a consistent event schema and ordering guarantees.

### 4) File & Asset Handling
- Server controls logs/screenshots and exposes them via HTTP (or returns URLs).
- Client should not read local server paths.

---

## Required Files & Responsibilities

### New/Modified Files
1) pepper_qt.py (root)
   - CLI entry point with identical args to PEPPER.py.
   - No Qt imports.
   - Starts or connects to server and then calls layout initializer (in pepper_qt._layout.py).

2) UI\pepper_qt._layout.py
   - Contains Qt imports and all UI setup.
   - Accepts a client/service interface that speaks HTTP/SSE.

3) Server app (new entry point, e.g. pepper_server.py)
   - Hosts HTTP endpoints and SSE stream.
   - Owns model runtime, MCP, logging, and tool execution.

---

## Core Tasks

### A) Define HTTP/SSE Contract
- HTTP endpoints
  - POST /sessions → create session
  - POST /sessions/{id}/messages → submit user message
  - POST /sessions/{id}/tools → tool request/ack
  - GET /sessions/{id}/history → pull transcript
  - GET /sessions/{id}/cards → list cards and metadata
- SSE stream
  - GET /sessions/{id}/events
  - Events: token, tool_call, tool_result, card_update, log, error

### B) Client-Side Adapters
- Create a small client library (requests + SSE).
- Map server events to existing UI widgets:
  - Chat column updates
  - Cards column updates
  - Status bar / toasts

### C) Move Engine Responsibilities to Server
- Engine/ logic moves behind HTTP API.
- MCP hosting remains server-side.
- Logging, screenshot capture, and model management stay on server.

### D) Implement pepper_qt._layout.py
- Reuse existing UI components in UI/.
- Replace direct engine calls with client calls.
- Ensure UI doesn’t block on network (async or worker threads).

### E) pepper_qt.py Entry
- Parses CLI args (same as PEPPER.py).
- Starts server or connects to existing server.
- Calls pepper_qt._layout.build_ui(client, args) (example).

---

## Dependency & Build Impacts
- Client now depends on an HTTP/SSE client library.
- Server may need FastAPI/Quart or similar.
- Ensure clear separation in packaging and deployment.

---

## Migration Plan (High-Level)
1) Baseline extraction: copy PEPPER.py → pepper_qt.py
2) Introduce pepper_qt._layout.py and move Qt layout code there.
3) Create HTTP client layer used by UI.
4) Create server entry point and expose minimal endpoints.
5) Wire chat flow end-to-end (message → SSE tokens).
6) Wire cards flow (card events → UI cards).
7) Gradually migrate tool and MCP calls.

---

## Risks & Mitigations
- Latency & streaming reliability: Use SSE with heartbeat pings.
- UI responsiveness: enforce async network calls.
- Compatibility: keep CLI args identical in pepper_qt.py.
- Single-instance behavior: must be implemented on client side.

---

## Acceptance Criteria
- pepper_qt.py launches and accepts same arguments as PEPPER.py.
- No Qt imports in pepper_qt.py.
- UI remains identical in functionality.
- Client can connect to server and stream chat output via SSE.
