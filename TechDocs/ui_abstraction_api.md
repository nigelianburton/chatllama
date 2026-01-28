# UI abstraction API inventory

Goal: document the implicit API surface between the UI layer and the rest of the app, to support swapping the UI with a different implementation.

## UI -> External dependencies (outside UI)

### UI components and their external calls

- [UI/column_chat.py](UI/column_chat.py)
  - Uses `ChatController` from [App/chat_controller.py](App/chat_controller.py):
    - Methods: `register_callbacks()`, `register_availability_callback()`, `get_last_assistant_message()`, `reload_mcp_tools()`, `get_user_tool_names()`, `send_message()`, `get_tools_advertisement()`
    - Property: `chat_server`
  - Uses `get_logger()` from [Engine/logger.py](Engine/logger.py)
  - Uses constants from [constants.py](constants.py): `SHOW_SAMPLE_MESSAGES`, `TOGGLE_OFF_COLOR`, `TOGGLE_ON_COLOR`

- [UI/column_settings.py](UI/column_settings.py)
  - Uses `SettingsStore` from [App/settings_store.py](App/settings_store.py):
    - Methods: `ensure_settings_file()`, `load_tool_preamble_general()`, `save_tool_preamble_general()`
  - Uses `ModelController` from [App/model_controller.py](App/model_controller.py):
    - Methods: `register_callbacks()`, `load_model()`
  - Uses `MCPController` from [App/mcp_controller.py](App/mcp_controller.py) (passed into MCP panel)
  - Uses constants from [constants.py](constants.py): `DEFAULT_MODEL_FILE`, `DEFAULT_TOOL_PREAMBLE_GENERAL`
  - Uses `get_logger()` from [Engine/logger.py](Engine/logger.py)

- [UI/mcp_settings_panel.py](UI/mcp_settings_panel.py)
  - Uses `SettingsStore` from [App/settings_store.py](App/settings_store.py):
    - Methods: `load_settings_cache()`, `get_mcp_settings()`, `save_mcp_settings()`, `get_built_in_mcp_state()`, `store_built_in_mcp_state()`, `get_mcp_state()`, `store_mcp_state()`
  - Uses `MCPController` from [App/mcp_controller.py](App/mcp_controller.py):
    - Methods: `copy_mcp_file()`, `delete_mcp_file()`, `load_internal_module()`, `get_internal_tool_names()`, `get_internal_preamble()`, `discover_stdio_methods()`, `discover_http_methods()`, `probe_http()`
  - Uses constants from [constants.py](constants.py): `INTERNAL_MCP_HOST`, `INTERNAL_MCP_PORT`

- [UI/pepper_qt_layout.py](UI/pepper_qt_layout.py)
  - Uses `ExitIdleController` from [App/window_controller.py](App/window_controller.py):
    - Methods: `request_exit()`, `capture_screenshot()`
  - Uses `WindowStateController` from [App/window_state_controller.py](App/window_state_controller.py):
    - Methods: `on_model_state_updated()`, `on_model_load_started()`, `on_model_load_finished()`, `on_cache_warm_started()`, `on_cache_warm_finished()`, `on_model_changed()`
  - Uses `StatusMessageController` + `attach_download_callback()` from [App/status_controller.py](App/status_controller.py)
  - Uses `SVGCard` from [MCP_Internal/card_svg.py](MCP_Internal/card_svg.py) (accesses `guid`, calls `deleteLater()`)
  - Uses `get_logger()` from [Engine/logger.py](Engine/logger.py)

- [UI/column_chat_messages.py](UI/column_chat_messages.py)
  - Uses `get_interaction_logger()` from [Engine/interaction_logger.py](Engine/interaction_logger.py):
    - Method used on returned logger: `log()`
  - Uses `get_logger()` from [Engine/logger.py](Engine/logger.py)

- [UI/column_cards.py](UI/column_cards.py)
  - Uses `get_logger()` from [Engine/logger.py](Engine/logger.py)
  - Uses constants from [constants.py](constants.py): `TOGGLE_OFF_COLOR`, `TOGGLE_ON_COLOR`

- [UI/page_main.py](UI/page_main.py)
  - Uses `get_logger()` from [Engine/logger.py](Engine/logger.py)
  - Uses constants from [constants.py](constants.py): `TOGGLE_OFF_COLOR`, `TOGGLE_ON_COLOR`

- [UI/settings_built_in_mcps.py](UI/settings_built_in_mcps.py)
  - Uses constants from [constants.py](constants.py): `TOGGLE_DISABLED_COLOR`, `TOGGLE_OFF_COLOR`, `TOGGLE_ON_COLOR`

- [UI/setting_mcp_item.py](UI/setting_mcp_item.py)
  - Uses constants from [constants.py](constants.py): `MCP_LABEL_WIDTH`, `MCP_PORT_INPUT_WIDTH`, `TOGGLE_DISABLED_COLOR`, `TOGGLE_OFF_COLOR`, `TOGGLE_ON_COLOR`

## External -> UI dependencies (outside UI calling into UI)

### UIContracts layout API (primary UI entrypoint)

The layout contract in [UIContracts/layout.py](UIContracts/layout.py) defines the callable UI surface that the rest of the app expects. Non‑UI code calls these from PEPPER/launcher/autorun/services:

- `create_app(argv)`
- `create_window(exit_idle, log_file, settings_folder)`
- `show_window(window)`
- `register_about_to_quit(app, callback)`
- `capture_screenshot(window)`
- `invoke_ui(window, func)`
- `autorun_stage_message(window, text, image_paths)`
- `autorun_submit_message(window)`
- `register_availability_callback(window, callback)`
- `get_last_assistant_message(window)`
- `schedule_exit(window, delay_ms)`
- `get_mcp_hooks(window)`
- `refresh_mcp_tools(window)`

Callers:
- [PEPPER_LAUNCHER.py](PEPPER_LAUNCHER.py)
- [App/autorun_orchestrator.py](App/autorun_orchestrator.py)
- [App/mcp_service.py](App/mcp_service.py)

### Direct UI usage from non‑UI modules

- [PEPPER.py](PEPPER.py)
  - Constructs `MainPageWidget` from [UI/page_main.py](UI/page_main.py)
  - Reads properties on `MainPageWidget`:
    - `model_title_label`, `status_label`, `progress_bar`
    - `settings_container`, `chat_container`, `cards_container`, `cards_layout`
  - Calls: `set_column_header_color()`
  - Expects `settings_container` signals: `model_state_updated`, `model_load_started`, `model_load_finished`, `cache_warm_started`, `cache_warm_finished`, `model_changed`, `mcp_settings_changed`
  - Expects `chat_container` signal: `model_state_updated`
  - Expects `chat_container` method: `refresh_mcp_tools()`

## Advice for UI independence + intermediate layer

1) **Formalize the UI contract in one place.**
   - Treat [UIContracts/layout.py](UIContracts/layout.py) as the authoritative interface. Add explicit docstrings and type hints for each function (inputs, outputs, threading constraints).
   - Create a small `UIAdapter` protocol in UIContracts to represent the `MainPageWidget` surface expected by non‑UI code (labels, containers, signals).

2) **Push stateful logic behind services.**
   - Keep `ChatController`, `ModelController`, `SettingsStore`, and `MCPController` as UI‑agnostic services.
   - The UI should only call these via adapters/interfaces (e.g., `IChatService`, `IModelService`), which can be mocked or swapped.

3) **Wrap UI signals/events behind a facade.**
   - Introduce a `UIEventBus` or `UIBindings` layer that translates between UI signals and application events.
   - This allows a non‑Qt UI to emit the same events without depending on Qt signal semantics.

4) **Split UI lifecycle from application lifecycle.**
   - Keep app boot/shutdown in PEPPER/launcher; route UI init/teardown through the layout interface only.
   - Use `get_mcp_hooks()` and `invoke_ui()` as the only callbacks into UI threads.

5) **Document threading/ownership explicitly.**
   - Functions like `invoke_ui()` and `autorun_*` are threading‑sensitive. The contract should state what thread they are called from and what thread they must execute on.

6) **Make constants/config injectable.**
   - For colors and UI constants from [constants.py](constants.py), consider a `UITheme` or `UIConfig` object passed into UI constructors, so a new UI can supply equivalent defaults without importing constants directly.

---

If you want, I can add an explicit `UIAdapter` protocol and a thin service layer to route all non‑UI calls through that interface.
