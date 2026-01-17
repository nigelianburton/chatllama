# Clean Chat Mode

ChatLlama now defaults to **clean chat mode** for an LM Studio-like experience.

## Problem

When tool integration is enabled, small models (< 8B parameters) tend to **role-play** tool usage instead of actually using tools:

```
User: hi
Model: TOOL: get_fashion_look
Output: Let's find a fabulous 2026 fashion look for you!
TOOL: get_all_looks
Output: Here are some diverse fashion looks available for 2026.
```

The model is **announcing** what it thinks it should do rather than generating natural responses or properly invoking tools.

## Solution

**Default Configuration** (`settings.yml`):
```yaml
tool_integration_enabled: false  # Clean chat mode (like LM Studio)
```

This gives you clean, natural responses:
```
User: Hi What's the capital of France?
Model: The capital of France is Paris. FR

It's one of the world's most famous cities, known for its art, culture, fashion...
```

## When to Enable Tools

Only enable `tool_integration_enabled: true` when:
1. Using models >= 8B parameters with native tool support
2. You need the model to invoke MCP tools
3. The model is trained for function calling (Qwen, Nemotron, etc.)

## LM Studio Integration

For complex tasks beyond your local model's capability:

**1. Start LM Studio API:**
- Load a capable model in LM Studio
- Enable API server (Settings → API → Start Server)
- Default: http://localhost:1234

**2. Enable LM Studio MCP Server:**
```yaml
mcp_server_enabled: true
mcp_server_command: python test_mcp/lm_studio_server.py
tool_integration_enabled: true  # Required for tool calls
```

**3. Usage:**
When enabled, models can invoke `query_lm_studio(prompt)` to delegate complex reasoning to LM Studio's model.

## Comparison

| Mode | Tool Integration | Behavior | Use Case |
|------|-----------------|----------|----------|
| Clean Chat | `false` | Natural responses like LM Studio | General chat, Q&A |
| Tool Mode | `true` | Can invoke MCP tools | Function calling, agent workflows |
| LM Studio Hybrid | `true` + lm_studio_server | Local + remote reasoning | Best of both worlds |

## Implementation

The system prompt changes based on configuration:

**Clean Mode:**
```python
"You are a helpful assistant."  # Simple, no tool announcements
```

**Tool Mode:**
```python
"You are a helpful assistant.

You have access to these tools:
- get_fashion_look(): Get a fashion recommendation
- query_lm_studio(prompt): Query LM Studio for complex tasks
..."
```

Small models without proper tool training should always use clean mode to avoid role-playing behavior.
