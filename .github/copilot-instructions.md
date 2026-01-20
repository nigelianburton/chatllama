
ChatLlama is a Python + Qt chat front end for local LLMs, built to use the lightweight llama-server nightly located in C:\Llama. The app is a three-column UI (Settings, Chat, Cards) focused on fast local iteration without LM Studio. It supports multimodal prompts with drag-and-drop image attachments, and the chat layer parses tool requests and presents tool calls/results in the conversation.

The differentiator is the cards concept and MCP integration: cards are writable objects where the LLM can render outputs (first card is SVG, with more cards planned). ChatLlama includes a built-in MCP server so internal tools (like the SVG card) can be advertised to the model, while also supporting external MCP tools and serving as an HTTP stateful MCP server for other clients to call. The target audience for now is the author, with the immediate goal of stabilizing this workflow over the next 24 hours.

Paths and defaults
- Default settings folder (dev): D:\_GITN\chatllama\llama_simple
- Work settings folder: C:\llama_simple
- Home settings folder: T:\llama_simple
- Logs are written to settings_folder\logs
- llama-server binary: C:\Llama\llama-server.exe
- llama-server port: 8014
- Models base folder: D:\LLM Models
- Default model folder: D:\LLM Models\mradermacher\Qwen3-VL-8B-Instruct-abliterated-v2.0-GGUF
- Default model file: D:\LLM Models\mradermacher\Qwen3-VL-8B-Instruct-abliterated-v2.0-GGUF\Qwen3-VL-8B-Instruct-abliterated-v2.0.Q4_K_S.gguf
- Default mmproj: D:\LLM Models\mradermacher\Qwen3-VL-8B-Instruct-abliterated-v2.0-GGUF\Qwen3-VL-8B-Instruct-abliterated-v2.0.mmproj-f16.gguf

SIMPLE key files overview
- SIMPLE/chat_llama.py: main Qt window, splitters, toolbars, wiring
- SIMPLE/column_settings.py: Settings column UI, model discovery callback, settings file creation
- SIMPLE/column_chat.py: Chat column UI, message widgets, attachments bar, model-ready state
- SIMPLE/column_cards.py: Cards column container and layout
- SIMPLE/cards/svg_card.py: SVG card widget with aspect ratio handling
- SIMPLE/mcp_internal_server.py: FastMCP server for SVG card tools
- SIMPLE/llamacpp-server.py: llama-server status, model discovery, model state callbacks
- SIMPLE/logger.py: logging to console and settings_folder\logs
- SIMPLE/utilities.py: log_screenshot helper
- SIMPLE/constants.py: paths and default model settings
- testers/svg_mcp_tester.py: MCP client test for SVG cards

