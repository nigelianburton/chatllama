import logging
from chatllama_subpanel_llmsettings import LlmSettingsPanel

logger = logging.getLogger(__name__)


class ChatLlamaLmStudio:
    """Handler for LM Studio-backed models, delegating to the main window."""

    def __init__(self, window) -> None:
        self.window = window

    @property
    def panel(self) -> LlmSettingsPanel:
        return self.window._settings_panel.lmstudio_panel  # type: ignore[attr-defined]

    def populate_models_with_capabilities(self) -> None:
        self.window._load_lm_studio_models()

    def load_model(self, model_name: str) -> None:
        self.window._load_lm_studio_model(model_name)

    def on_selection_changed(self, index: int) -> None:
        self.window._on_lmstudio_selection_changed(index)

    def set_status(self, message: str) -> None:
        if self.panel:
            self.panel.set_status(message)
