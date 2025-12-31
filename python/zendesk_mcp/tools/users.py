"""User tools for Zendesk MCP Server."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from zendesk_mcp.zendesk_client import ZendeskClient


def register_users_tools(mcp: FastMCP, client: ZendeskClient) -> None:
    """Register user-related tools with the MCP server."""

    @mcp.tool()
    async def list_users(
        page: int | None = None,
        per_page: int | None = None,
        role: str | None = None,
    ) -> str:
        """List users in Zendesk.

        Args:
            page: Page number for pagination
            per_page: Number of users per page (max 100)
            role: Filter users by role (end-user, agent, admin)
        """
        try:
            params = {"page": page, "per_page": per_page, "role": role}
            result = await client.list_users(params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing users: {e}"

    @mcp.tool()
    async def get_user(id: int) -> str:
        """Get a specific user by ID.

        Args:
            id: User ID
        """
        try:
            result = await client.get_user(id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting user: {e}"

    @mcp.tool()
    async def create_user(
        name: str,
        email: str,
        role: str | None = None,
        phone: str | None = None,
        organization_id: int | None = None,
        tags: list[str] | None = None,
        notes: str | None = None,
    ) -> str:
        """Create a new user.

        Args:
            name: User's full name
            email: User's email address
            role: User's role (end-user, agent, admin)
            phone: User's phone number
            organization_id: ID of the user's organization
            tags: Tags for the user
            notes: Notes about the user
        """
        try:
            user_data: dict[str, Any] = {"name": name, "email": email}
            if role is not None:
                user_data["role"] = role
            if phone is not None:
                user_data["phone"] = phone
            if organization_id is not None:
                user_data["organization_id"] = organization_id
            if tags is not None:
                user_data["tags"] = tags
            if notes is not None:
                user_data["notes"] = notes

            result = await client.create_user(user_data)
            return f"User created successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error creating user: {e}"

    @mcp.tool()
    async def update_user(
        id: int,
        name: str | None = None,
        email: str | None = None,
        role: str | None = None,
        phone: str | None = None,
        organization_id: int | None = None,
        tags: list[str] | None = None,
        notes: str | None = None,
    ) -> str:
        """Update an existing user.

        Args:
            id: User ID to update
            name: Updated user's name
            email: Updated email address
            role: Updated user's role (end-user, agent, admin)
            phone: Updated phone number
            organization_id: Updated organization ID
            tags: Updated tags for the user
            notes: Updated notes about the user
        """
        try:
            user_data: dict[str, Any] = {}
            if name is not None:
                user_data["name"] = name
            if email is not None:
                user_data["email"] = email
            if role is not None:
                user_data["role"] = role
            if phone is not None:
                user_data["phone"] = phone
            if organization_id is not None:
                user_data["organization_id"] = organization_id
            if tags is not None:
                user_data["tags"] = tags
            if notes is not None:
                user_data["notes"] = notes

            result = await client.update_user(id, user_data)
            return f"User updated successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error updating user: {e}"

    @mcp.tool()
    async def delete_user(id: int) -> str:
        """Delete a user.

        Args:
            id: User ID to delete
        """
        try:
            await client.delete_user(id)
            return f"User {id} deleted successfully!"
        except Exception as e:
            return f"Error deleting user: {e}"
