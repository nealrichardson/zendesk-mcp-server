"""Organization tools for Zendesk MCP Server."""

import json
from typing import Any

from mcp.server import Server

from zendesk_mcp.zendesk_client import ZendeskClient


def register_organizations_tools(server: Server, client: ZendeskClient) -> None:
    """Register organization-related tools with the MCP server."""

    @server.tool()
    async def list_organizations(
        page: int | None = None,
        per_page: int | None = None,
    ) -> str:
        """List organizations in Zendesk.

        Args:
            page: Page number for pagination
            per_page: Number of organizations per page (max 100)
        """
        try:
            params = {"page": page, "per_page": per_page}
            result = await client.list_organizations(params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing organizations: {e}"

    @server.tool()
    async def get_organization(id: int) -> str:
        """Get a specific organization by ID.

        Args:
            id: Organization ID
        """
        try:
            result = await client.get_organization(id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting organization: {e}"

    @server.tool()
    async def create_organization(
        name: str,
        domain_names: list[str] | None = None,
        details: str | None = None,
        notes: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Create a new organization.

        Args:
            name: Organization name
            domain_names: Domain names for the organization
            details: Details about the organization
            notes: Notes about the organization
            tags: Tags for the organization
        """
        try:
            org_data: dict[str, Any] = {"name": name}
            if domain_names is not None:
                org_data["domain_names"] = domain_names
            if details is not None:
                org_data["details"] = details
            if notes is not None:
                org_data["notes"] = notes
            if tags is not None:
                org_data["tags"] = tags

            result = await client.create_organization(org_data)
            return f"Organization created successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error creating organization: {e}"

    @server.tool()
    async def update_organization(
        id: int,
        name: str | None = None,
        domain_names: list[str] | None = None,
        details: str | None = None,
        notes: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Update an existing organization.

        Args:
            id: Organization ID to update
            name: Updated organization name
            domain_names: Updated domain names
            details: Updated details
            notes: Updated notes
            tags: Updated tags
        """
        try:
            org_data: dict[str, Any] = {}
            if name is not None:
                org_data["name"] = name
            if domain_names is not None:
                org_data["domain_names"] = domain_names
            if details is not None:
                org_data["details"] = details
            if notes is not None:
                org_data["notes"] = notes
            if tags is not None:
                org_data["tags"] = tags

            result = await client.update_organization(id, org_data)
            return f"Organization updated successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error updating organization: {e}"

    @server.tool()
    async def delete_organization(id: int) -> str:
        """Delete an organization.

        Args:
            id: Organization ID to delete
        """
        try:
            await client.delete_organization(id)
            return f"Organization {id} deleted successfully!"
        except Exception as e:
            return f"Error deleting organization: {e}"
