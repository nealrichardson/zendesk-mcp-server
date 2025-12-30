"""Automation tools for Zendesk MCP Server."""

import json
from typing import Any

from mcp.server import Server

from zendesk_mcp.zendesk_client import ZendeskClient


def register_automations_tools(server: Server, client: ZendeskClient) -> None:
    """Register automation-related tools with the MCP server."""

    @server.tool()
    async def list_automations(
        page: int | None = None,
        per_page: int | None = None,
    ) -> str:
        """List automations in Zendesk.

        Args:
            page: Page number for pagination
            per_page: Number of automations per page (max 100)
        """
        try:
            params = {"page": page, "per_page": per_page}
            result = await client.list_automations(params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing automations: {e}"

    @server.tool()
    async def get_automation(id: int) -> str:
        """Get a specific automation by ID.

        Args:
            id: Automation ID
        """
        try:
            result = await client.get_automation(id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting automation: {e}"

    @server.tool()
    async def create_automation(
        title: str,
        conditions: dict[str, Any],
        actions: list[dict[str, Any]],
        description: str | None = None,
    ) -> str:
        """Create a new automation.

        Args:
            title: Automation title
            conditions: Conditions for the automation. Object with 'all' and/or 'any' arrays of condition objects.
            actions: Actions to perform when automation conditions are met
            description: Automation description
        """
        try:
            automation_data: dict[str, Any] = {
                "title": title,
                "conditions": conditions,
                "actions": actions,
            }
            if description is not None:
                automation_data["description"] = description

            result = await client.create_automation(automation_data)
            return f"Automation created successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error creating automation: {e}"

    @server.tool()
    async def update_automation(
        id: int,
        title: str | None = None,
        description: str | None = None,
        conditions: dict[str, Any] | None = None,
        actions: list[dict[str, Any]] | None = None,
    ) -> str:
        """Update an existing automation.

        Args:
            id: Automation ID to update
            title: Updated automation title
            description: Updated automation description
            conditions: Updated conditions
            actions: Updated actions
        """
        try:
            automation_data: dict[str, Any] = {}
            if title is not None:
                automation_data["title"] = title
            if description is not None:
                automation_data["description"] = description
            if conditions is not None:
                automation_data["conditions"] = conditions
            if actions is not None:
                automation_data["actions"] = actions

            result = await client.update_automation(id, automation_data)
            return f"Automation updated successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error updating automation: {e}"

    @server.tool()
    async def delete_automation(id: int) -> str:
        """Delete an automation.

        Args:
            id: Automation ID to delete
        """
        try:
            await client.delete_automation(id)
            return f"Automation {id} deleted successfully!"
        except Exception as e:
            return f"Error deleting automation: {e}"
