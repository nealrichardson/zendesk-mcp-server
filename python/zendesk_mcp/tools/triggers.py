"""Trigger tools for Zendesk MCP Server."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from zendesk_mcp.zendesk_client import ZendeskClient


def register_triggers_tools(mcp: FastMCP, client: ZendeskClient) -> None:
    """Register trigger-related tools with the MCP server."""

    @mcp.tool()
    async def list_triggers(
        page: int | None = None,
        per_page: int | None = None,
    ) -> str:
        """List triggers in Zendesk.

        Args:
            page: Page number for pagination
            per_page: Number of triggers per page (max 100)
        """
        try:
            params = {"page": page, "per_page": per_page}
            result = await client.list_triggers(params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing triggers: {e}"

    @mcp.tool()
    async def get_trigger(id: int) -> str:
        """Get a specific trigger by ID.

        Args:
            id: Trigger ID
        """
        try:
            result = await client.get_trigger(id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting trigger: {e}"

    @mcp.tool()
    async def create_trigger(
        title: str,
        conditions: dict[str, Any],
        actions: list[dict[str, Any]],
        description: str | None = None,
    ) -> str:
        """Create a new trigger.

        Args:
            title: Trigger title
            conditions: Conditions for the trigger. Object with 'all' and/or 'any' arrays of condition objects.
            actions: Actions to perform when trigger conditions are met
            description: Trigger description
        """
        try:
            trigger_data: dict[str, Any] = {
                "title": title,
                "conditions": conditions,
                "actions": actions,
            }
            if description is not None:
                trigger_data["description"] = description

            result = await client.create_trigger(trigger_data)
            return f"Trigger created successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error creating trigger: {e}"

    @mcp.tool()
    async def update_trigger(
        id: int,
        title: str | None = None,
        description: str | None = None,
        conditions: dict[str, Any] | None = None,
        actions: list[dict[str, Any]] | None = None,
    ) -> str:
        """Update an existing trigger.

        Args:
            id: Trigger ID to update
            title: Updated trigger title
            description: Updated trigger description
            conditions: Updated conditions
            actions: Updated actions
        """
        try:
            trigger_data: dict[str, Any] = {}
            if title is not None:
                trigger_data["title"] = title
            if description is not None:
                trigger_data["description"] = description
            if conditions is not None:
                trigger_data["conditions"] = conditions
            if actions is not None:
                trigger_data["actions"] = actions

            result = await client.update_trigger(id, trigger_data)
            return f"Trigger updated successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error updating trigger: {e}"

    @mcp.tool()
    async def delete_trigger(id: int) -> str:
        """Delete a trigger.

        Args:
            id: Trigger ID to delete
        """
        try:
            await client.delete_trigger(id)
            return f"Trigger {id} deleted successfully!"
        except Exception as e:
            return f"Error deleting trigger: {e}"
