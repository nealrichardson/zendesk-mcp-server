"""Ticket tools for Zendesk MCP Server."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from zendesk_mcp.zendesk_client import ZendeskClient


def register_tickets_tools(mcp: FastMCP, client: ZendeskClient) -> None:
    """Register ticket-related tools with the MCP server."""

    @mcp.tool()
    async def list_tickets(
        page: int | None = None,
        per_page: int | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> str:
        """List tickets in Zendesk.

        Args:
            page: Page number for pagination
            per_page: Number of tickets per page (max 100)
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
        """
        try:
            params = {
                "page": page,
                "per_page": per_page,
                "sort_by": sort_by,
                "sort_order": sort_order,
            }
            result = await client.list_tickets(params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing tickets: {e}"

    @mcp.tool()
    async def get_ticket(id: int) -> str:
        """Get a specific ticket by ID.

        Args:
            id: Ticket ID
        """
        try:
            result = await client.get_ticket(id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting ticket: {e}"

    @mcp.tool()
    async def create_ticket(
        subject: str,
        comment: str,
        priority: str | None = None,
        status: str | None = None,
        requester_id: int | None = None,
        assignee_id: int | None = None,
        group_id: int | None = None,
        type: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Create a new ticket.

        Args:
            subject: Ticket subject
            comment: Ticket comment/description
            priority: Ticket priority (urgent, high, normal, low)
            status: Ticket status (new, open, pending, hold, solved, closed)
            requester_id: User ID of the requester
            assignee_id: User ID of the assignee
            group_id: Group ID for the ticket
            type: Ticket type (problem, incident, question, task)
            tags: Tags for the ticket
        """
        try:
            ticket_data: dict[str, Any] = {
                "subject": subject,
                "comment": {"body": comment},
            }
            if priority is not None:
                ticket_data["priority"] = priority
            if status is not None:
                ticket_data["status"] = status
            if requester_id is not None:
                ticket_data["requester_id"] = requester_id
            if assignee_id is not None:
                ticket_data["assignee_id"] = assignee_id
            if group_id is not None:
                ticket_data["group_id"] = group_id
            if type is not None:
                ticket_data["type"] = type
            if tags is not None:
                ticket_data["tags"] = tags

            result = await client.create_ticket(ticket_data)
            return f"Ticket created successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error creating ticket: {e}"

    @mcp.tool()
    async def update_ticket(
        id: int,
        subject: str | None = None,
        comment: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        assignee_id: int | None = None,
        group_id: int | None = None,
        type: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Update an existing ticket.

        Args:
            id: Ticket ID to update
            subject: Updated ticket subject
            comment: New comment to add
            priority: Updated ticket priority (urgent, high, normal, low)
            status: Updated ticket status (new, open, pending, hold, solved, closed)
            assignee_id: User ID of the new assignee
            group_id: New group ID for the ticket
            type: Updated ticket type (problem, incident, question, task)
            tags: Updated tags for the ticket
        """
        try:
            ticket_data: dict[str, Any] = {}
            if subject is not None:
                ticket_data["subject"] = subject
            if comment is not None:
                ticket_data["comment"] = {"body": comment}
            if priority is not None:
                ticket_data["priority"] = priority
            if status is not None:
                ticket_data["status"] = status
            if assignee_id is not None:
                ticket_data["assignee_id"] = assignee_id
            if group_id is not None:
                ticket_data["group_id"] = group_id
            if type is not None:
                ticket_data["type"] = type
            if tags is not None:
                ticket_data["tags"] = tags

            result = await client.update_ticket(id, ticket_data)
            return f"Ticket updated successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error updating ticket: {e}"

    @mcp.tool()
    async def delete_ticket(id: int) -> str:
        """Delete a ticket.

        Args:
            id: Ticket ID to delete
        """
        try:
            await client.delete_ticket(id)
            return f"Ticket {id} deleted successfully!"
        except Exception as e:
            return f"Error deleting ticket: {e}"

    @mcp.tool()
    async def list_ticket_comments(
        ticket_id: int,
        sort_order: str | None = None,
        body_format: str = "plain",
        include_metadata: bool = False,
        include_attachment_details: bool = False,
    ) -> str:
        """List all comments on a ticket. Supports filtering to reduce response size.

        Args:
            ticket_id: Ticket ID to get comments from
            sort_order: Sort order for comments (asc = oldest first, desc = newest first)
            body_format: Which body format to return (plain, html, both). Default: plain
            include_metadata: Include metadata.system fields like client info, IP, location. Default: false
            include_attachment_details: Include full attachment details like thumbnails, malware scans. Default: false
        """
        try:
            params = {}
            if sort_order:
                params["sort_order"] = sort_order

            result = await client.list_ticket_comments(ticket_id, params)

            # Filter comments to reduce response size
            if "comments" in result:
                filtered_comments = []
                for comment in result["comments"]:
                    filtered = dict(comment)

                    # Filter body formats
                    if body_format == "plain":
                        filtered.pop("html_body", None)
                        filtered.pop("body", None)
                    elif body_format == "html":
                        filtered.pop("plain_body", None)
                        filtered.pop("body", None)

                    # Filter metadata
                    if not include_metadata and "metadata" in filtered:
                        if "system" in filtered.get("metadata", {}):
                            del filtered["metadata"]["system"]
                            if not filtered["metadata"]:
                                del filtered["metadata"]

                    # Filter attachment details
                    if not include_attachment_details and "attachments" in filtered:
                        filtered["attachments"] = [
                            {
                                "id": att.get("id"),
                                "file_name": att.get("file_name"),
                                "content_url": att.get("content_url"),
                                "content_type": att.get("content_type"),
                                "size": att.get("size"),
                            }
                            for att in filtered["attachments"]
                        ]

                    filtered_comments.append(filtered)
                result["comments"] = filtered_comments

            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing ticket comments: {e}"
