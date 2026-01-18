import logging
from chatllama_subpanel_llmsettings import LlmSettingsPanel

logger = logging.getLogger(__name__)


class ChatLlamaCpp:
    """Handler for local llama.cpp models, delegating to the main window."""

    def __init__(self, window) -> None:
        self.window = window

    @property
    def panel(self) -> LlmSettingsPanel:
        return self.window._settings_panel.cpp_panel  # type: ignore[attr-defined]

    def populate_models_with_capabilities(self) -> None:
        """Use window helper to discover models and annotate capabilities."""
        self.window._populate_models_with_capabilities()

    def load_model(self, model_path: str) -> None:
        self.window._load_model(model_path)

    def on_selection_changed(self, index: int) -> None:
        self.window._on_model_selection_changed(index)

    def set_status(self, message: str) -> None:
        if self.panel:
            self.panel.set_status(message)
