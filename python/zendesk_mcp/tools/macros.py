"""Macro tools for Zendesk MCP Server."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from zendesk_mcp.zendesk_client import ZendeskClient


def register_macros_tools(mcp: FastMCP, client: ZendeskClient) -> None:
    """Register macro-related tools with the MCP server."""

    @mcp.tool()
    async def list_macros(
        page: int | None = None,
        per_page: int | None = None,
    ) -> str:
        """List macros in Zendesk.

        Args:
            page: Page number for pagination
            per_page: Number of macros per page (max 100)
        """
        try:
            params = {"page": page, "per_page": per_page}
            result = await client.list_macros(params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing macros: {e}"

    @mcp.tool()
    async def get_macro(id: int) -> str:
        """Get a specific macro by ID.

        Args:
            id: Macro ID
        """
        try:
            result = await client.get_macro(id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting macro: {e}"

    @mcp.tool()
    async def create_macro(
        title: str,
        actions: list[dict[str, Any]],
        description: str | None = None,
    ) -> str:
        """Create a new macro.

        Args:
            title: Macro title
            actions: Actions to perform when macro is applied. Each action has 'field' and 'value' keys.
            description: Macro description
        """
        try:
            macro_data: dict[str, Any] = {"title": title, "actions": actions}
            if description is not None:
                macro_data["description"] = description

            result = await client.create_macro(macro_data)
            return f"Macro created successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error creating macro: {e}"

    @mcp.tool()
    async def update_macro(
        id: int,
        title: str | None = None,
        description: str | None = None,
        actions: list[dict[str, Any]] | None = None,
    ) -> str:
        """Update an existing macro.

        Args:
            id: Macro ID to update
            title: Updated macro title
            description: Updated macro description
            actions: Updated actions
        """
        try:
            macro_data: dict[str, Any] = {}
            if title is not None:
                macro_data["title"] = title
            if description is not None:
                macro_data["description"] = description
            if actions is not None:
                macro_data["actions"] = actions

            result = await client.update_macro(id, macro_data)
            return f"Macro updated successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error updating macro: {e}"

    @mcp.tool()
    async def delete_macro(id: int) -> str:
        """Delete a macro.

        Args:
            id: Macro ID to delete
        """
        try:
            await client.delete_macro(id)
            return f"Macro {id} deleted successfully!"
        except Exception as e:
            return f"Error deleting macro: {e}"
