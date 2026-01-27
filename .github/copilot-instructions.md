**Overview:** ChatLlama is a Python + Qt desktop front end for local LLMs, built around llama-server (C:\Llama) with a three-column UI (Settings, Chat, Cards) and a cards-first workflow.

**Environment mandate:** Always run commands inside the `chatllama2` conda environment (`conda activate chatllama2`) before executing Python or scripts.

Automation and tooling
- The chat layer parses tool requests and surfaces tool calls/results in the conversation.
- Internal MCPs are loaded from MCP_Internal/mcp_*.py and share a single FastMCP HTTP server.
- Internal MCP tools are prefixed (e.g., internal.mcp_card_svg.CreateCard).
- Autorun uses JSON input with explicit message boundaries; avoid silent fallbacks during development.
	- Single-instance behavior: if ChatLlama is already running, new launches forward the args (including autorun) to the existing instance and then exit.
	- Run autorun via the CLI: PEPPER.py --autorun <path-to-autorun-json>.
	- Autorun JSON is an array of messages; each message can include text and optional images.
	Example:
	{
		"messages": [
			{"text": "...", "images": ["D:/path/to/image.png"]}
		]
	}
	- SVG card autoruns can reference bundled assets with the resource: scheme (e.g., resource:josie.png).
	- Autorun completes only after any screenshot description finishes; do not assume immediate exit.

Tools guidance (OpenAI-style compatibility)
- Always persist assistant `tool_calls` metadata in the message history before executing tools.
- Tool result messages should include `tool_call_id` and `name` fields so results map to the correct call.
- If the upstream model provides tool-call IDs, propagate them instead of inventing new ones.
- Avoid tool loops by adding explicit stop instructions (e.g., after `DrawCard` succeeds, reply with a brief confirmation and do not call it again unless the user requests changes).
- Ensure tool result payloads are JSON-serializable; avoid silent fallbacks that hide tool errors.

File paths and URI conventions
- Prefer absolute Windows paths for local files (e.g., D:\_GITN\chatllama\pepper_settings\logs\session_*.png).
- For JSON and Markdown, forward slashes are acceptable and recommended (e.g., D:/path/to/image.png) to avoid escaping backslashes.
- For SVG images rendered in cards, use resource:filename to refer to assets bundled in the app (e.g., resource:josie.png).

Paths and defaults
- Default settings folder (dev): D:\_GITN\chatllama\pepper_settings
- Work settings folder: C:\pepper_settings
- Home settings folder: T:\pepper_settings
- Logs are written to settings_folder\logs
- llama-server binary: C:\Llama\llama-server.exe
- llama-server port: 8014
- Models base folder: D:\LLM Models
- Default model folder: D:\LLM Models\mradermacher\Qwen3-VL-8B-Instruct-abliterated-v2.0-GGUF
- Default model file: D:\LLM Models\mradermacher\Qwen3-VL-8B-Instruct-abliterated-v2.0-GGUF\Qwen3-VL-8B-Instruct-abliterated-v2.0.Q4_K_S.gguf
- Default mmproj: D:\LLM Models\mradermacher\Qwen3-VL-8B-Instruct-abliterated-v2.0-GGUF\Qwen3-VL-8B-Instruct-abliterated-v2.0.mmproj-f16.gguf

Development preference
- Avoid fallbacks that mask errors during development. If a dependency fails (e.g., llama-server), surface the failure rather than silently degrading.

File organization
- PEPPER.py: main Qt window, splitters, toolbars, wiring
- Engine/: runtime logic (models, MCP servers, chat manager, logging utilities)
- UI/: Qt widgets for Settings, Chat, Cards, and subpanels
- MCP_Internal/: internal MCPs (mcp_*.py) + shared card widgets/handlers
- Tools/: tool protocol adapters, registry, executor, MCP client manager
- autoruns/: autorun JSON inputs
- scripts/, testers/, tests/: scripts and validation harnesses
- pepper_settings/: local settings, caches, and logs

SIMPLE key files overview
- PEPPER.py: main Qt window, splitters, toolbars, wiring
- UI/column_settings.py: Settings column UI, model discovery callback, settings file creation
- UI/column_chat.py: Chat column UI, message widgets, attachments bar, model-ready state
- UI/column_cards.py: Cards column container and layout
- MCP_Internal/card_svg.py: SVG card widget + tool registration
- MCP_Internal/card_svg_handler.py: SVG validation/parsing + instructions
- MCP_Internal/card_textviewer_handler.py: text viewer validation + SVG generation
- MCP_Internal/mcp_card_svg.py: built-in SVG MCP entrypoint
- MCP_Internal/mcp_card_textviewer.py: built-in text viewer MCP entrypoint
- Engine/mcp_internal_server.py: FastMCP server + mcp_*.py loader
- Engine/manager_models.py: llama-server status, model discovery, model state callbacks
- Engine/logger.py: logging to console and settings_folder\logs
- Engine/utilities.py: log_screenshot helper
- constants.py: paths and default model settings
- testers/svg_mcp_tester.py: MCP client test for SVG cards

Known minor issues
- Chat input box auto-resize beyond ~3 lines is not working; QTextEdit remains at minimum height and shows a scrollbar instead.

Future Plans
- Router mode can keep multiple models loaded concurrently (feature), but on 16GB GPUs this can exhaust VRAM and spill layers to system RAM, causing major slowdowns.
- Add a Settings-pane control to regulate concurrent model residency (e.g., max loaded models or VRAM budget guardrail).
- Capture per-model VRAM usage (dependent on context size and GPU offload) and store with model metadata in settings to predict whether a new load will exceed GPU capacity.
- Add explicit GPU/CPU layer split controls (or presets) so users can balance VRAM vs RAM usage across models.
- Multi-user router mode can benefit from multiple resident models; for single-user, keep at least one fast small model for tasks like embeddings or quick utility calls.

Recent progress
- MCP integration now supports both stdio and HTTP servers simultaneously (fashion_stdio 2026 + fashion_http 1960s), and the LLM can route to either.

Logs
- Location: settings_folder\logs (dev default: D:\_GITN\chatllama\pepper_settings\logs)
- Each run creates a timestamped subfolder named YYYY-MM-DD_HH-MM-SS
- Log file: session.log (per-session)
- Interaction log: interaction.json (per-session summary)
- Autorun artifacts (when enabled): screencap.png, card1.png..cardN.png, description.txt

Todo
- If the LLM is flagged as being able to view images, MCP responses should include a screen capture of the resulting card.
- Images consume context, so message history should not retain these temporary images; only the latest should be included.

