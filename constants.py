LLAMA_SERVER_PORT = 8014
LLAMA_SERVER_HOST = "127.0.0.1"
LLAMA_SERVER_EXE = r"C:\Llama\llama-server.exe"
GGUF_MODELS_DIR = r"D:\LLM Models"
DEFAULT_MODEL_DIR = r"D:\LLM Models\mradermacher\Qwen3-VL-8B-Instruct-abliterated-v2.0-GGUF"
DEFAULT_MODEL_FILE = r"D:\LLM Models\mradermacher\Qwen3-VL-8B-Instruct-abliterated-v2.0-GGUF\Qwen3-VL-8B-Instruct-abliterated-v2.0.Q4_K_S.gguf"
DEFAULT_MMPROJ_FILE = r"D:\LLM Models\mradermacher\Qwen3-VL-8B-Instruct-abliterated-v2.0-GGUF\Qwen3-VL-8B-Instruct-abliterated-v2.0.mmproj-f16.gguf"
LLAMA_CPP_MODEL_INIT_FILE = "LLAMA_CPP_MODEL_INIT.ini"
PEPPER_SETTINGS_FILE = "PEPPER_SETTINGS.json"
DEFAULT_TOOL_PREAMBLE_GENERAL = "Tools are available for this chat."
DEFAULT_TOOL_PREAMBLE_CARDS = (
	"SVG cards are UI-only. Do NOT output raw SVG in assistant messages. "
	"Always call internal.CreateCard first to get a guid, then call internal.DrawCard "
	"with a full <svg> document sized 480x640 (portrait) or 640x480 (landscape) "
	"ONLY inside the DrawCard tool call arguments. "
	"Never invent guids and never paste SVG in chat content."
)
INTERNAL_MCP_NAME = "internal"
INTERNAL_MCP_HOST = "127.0.0.1"
INTERNAL_MCP_PORT = 6821
AUTORUN_READY_TIMEOUT_SECONDS = 10
AUTORUN_RESPONSE_TIMEOUT_SECONDS = 60
AUTORUN_BUSY_ACK_TIMEOUT_SECONDS = 1
SETTINGS_WORK = r"C:\pepper_settings"
SETTINGS_HOME = r"T:\pepper_settings"
SETTINGS_DEV = r"D:\_GITN\chatllama\pepper_settings"
SHOW_SAMPLE_MESSAGES = False
TOGGLE_ON_COLOR = "#cfe8ff"
TOGGLE_OFF_COLOR = "#f0f0f0"
TOGGLE_DISABLED_COLOR = "#e1e1e1"
HEADER_COLOR_READY = "#b6e3b6"
HEADER_COLOR_LOADING = "#d9d9d9"
HEADER_COLOR_FAULT = "#f5b7b1"
MCP_LABEL_WIDTH = 28
MCP_PORT_INPUT_WIDTH = 32
