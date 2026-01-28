from __future__ import annotations

from Engine.mcp_internal_server import InternalMcpServer


def start_internal_mcp(layout, window, logger) -> InternalMcpServer | None:
    try:
        ui_invoke, ui_create_card, ui_delete_card = layout.get_mcp_hooks(window)
        logger.info("Starting internal MCP server...")
        server = InternalMcpServer(
            ui_invoke=ui_invoke,
            ui_create_card=ui_create_card,
            ui_delete_card=ui_delete_card,
        )
        server.start()
        layout.invoke_ui(window, lambda: layout.refresh_mcp_tools(window))
        return server
    except Exception as exc:
        logger.exception("Failed to start internal MCP server: %s", exc)
        return None
