"""Talk tools for Zendesk MCP Server."""

import json

from mcp.server.fastmcp import FastMCP

from zendesk_mcp.zendesk_client import ZendeskClient


def register_talk_tools(mcp: FastMCP, client: ZendeskClient, enable_write_tools: bool = False) -> None:
    """Register talk-related tools with the MCP server."""

    @mcp.tool()
    async def get_talk_stats() -> str:
        """Get Zendesk Talk statistics."""
        try:
            result = await client.get_talk_stats()
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting Talk stats: {e}"
