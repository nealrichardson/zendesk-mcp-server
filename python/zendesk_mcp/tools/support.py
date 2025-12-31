"""Support tools for Zendesk MCP Server."""

from mcp.server.fastmcp import FastMCP

from zendesk_mcp.zendesk_client import ZendeskClient


def register_support_tools(mcp: FastMCP, client: ZendeskClient) -> None:
    """Register support-related tools with the MCP server."""

    @mcp.tool()
    async def support_info() -> str:
        """Get information about Zendesk Support configuration.

        This is a placeholder for future implementation.
        """
        return (
            "Zendesk Support information would be displayed here. "
            "This is a placeholder for future implementation."
        )
