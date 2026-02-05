"""Help Center tools for Zendesk MCP Server."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from zendesk_mcp.zendesk_client import ZendeskClient


def register_help_center_tools(mcp: FastMCP, client: ZendeskClient, enable_write_tools: bool = False) -> None:
    """Register help center-related tools with the MCP server."""

    def write_tool(func):
        """Only register as a tool if write mode is enabled."""
        if enable_write_tools:
            return mcp.tool()(func)
        return func

    @mcp.tool()
    async def list_articles(
        page: int | None = None,
        per_page: int | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> str:
        """List Help Center articles.

        Args:
            page: Page number for pagination
            per_page: Number of articles per page (max 100)
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
            result = await client.list_articles(params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing articles: {e}"

    @mcp.tool()
    async def get_article(id: int) -> str:
        """Get a specific Help Center article by ID.

        Args:
            id: Article ID
        """
        try:
            result = await client.get_article(id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting article: {e}"

    @write_tool
    async def create_article(
        title: str,
        body: str,
        section_id: int,
        locale: str | None = None,
        draft: bool | None = None,
        permission_group_id: int | None = None,
        user_segment_id: int | None = None,
        label_names: list[str] | None = None,
    ) -> str:
        """Create a new Help Center article.

        Args:
            title: Article title
            body: Article body content (HTML)
            section_id: Section ID where the article will be created
            locale: Article locale (e.g., 'en-us')
            draft: Whether the article is a draft
            permission_group_id: Permission group ID for the article
            user_segment_id: User segment ID for the article
            label_names: Labels for the article
        """
        try:
            article_data: dict[str, Any] = {"title": title, "body": body}
            if locale is not None:
                article_data["locale"] = locale
            if draft is not None:
                article_data["draft"] = draft
            if permission_group_id is not None:
                article_data["permission_group_id"] = permission_group_id
            if user_segment_id is not None:
                article_data["user_segment_id"] = user_segment_id
            if label_names is not None:
                article_data["label_names"] = label_names

            result = await client.create_article(article_data, section_id)
            return f"Article created successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error creating article: {e}"

    @write_tool
    async def update_article(
        id: int,
        title: str | None = None,
        body: str | None = None,
        locale: str | None = None,
        draft: bool | None = None,
        permission_group_id: int | None = None,
        user_segment_id: int | None = None,
        label_names: list[str] | None = None,
    ) -> str:
        """Update an existing Help Center article.

        Args:
            id: Article ID to update
            title: Updated article title
            body: Updated article body content (HTML)
            locale: Updated article locale (e.g., 'en-us')
            draft: Whether the article is a draft
            permission_group_id: Updated permission group ID
            user_segment_id: Updated user segment ID
            label_names: Updated labels
        """
        try:
            article_data: dict[str, Any] = {}
            if title is not None:
                article_data["title"] = title
            if body is not None:
                article_data["body"] = body
            if locale is not None:
                article_data["locale"] = locale
            if draft is not None:
                article_data["draft"] = draft
            if permission_group_id is not None:
                article_data["permission_group_id"] = permission_group_id
            if user_segment_id is not None:
                article_data["user_segment_id"] = user_segment_id
            if label_names is not None:
                article_data["label_names"] = label_names

            result = await client.update_article(id, article_data)
            return f"Article updated successfully!\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error updating article: {e}"

    @write_tool
    async def delete_article(id: int) -> str:
        """Delete a Help Center article.

        Args:
            id: Article ID to delete
        """
        try:
            await client.delete_article(id)
            return f"Article {id} deleted successfully!"
        except Exception as e:
            return f"Error deleting article: {e}"
