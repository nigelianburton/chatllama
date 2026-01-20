# ChatLlama

🤖 **Lightweight local LLM chat interface with MCP agent support**

Built with PyQt6, llama-cpp-python, and fastmcp for standalone operation without LM Studio dependency.

## ✨ Features

- 🚀 **Standalone operation** - No LM Studio required (uses llama.cpp backend directly)
- 🤖 **Multi-model support** - Automatic discovery from nested author folders
- 👁️ **Vision models** - Qwen3-VL series with image understanding
- 🛠️ **MCP agent tools** - Model Context Protocol integration via fastmcp
- ⚡ **GPU acceleration** - CUDA support with configurable offloading
- 📊 **Smart caching** - Model capability detection (vision, tools, context, VRAM)
- 🎛️ **CLI automation** - Command-line mode for testing and batch processing
- 💬 **Streaming responses** - Real-time token-by-token display
- 🎨 **Modern UI** - Collapsible panels, keyboard shortcuts, status indicators

## 🚀 Quick Start

### 1. Installation

```bash
# Create conda environment
conda create -n chatllama python=3.11.14
conda activate chatllama

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy the template and customize paths:
```bash
cp config/settings.yml.template config/settings.yml
```

Edit `config/settings.yml`:
```yaml
llama_cpp_path: "C:\\Users\\YOUR_USERNAME\\.lmstudio\\extensions\\backends\\..."
models_dir: "D:\\LLM Models"
default_model: "mradermacher\\Huihui-LFM2-2.6B-Exp-abliterated-GGUF"
```

### 3. Run

```bash
# Interactive mode
python chatllama.py

# Or directly
python src/chat.py

# List available models
python src/chat.py --list-models

# Use specific model
python src/chat.py --model "mradermacher\\gemma-3-27b-it-abliterated-GGUF"

# Automation mode (testing)
python src/chat.py --input-file tests/test_input.txt
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [MCP Integration Guide](docs/MCP_INTEGRATION.md) | Complete MCP protocol implementation |
| [Command-Line Arguments](docs/COMMANDLINE_ARGS.md) | CLI usage and options |
| [Automation Mode](docs/AUTOMATION_MODE.md) | Batch testing with input files |
| [Model Capabilities](docs/CAPABILITIES_CACHING.md) | Capability detection and caching |
| [MCP Tools Reference](docs/MCP_TOOLS_QUICK_REF.md) | Quick tool reference |
| [Tool Detection](docs/TOOL_DETECTION.md) | How tool/vision detection works |

## 🏗️ Project Structure

```
chatllama/
├── src/                      # Source code
│   ├── chat.py              # Main application
│   └── __init__.py
├── config/                   # Configuration
│   ├── settings.yml.template # Settings template
│   └── mcp.json             # MCP server definitions
├── test_mcp/                # Test MCP servers
│   ├── fashion_stdio.py     # Stateless fashion advisor
│   └── fashion_server/      # Stateful fashion curator
├── docs/                    # Documentation
├── tests/                   # Test files
├── scripts/                 # Utility scripts
├── logs/                    # Session logs (gitignored)
├── .github/
│   └── copilot-instructions.md
├── chatllama.py            # Launcher script
├── requirements.txt        # Python dependencies
└── README.md
```

## 🤖 MCP Integration

ChatLlama uses the Model Context Protocol (MCP) for agent capabilities:

### Built-in Test Servers

**fashion-curator** (Stateful)
- User profile management
- Personalized recommendations
- Save favorite looks
- Statistics tracking

**fashion-advisor** (Stateless)
- Random fashion looks
- Filter by vibe
- Quick lookups

### Adding Custom MCP Servers

Edit `config/mcp.json`:
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["path/to/server.py"],
      "type": "stdio"
    }
  }
}
```

## 🎯 Model Support

### Supported Architectures
- ✅ Llama, Llama 2, Llama 3
- ✅ Qwen, Qwen2, Qwen3 (including VL vision models)
- ✅ Gemma, Gemma 2, Gemma 3
- ✅ Mistral, Mixtral
- ✅ Phi models
- ✅ Many more via llama.cpp

### Model Discovery
Models are automatically discovered from:
```
D:\LLM Models\
├── author1\
│   └── model-name-GGUF\
│       ├── model.Q4_K_S.gguf
│       └── model.mmproj-f16.gguf (vision)
└── author2\
    └── another-model-GGUF\
        └── model.Q4_K_M.gguf
```

### Capability Detection
On first run, models are scanned for:
- 👁️ **Vision support** - Image understanding capability
- 🛠️ **Tool support** - Function calling capability
- 📏 **Context length** - Max tokens supported
- 💾 **VRAM usage** - GPU memory requirements

Results are cached in `config/settings.yml` for instant startup.

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Ctrl+Enter` | New line in prompt |
| Toolbar `☰` | Toggle settings panel |

## 🔧 Configuration Options

See `config/settings.yml.template` for all options:

- **Backend paths** - llama.cpp location, model directory
- **Server settings** - Port, GPU layers
- **MCP integration** - Enable/disable, server command
- **Tool system** - Preamble template, integration toggle
- **Model cache** - Automatic capability storage

## 🐛 Troubleshooting

### Model won't load
- Check `logs/session_*.log` for details
- Verify model path in settings
- Try with smaller model first
- Check GPU memory availability

### Vision model fails
- App automatically falls back to llama-server
- Ensure llama-server.exe is available in backend path
- Check port 8000 isn't blocked

### MCP tools not appearing
- Verify `tool_integration_enabled: true` in settings
- Check MCP server is running: look for process in logs
- Review `chatllama.log` for connection errors

## 📝 Development

### Running Tests
```bash
# Test capabilities cache
python tests/test_capabilities_cache.py

# Test automation mode
python src/chat.py --input-file tests/test_input.txt
```

### Code Style
- Type hints on all functions
- Logging at DEBUG/INFO/ERROR levels
- Qt signals/slots for async operations
- Worker threads for long operations
- PEP 8 compliance

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Follow existing code style
4. Add tests for new features
5. Update documentation
6. Submit a pull request

## 📜 License

MIT License - See LICENSE file for details

## 🙏 Credits

- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) - Python bindings for llama.cpp
- [FastMCP](https://github.com/jlowin/fastmcp) - Fast Model Context Protocol implementation
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - Python Qt bindings
- [LM Studio](https://lmstudio.ai/) - llama.cpp backend provider

## 🔗 Resources

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [GGUF Format](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md)
- [llama.cpp](https://github.com/ggerganov/llama.cpp)

---

**Made with ❤️ for the local LLM community**


