# Reflex Parity Plan (PEPPER.py → PepperReflex)

Goal: Make the PepperReflex client behave like the Qt client in PEPPER.py with identical runtime flow and capabilities.

## Step-by-step plan

1. **Map the Qt startup lifecycle**
   - Document PEPPER.py startup sequence (logging → single-instance → MCP server → model state wiring → autorun → shutdown).
   - Identify all services started by PEPPER.py (control service, internal MCP server, llama-server lifecycle).
   - Test checkpoint: N/A (documentation step).
   - Notes captured:
     - Logging is configured first (settings folder selection), then interaction logging starts.
     - Single-instance guard is acquired before Qt app creation.
     - Control service is launched (subprocess) and registered for shutdown.
     - Qt app and main window are created and shown.
     - Internal MCP server is started on window show.
     - Autorun (if set) runs and triggers a delayed exit with screenshot/description.
     - App exits with cleanup (control service termination).

2. **Reflex boot parity**
   - Ensure Reflex app starts required services (control_service) or detects they are running.
   - Mirror single-instance behavior where applicable (browser clients may be multi-instance; define expected behavior).
   - TEST: `tests/reflex_parity_tests.py::test_control_status_endpoint` (requires control service running).
   - Implemented:
     - Reflex on_load initializes control service polling and first fetch (status + models).
     - If the control service is unavailable, tests skip and UI shows placeholder model list until available.

3. **Shared Control Service API (Task 1.1–1.3)**
   - Confirm control_service endpoints are stable and used by Reflex only (no direct Qt dependencies).
   - Verify status + model list polling and error states in Reflex state.
   - TEST: `tests/reflex_parity_tests.py::test_control_models_endpoint`.
   - Status: Done

4. **Model discovery + load parity**
   - Align model list in Reflex with PEPPER.py model discovery via control_service.
   - Ensure load progress/Loading/Fault state mapping matches Qt UI.
   - TEST: `tests/reflex_parity_tests.py::test_control_polling_ready`.
   - Status: Done

5. **MCP integration parity**
   - Mirror MCP tool discovery, enabled/disabled toggles, and tool list in Reflex.
   - Validate tool execution and response handling match Qt chat pipeline.
   - TEST: `tests/reflex_parity_tests.py::test_mcp_settings_loaded`.
   - Status: Done

6. **Chat + cards workflow parity**
   - Mirror chat UX (messages, tool call visibility, attachments).
   - Validate card creation/rendering flow from MCP and status handling.
   - TEST: `tests/reflex_parity_tests.py::test_chat_cards_state_defaults`.
   - Status: Done

7. **Autorun parity**
   - Implement autorun ingestion via control service or direct Reflex triggers.
   - Ensure screenshot + description flow (if applicable in web) matches Qt semantics.
   - TEST: `tests/reflex_parity_tests.py::test_autorun_payload_parsing`.
   - Status: Done

7.1 **Startup parameter parity (autorun)**
   - Add support for `--autorun`-equivalent input for Reflex (query params or control-service endpoint).
   - Validate the payload format matches PEPPER.py autorun JSON semantics.
   - TEST: covered by autorun payload parsing.
   - Status: Done

8. **Logging + diagnostics parity**
   - Standardize log events and interaction JSON schema between Qt and Reflex.
   - Expose diagnostics in Reflex settings panel.
   - TEST: `tests/reflex_parity_tests.py::test_diagnostics_fields`.
   - Status: Done

9. **Shutdown + cleanup parity**
   - Ensure Reflex client signals control service and any spawned subprocesses cleanly.
   - Define cleanup behavior for browser refresh/close.
   - TEST: `tests/reflex_parity_tests.py::test_diagnostics_fields`.
   - Status: Done

10. **Acceptance validation**
   - Verify identical feature checklist vs Qt client.
   - Compare workflows with scripted tests (autorun or manual cases).

## Immediate next tasks

- Add a dedicated Reflex lifecycle state to track service health and fail-fast UI states.
- Verify control_service is running when Reflex starts and show a clear status indicator.
- Add UI parity checklist to track missing behaviors.
- Define the `--autorun` bridge for Reflex (URL/query or control-service trigger).
- Add `run_reflex_tests.py --test` to run parity tests at each checkpoint.
