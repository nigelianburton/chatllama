from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable


class ModelController:
    def __init__(self, logger) -> None:
        self._logger = logger
        self._module = None
        self._load_module()

    def _load_module(self) -> None:
        module_path = Path(__file__).resolve().parents[1] / "Engine" / "manager_models.py"
        spec = importlib.util.spec_from_file_location("manager_models", module_path)
        if spec is None or spec.loader is None:
            self._logger.error("Failed to load llamacpp-server module")
            return
        import sys
        module = sys.modules.get(spec.name)
        if module is None:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        self._module = module

    def register_callbacks(
        self,
        on_models_discovered: Callable[[list, object], None],
        on_model_state: Callable[[str, object], None],
        on_cache_warm_state: Callable[[str], None] | None = None,
    ) -> bool:
        if self._module is None:
            return False
        try:
            self._module.register_models_callback(on_models_discovered)
            self._module.register_model_state_callback(on_model_state)
            if on_cache_warm_state is not None and hasattr(self._module, "register_cache_warm_callback"):
                self._module.register_cache_warm_callback(on_cache_warm_state)
            return True
        except Exception as exc:
            self._logger.exception("Failed to register model callbacks: %s", exc)
            return False

    def load_model(self, model_ref: str) -> None:
        if self._module is None:
            raise RuntimeError("Model module not loaded")
        self._module.load_model(model_ref)
