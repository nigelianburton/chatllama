# UI Abstraction Plan — Launcher + Pluggable UI Layouts

## Goal
Abstract the UI from core functionality so it can be swapped (Qt now, Reflex/React later) **without** forcing a client/server split yet. A single launcher (PEPPER_LAUNCHER.py) hosts UI-agnostic services (arg parsing, logging, single-instance, MCP server, autorun, etc.), while UI-specific code lives in layout modules (e.g., UI\pepper_qt_layout.py).

---

## Architectural Implications

### 1) Process Boundary
- Now: Single process (UI + engine + model runtime).
- Target (now): **Single process** with a clean interface between UI and core.
- Future: Optional client/server split **only if needed**.
### 2) Interface Boundary
- UI modules must expose a stable interface (create app/window, show window, capture screenshot, autorun helpers).
- Launcher owns the shared services and calls into the chosen UI module.

### 3) State & Lifecycle
- Core state remains in-process (model loading, MCP, tool registry, logging).
- UI-specific state remains in the layout module (window widgets, visual status).
- Launcher handles startup/shutdown sequencing for all shared services.

### 4) Transport
- No HTTP/SSE required now.
- If/when needed, add a thin transport layer without changing UI contracts.

### 5) File & Asset Handling
- Launcher provides utilities (logging, screenshots) and delegates UI calls as needed.
- UI modules should **not** own global file paths; those come from launcher config.

---

## Required Files & Responsibilities

### New/Modified Files
1) PEPPER_LAUNCHER.py (root)
  - Single entry point for all UI variants.
  - Owns: argument parsing, settings folder selection, logging init, single-instance, MCP server, autorun flow, shutdown.
  - Loads a UI layout module based on `--ui` (default: qt).

2) UI\pepper_qt_layout.py
  - Qt-specific imports and UI setup.
  - Implements the UI interface used by the launcher.
  - Can be replaced later by UI\pepper_reflex_layout.py.

3) PEPPER.py
  - Kept intact for now; serves as the reference behavior for parity.

---

## Core Tasks

### A) Define the UI Interface
- `create_app(argv)` → returns UI application instance
- `create_window(exit_idle, log_file, settings_folder, shared_services)`
- `show_window(window)`
- `capture_screenshot(window)`
- `start_autorun(window, logger, autorun_args)`
- `register_about_to_quit(app, callback)`

### B) Move Shared Services into Launcher
- Single-instance handling.
- Settings folder selection.
- Logging and interaction logger.
- Internal MCP server startup.
- Autorun orchestration.
- Graceful shutdown hooks.

### C) Keep UI-Specific Code in Layouts
- Qt widget creation and wiring.
- Qt signals/slots and visual state updates.
- UI-specific screenshot capture calls (delegating to shared utils as needed).

### D) Parity Check Against PEPPER.py
- Ensure PEPPER_LAUNCHER + pepper_qt_layout reproduces PEPPER.py behavior.
- Keep CLI args identical.
- Keep autorun behavior identical (including screenshot/description).

### E) Optional Future Transport Layer
- Only introduce HTTP/SSE if you need remote or multi-process separation.

---

## Dependency & Build Impacts
- No new network dependencies required.
- Keep PyQt6 and existing engine dependencies unchanged.

---

## Migration Plan (High-Level)
1) PEPPER.py remains reference implementation.
2) PEPPER_LAUNCHER hosts shared services.
3) UI\pepper_qt_layout implements UI interface.
4) Replace direct Qt imports in launcher with layout calls.
5) Add a new layout module when you want a different UI.

---

## Risks & Mitigations
- UI/launcher interface drift: keep a small, explicit interface.
- Hidden UI dependencies in launcher: enforce no-Qt imports in launcher.
- Parity gaps: compare behavior against PEPPER.py after each refactor.

---

## Acceptance Criteria
- PEPPER_LAUNCHER accepts same CLI args as PEPPER.py (plus `--ui`).
- No Qt imports in PEPPER_LAUNCHER.
- pepper_qt_layout reproduces PEPPER.py UI behavior.
- Swapping layout modules requires no launcher changes.
