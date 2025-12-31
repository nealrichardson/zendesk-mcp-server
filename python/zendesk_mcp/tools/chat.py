"""Chat tools for Zendesk MCP Server."""

import json

from mcp.server.fastmcp import FastMCP

from zendesk_mcp.zendesk_client import ZendeskClient


def register_chat_tools(mcp: FastMCP, client: ZendeskClient, enable_write_tools: bool = False) -> None:
    """Register chat-related tools with the MCP server."""

    @mcp.tool()
    async def list_chats(
        page: int | None = None,
        per_page: int | None = None,
    ) -> str:
        """List Zendesk Chat conversations.

        Args:
            page: Page number for pagination
            per_page: Number of chats per page (max 100)
        """
        try:
            params = {"page": page, "per_page": per_page}
            result = await client.list_chats(params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing chats: {e}"
