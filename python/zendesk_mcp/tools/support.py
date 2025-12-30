"""Support tools for Zendesk MCP Server."""

from mcp.server import Server

from zendesk_mcp.zendesk_client import ZendeskClient


def register_support_tools(server: Server, client: ZendeskClient) -> None:
    """Register support-related tools with the MCP server."""

    @server.tool()
    async def support_info() -> str:
        """Get information about Zendesk Support configuration.

        This is a placeholder for future implementation.
        """
        return (
            "Zendesk Support information would be displayed here. "
            "This is a placeholder for future implementation."
        )
