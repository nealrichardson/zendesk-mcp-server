"""View tools for Zendesk MCP Server."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from zendesk_mcp.zendesk_client import ZendeskClient


def register_views_tools(mcp: FastMCP, client: ZendeskClient, enable_write_tools: bool = False) -> None:
    """Register view-related tools with the MCP server."""

    def write_tool(func):
        """Only register as a tool if write mode is enabled."""
        if enable_write_tools:
            return mcp.tool()(func)
        return func

    @mcp.tool()
    async def list_views(
        page: int | None = None,
        per_page: int | None = None,
    ) -> str:
        """List views in Zendesk.

        Args:
            page: Page number for pagination
            per_page: Number of views per page (max 100)
        """
        try:
            params = {"page": page, "per_page": per_page}
            result = await client.list_views(params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing views: {e}"

    @mcp.tool()
    async def get_view(id: int) -> str:
        """Get a specific view by ID.

        Args:
            id: View ID
        """
        try:
            result = await client.get_view(id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting view: {e}"

    @write_tool
    async def create_view(
        title: str,
        conditions: dict[str, Any],
        description: str | None = None,
    ) -> str:
        """Create a new view.

        Args:
            title: View title
            conditions: Conditions for the view. Object with 'all' and/or 'any' arrays of condition objects.
            description: View description
        """
        try:
            view_data: dict[str, Any] = {"title": title, "conditions": conditions}
            if description is not None:
                view_data["description"] = description

            result = await client.create_view(view_data)
            return f"View created successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error creating view: {e}"

    @write_tool
    async def update_view(
        id: int,
        title: str | None = None,
        description: str | None = None,
        conditions: dict[str, Any] | None = None,
    ) -> str:
        """Update an existing view.

        Args:
            id: View ID to update
            title: Updated view title
            description: Updated view description
            conditions: Updated conditions
        """
        try:
            view_data: dict[str, Any] = {}
            if title is not None:
                view_data["title"] = title
            if description is not None:
                view_data["description"] = description
            if conditions is not None:
                view_data["conditions"] = conditions

            result = await client.update_view(id, view_data)
            return f"View updated successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error updating view: {e}"

    @write_tool
    async def delete_view(id: int) -> str:
        """Delete a view.

        Args:
            id: View ID to delete
        """
        try:
            await client.delete_view(id)
            return f"View {id} deleted successfully!"
        except Exception as e:
            return f"Error deleting view: {e}"
