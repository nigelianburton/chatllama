from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from Engine.logger import configure_logging, get_logger
from Engine import manager_models
from constants import SETTINGS_DEV

LOGGER = get_logger("ControlService")

_manager_started = False
_cached_models: List[manager_models.ModelInfo] = []
_cached_state: tuple[str, str | None] = ("Loading", None)


def _on_models(models: List[manager_models.ModelInfo], loaded: str | None) -> None:
    global _cached_models, _cached_state
    _cached_models = models
    if loaded:
        _cached_state = (_cached_state[0], loaded)


def _on_state(state: str, model_name: str | None) -> None:
    global _cached_state
    _cached_state = (state, model_name)


def _ensure_manager_started() -> None:
    global _manager_started
    if _manager_started:
        return
    _manager_started = True
    manager_models.register_models_callback(_on_models)
    manager_models.register_model_state_callback(_on_state)

app = FastAPI(title="ChatLlama Control Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _serialize_models(models: List[manager_models.ModelInfo]) -> List[Dict[str, Any]]:
    return [asdict(model) for model in models]


def _load_model_background(model_name: str) -> None:
    try:
        manager_models.ensure_running()
        manager_models.load_model(model_name)
    except Exception:
        LOGGER.exception("Model load failed for %s", model_name)
        try:
            manager_models._emit_state("Fault", model_name)
        except Exception:
            LOGGER.exception("Failed to emit Fault state for %s", model_name)


@app.get("/status")
def status() -> Dict[str, Any]:
    _ensure_manager_started()
    state, model_name = _cached_state
    return {
        "model_name": model_name,
        "status": state,
    }


@app.get("/models")
def models() -> Dict[str, Any]:
    _ensure_manager_started()
    return {"models": _serialize_models(_cached_models)}


@app.post("/load")
def load(payload: Dict[str, Any], background_tasks: BackgroundTasks) -> JSONResponse:
    model_name = (payload or {}).get("model_name")
    if not model_name:
        return JSONResponse(
            status_code=400,
            content={"error": "model_name is required"},
        )
    _ensure_manager_started()
    background_tasks.add_task(_load_model_background, model_name)
    return JSONResponse(
        status_code=202,
        content={"accepted": True, "model_name": model_name},
    )


if __name__ == "__main__":
    import uvicorn

    settings = manager_models.load_settings_fresh()
    settings_folder = Path(settings.get("settings_folder", SETTINGS_DEV))
    configure_logging(settings_folder)
    uvicorn.run(app, host="127.0.0.1", port=8001)