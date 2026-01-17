# Test MCP Servers

Three example Model Context Protocol (MCP) servers built with fastmcp for ChatLlama.

## 1. LM Studio Query Server - `lm_studio_server.py` ⭐ NEW

Query LM Studio's API for complex reasoning tasks. Perfect for delegating difficult queries from smaller models to more capable ones.

**Features:**
- OpenAI-compatible API integration
- Query LM Studio's loaded model for enhanced reasoning
- Configurable temperature and max tokens
- Custom system messages for task-specific prompts

**Tools:**
- `query_lm_studio(prompt, system_message?, max_tokens?, temperature?)` - Send a query to LM Studio's model

**Requirements:**
- LM Studio running with a model loaded
- API server enabled (default: http://localhost:1234)

**Run:**
```bash
python lm_studio_server.py
```

**Usage in ChatLlama:**
Set in settings.yml:
```yaml
mcp_server_enabled: true
mcp_server_command: python test_mcp/lm_studio_server.py
tool_integration_enabled: true  # Enable to use tools
```

This gives your local model the ability to delegate complex tasks to LM Studio's more capable model.

---

## 2. Fashion Advisor (Stdio Style) - `fashion_stdio.py`

A stateless MCP server using stdio transport. Perfect for lightweight, simple integrations.

**Features:**
- Returns random cool woman's fashion looks for 2026
- Supports querying by vibe/mood
- Lightweight and stateless

**Tools:**
- `get_fashion_look()` - Get a random fashion look
- `get_all_looks()` - Get all available looks
- `get_look_by_vibe(vibe)` - Get a look matching a specific vibe

**Run:**
```bash
python fashion_stdio.py
```

**Usage in ChatLlama:**
Add to your MCP config to use stdio transport for simple tool calls.

---

## 3. Fashion Curator Server (HTTP Server Style) - `fashion_server/server.py`

A stateful MCP server that runs in its own console. Maintains user profiles and personalized recommendations.

**Features:**
- User profile management with preferred styles
- Personalized recommendations based on user vibes
- Save/favorite looks
- User statistics and recommendation history
- Stateful storage (in-memory for demo, can be persisted)

**Tools:**
- `create_user_profile(user_id, favorite_vibes)` - Create a user profile
- `get_personalized_recommendation(user_id)` - Get a personalized look
- `save_favorite_look(user_id, look_id)` - Save a look
- `get_user_saved_looks(user_id)` - Retrieve saved looks
- `get_user_statistics(user_id)` - Get user stats
- `list_all_looks()` - Get all available looks

**Run:**
```bash
python fashion_server/server.py
```

This will start the server in its own console on the default MCP port.

**Usage in ChatLlama:**
Configure in MCP settings to connect to the running server. The server maintains state across multiple calls.

---

## Fashion Looks Available (2026)

Both servers include the same collection of 8 curated fashion looks:

1. **Neo-Minimalist Edge** - Modern, sophisticated, rebellious
2. **Cyberpunk Glam** - Futuristic, bold, confident
3. **Quiet Luxury Revived** - Effortless, refined, timeless
4. **Cottagecore Meets City** - Romantic, adventurous, nostalgic
5. **Street Maximalist** - Playful, expressive, joyful
6. **Tech-Chic Nomad** - Practical, modern, adventurous
7. **Romantic 70s Redux** - Groovy, feminine, retro
8. **Power Androgyne** - Confident, commanding, modern

---

## Integration with ChatLlama

To integrate these MCPs with ChatLlama:

1. **Stdio MCP** - Add to `chat.py` MCP configuration with stdio transport
2. **Server MCP** - Start the server in a separate terminal, then configure ChatLlama to connect

Both use fastmcp v2.14.3+ and are compatible with the ChatLlama agent system.
