"""Group tools for Zendesk MCP Server."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from zendesk_mcp.zendesk_client import ZendeskClient


def register_groups_tools(mcp: FastMCP, client: ZendeskClient) -> None:
    """Register group-related tools with the MCP server."""

    @mcp.tool()
    async def list_groups(
        page: int | None = None,
        per_page: int | None = None,
    ) -> str:
        """List agent groups in Zendesk.

        Args:
            page: Page number for pagination
            per_page: Number of groups per page (max 100)
        """
        try:
            params = {"page": page, "per_page": per_page}
            result = await client.list_groups(params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing groups: {e}"

    @mcp.tool()
    async def get_group(id: int) -> str:
        """Get a specific group by ID.

        Args:
            id: Group ID
        """
        try:
            result = await client.get_group(id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting group: {e}"

    @mcp.tool()
    async def create_group(
        name: str,
        description: str | None = None,
    ) -> str:
        """Create a new agent group.

        Args:
            name: Group name
            description: Group description
        """
        try:
            group_data: dict[str, Any] = {"name": name}
            if description is not None:
                group_data["description"] = description

            result = await client.create_group(group_data)
            return f"Group created successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error creating group: {e}"

    @mcp.tool()
    async def update_group(
        id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> str:
        """Update an existing group.

        Args:
            id: Group ID to update
            name: Updated group name
            description: Updated group description
        """
        try:
            group_data: dict[str, Any] = {}
            if name is not None:
                group_data["name"] = name
            if description is not None:
                group_data["description"] = description

            result = await client.update_group(id, group_data)
            return f"Group updated successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error updating group: {e}"

    @mcp.tool()
    async def delete_group(id: int) -> str:
        """Delete a group.

        Args:
            id: Group ID to delete
        """
        try:
            await client.delete_group(id)
            return f"Group {id} deleted successfully!"
        except Exception as e:
            return f"Error deleting group: {e}"
