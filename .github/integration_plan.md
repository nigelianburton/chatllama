# Integration Plan — Launcher + Pluggable UI (App + UIContracts)

## Objective
Decouple UI implementations from shared services so the UI is replaceable (Qt now, others later) without changing core behavior.

---

## Phase 0 — Baseline & Safety
**Tasks**
- Keep PEPPER.py unchanged as reference.
- Ensure PEPPER_LAUNCHER.py runs with the same CLI args as PEPPER.py plus `--ui`.
- Confirm no Qt imports in PEPPER_LAUNCHER.py.

**Tests**
- Run launcher help:
	`python PEPPER_LAUNCHER.py --help`
- Run Qt UI path:
	`python PEPPER_LAUNCHER.py --ui qt`

---

## Phase 1 — App + UIContracts Scaffolding
**Tasks**
- Create App/ for shared orchestration and state.
- Create UIContracts/ for UI interface definitions (pure Python, no Qt).
- Move shared services into App (single-instance, control service lifecycle, MCP server startup, autorun orchestration).
- Keep UI-specific logic in UI modules; they implement the UIContracts interface.

**Tests**
- Import checks:
	`python -c "import App, UIContracts"`
- Run Qt UI path:
	`python PEPPER_LAUNCHER.py --ui qt`

---

## Phase 2 — Qt Layout Conformance
**Tasks**
- Ensure UI/pepper_qt_layout.py implements UIContracts.
- Replace any shared service logic in UI with App calls.

**Tests**
- Launch and open main window:
	`python PEPPER_LAUNCHER.py --ui qt`

---

## Phase 3 — Move Non-UI Logic Out of UI
**Tasks**
- Identify engine/state logic inside UI modules.
- Relocate state ownership into App services.
- UI becomes pure view + event forwarding.

**Tests**
- Run a normal session and confirm model list, chat, and cards work.
- Optional autorun smoke test:
	`python PEPPER_LAUNCHER.py --autorun D:/_GITN/chatllama/autoruns/autorun_svg_card.json`

---

## Phase 4 — Parity Audit vs PEPPER.py
**Tasks**
- Side-by-side behavior checklist against PEPPER.py.
- Close any gaps in UIContracts or App services.

**Tests**
- Repeat CLI behaviors (model selection, autorun, logs).
- Confirm logs saved to settings folder.

---

## Phase 5 — Ready for Alternate UI
**Tasks**
- Add stub UI/pepper_reflex_layout.py implementing UIContracts.
- Ensure launcher can switch UI with `--ui reflex`.

**Tests**
- `python PEPPER_LAUNCHER.py --ui reflex` (should start without crashing).

---

## Notes
- All tests run inside `conda activate chatllama2`.
- Avoid new network dependencies unless client/server split is explicitly required.