Integration Plan: Task 1 - Shared Model Control API
Objective: Decouple model management from the Qt UI and expose it via a shared HTTP service to support functional parity between the legacy Qt client and the new Reflex web client.

Task 1.1: Create the Control Service
File: Engine/control_service.py

Requirements:

Implement a FastAPI server running on http://127.0.0.1:8001 (to avoid conflict with llama-server on 8014).

Endpoint GET /status: Return a JSON object with model_name and status (Ready, Loading, Fault, Waiting) by wrapping manager_models._get_model_state().

Endpoint GET /models: Return the list of discovered GGUF files by wrapping manager_models.get_discovered_models().

Endpoint POST /load: Accept a model_name JSON payload. Execute manager_models.load_model(name) in a background thread using FastAPI's BackgroundTasks to ensure the API remains responsive during the load.

Task 1.2: Lifecycle Management in PEPPER.py
File: PEPPER.py

Requirements:

In the main() function, launch control_service.py as a background subprocess before initializing the Qt application.

Ensure the subprocess is terminated correctly when the main window is closed.

Task 1.3: Update Reflex BaseState
File: PepperReflex/pepper_reflex/state.py

Requirements:

Add a background task (rx.background_task) that polls http://127.0.0.1:8001/status every 2 seconds.

Update BaseState.model_name and BaseState.model_state based on the API response.

Wire the "Load" button in the Settings view to perform a POST request to the service.