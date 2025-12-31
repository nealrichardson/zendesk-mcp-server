"""Search tools for Zendesk MCP Server."""

import json

from mcp.server.fastmcp import FastMCP

from zendesk_mcp.zendesk_client import ZendeskClient


def register_search_tools(mcp: FastMCP, client: ZendeskClient, enable_write_tools: bool = False) -> None:
    """Register search-related tools with the MCP server."""

    @mcp.tool()
    async def search(
        query: str,
        sort_by: str | None = None,
        sort_order: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> str:
        """Search across Zendesk data.

        Args:
            query: Search query string
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            page: Page number for pagination
            per_page: Number of results per page (max 100)
        """
        try:
            params = {
                "sort_by": sort_by,
                "sort_order": sort_order,
                "page": page,
                "per_page": per_page,
            }
            result = await client.search(query, params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error searching: {e}"
