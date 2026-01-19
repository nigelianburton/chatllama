"""MCP stdio client helper for tool discovery and prompt formatting.

Encapsulates MCP tool fetching, caching, OpenAI conversion, and prompt
construction so chat.py stays lean. Server processes are spawned on-demand
via mcp.client.stdio.stdio_client.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


class McpToolManager:
    """Manage MCP tool discovery and formatting for ChatLlama."""

    def __init__(
        self,
        command: str,
        project_root: Path,
        tool_preamble: str,
        tool_integration_enabled: bool,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.command = command
        self.project_root = project_root
        self.tool_preamble = tool_preamble
        self.tool_integration_enabled = tool_integration_enabled
        self.logger = logger or logging.getLogger(__name__)
        self._tools_cache: Optional[list] = None

    # ---- Public API ----
    def fetch_mcp_tools(self) -> Optional[list]:
        """Fetch tools from MCP server via stdio; returns cached tools if available."""
        if self._tools_cache is not None:
            self.logger.debug("Returning cached MCP tools (%d)", len(self._tools_cache))
            return self._tools_cache

        if not self.tool_integration_enabled:
            self.logger.debug("Tool integration disabled; skipping MCP fetch")
            return None

        tools = self._fetch_via_stdio()
        if tools:
            self._tools_cache = tools
        return tools

    def convert_mcp_tools_to_openai_format(self, mcp_tools: list) -> list:
        """Convert MCP ToolDescription objects/dicts into OpenAI function tool format."""
        if not mcp_tools:
            return []

        openai_tools = []
        for tool in mcp_tools:
            try:
                if isinstance(tool, dict):
                    name = tool.get("name", "")
                    description = tool.get("description", "")
                    input_schema = tool.get("inputSchema", {})
                else:
                    name = getattr(tool, "name", "")
                    description = getattr(tool, "description", "")
                    input_schema = getattr(tool, "inputSchema", {})

                tool_def = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description or "",
                        "parameters": input_schema,
                    },
                }
                openai_tools.append(tool_def)
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.warning("Failed to convert tool %s: %s", tool, exc)

        if openai_tools:
            self.logger.info("Converted %d MCP tools to OpenAI format", len(openai_tools))
        return openai_tools

    def build_tool_prompt(self, tools: list) -> str:
        """Build system prompt section using settings preamble with {tools_json}."""
        if not tools:
            return ""
        tools_json = json.dumps(tools, indent=2)
        prompt = "\n" + self.tool_preamble.replace("{tools_json}", tools_json)
        self.logger.info("Built tool prompt for %d tools", len(tools))
        return prompt

    def merge_builtin_tools(self, tools: Optional[list], builtin_tools: Optional[list]) -> Optional[list]:
        """Merge built-in HTTP MCP tools with fetched tools, avoiding duplicates."""
        if not builtin_tools:
            return tools
        if tools is None:
            tools = []
        existing = {t.get("name") for t in tools if isinstance(t, dict)}
        added = 0
        for bt in builtin_tools:
            if bt.get("name") not in existing:
                tools.append(bt)
                added += 1
        if added:
            self.logger.info("Merged %d built-in MCP tools", added)
        return tools

    # ---- Internal helpers ----
    def _fetch_via_stdio(self) -> Optional[list]:
        """Connect via stdio MCP client, run tools/list, and return ToolDescription list."""
        cmd_parts = self.command.split()

        async def get_tools():
            server_params = StdioServerParameters(
                command=cmd_parts[0],
                args=cmd_parts[1:] if len(cmd_parts) > 1 else [],
                cwd=self.project_root,
            )
            self.logger.info("Connecting to MCP server via stdio: %s", self.command)
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_response = await session.list_tools()
                    self.logger.info("MCP list_tools returned %d tools", len(tools_response.tools))
                    return tools_response.tools

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tools = loop.run_until_complete(get_tools())
            loop.close()
            if not tools:
                self.logger.warning("No tools returned from MCP server")
            return tools
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Failed to fetch MCP tools: %s", exc)
            return None


__all__ = ["McpToolManager"]
