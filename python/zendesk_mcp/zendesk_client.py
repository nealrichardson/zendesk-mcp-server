"""Zendesk API client for making authenticated requests."""

import base64
import os
import re
from typing import Any

import httpx


class ZendeskClient:
    """Async client for interacting with the Zendesk API."""

    def __init__(self) -> None:
        self.domain = os.getenv("ZENDESK_DOMAIN")
        self.subdomain = os.getenv("ZENDESK_SUBDOMAIN")
        self.email = os.getenv("ZENDESK_EMAIL")
        self.api_token = os.getenv("ZENDESK_API_TOKEN")
        self.password = os.getenv("ZENDESK_PASSWORD")

        if (not self.domain and not self.subdomain) or not self.email or (not self.api_token and not self.password):
            print(
                "Warning: Zendesk credentials not found in environment variables. "
                "Please set (ZENDESK_DOMAIN or ZENDESK_SUBDOMAIN), ZENDESK_EMAIL, "
                "and (ZENDESK_API_TOKEN or ZENDESK_PASSWORD)."
            )

        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def get_base_url(self) -> str:
        """Get the base URL for Zendesk API requests."""
        if self.domain:
            # Strip https:// prefix and trailing slash if present
            clean_domain = re.sub(r"^https?://", "", self.domain).rstrip("/")
            return f"https://{clean_domain}/api/v2"
        return f"https://{self.subdomain}.zendesk.com/api/v2"

    def get_auth_header(self) -> str:
        """Generate the Basic Auth header value."""
        if self.api_token:
            auth_string = f"{self.email}/token:{self.api_token}"
        else:
            auth_string = f"{self.email}:{self.password}"
        auth = base64.b64encode(auth_string.encode()).decode()
        return f"Basic {auth}"

    async def request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make an authenticated request to the Zendesk API."""
        if (not self.domain and not self.subdomain) or not self.email or (not self.api_token and not self.password):
            raise ValueError("Zendesk credentials not configured. Please set environment variables.")

        url = f"{self.get_base_url()}{endpoint}"
        headers = {
            "Authorization": self.get_auth_header(),
            "Content-Type": "application/json",
        }

        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        response = await self.client.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            params=params,
        )

        if response.status_code >= 400:
            raise ValueError(f"Zendesk API Error: {response.status_code} - {response.text}")

        if response.status_code == 204:
            return None
        return response.json()

    # Tickets
    async def list_tickets(self, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", "/tickets.json", params=params)

    async def get_ticket(self, ticket_id: int) -> Any:
        return await self.request("GET", f"/tickets/{ticket_id}.json")

    async def create_ticket(self, data: dict[str, Any]) -> Any:
        return await self.request("POST", "/tickets.json", data={"ticket": data})

    async def update_ticket(self, ticket_id: int, data: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/tickets/{ticket_id}.json", data={"ticket": data})

    async def delete_ticket(self, ticket_id: int) -> Any:
        return await self.request("DELETE", f"/tickets/{ticket_id}.json")

    async def list_ticket_comments(self, ticket_id: int, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", f"/tickets/{ticket_id}/comments.json", params=params)

    # Users
    async def list_users(self, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", "/users.json", params=params)

    async def get_user(self, user_id: int) -> Any:
        return await self.request("GET", f"/users/{user_id}.json")

    async def create_user(self, data: dict[str, Any]) -> Any:
        return await self.request("POST", "/users.json", data={"user": data})

    async def update_user(self, user_id: int, data: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/users/{user_id}.json", data={"user": data})

    async def delete_user(self, user_id: int) -> Any:
        return await self.request("DELETE", f"/users/{user_id}.json")

    # Organizations
    async def list_organizations(self, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", "/organizations.json", params=params)

    async def get_organization(self, org_id: int) -> Any:
        return await self.request("GET", f"/organizations/{org_id}.json")

    async def create_organization(self, data: dict[str, Any]) -> Any:
        return await self.request("POST", "/organizations.json", data={"organization": data})

    async def update_organization(self, org_id: int, data: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/organizations/{org_id}.json", data={"organization": data})

    async def delete_organization(self, org_id: int) -> Any:
        return await self.request("DELETE", f"/organizations/{org_id}.json")

    # Groups
    async def list_groups(self, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", "/groups.json", params=params)

    async def get_group(self, group_id: int) -> Any:
        return await self.request("GET", f"/groups/{group_id}.json")

    async def create_group(self, data: dict[str, Any]) -> Any:
        return await self.request("POST", "/groups.json", data={"group": data})

    async def update_group(self, group_id: int, data: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/groups/{group_id}.json", data={"group": data})

    async def delete_group(self, group_id: int) -> Any:
        return await self.request("DELETE", f"/groups/{group_id}.json")

    # Macros
    async def list_macros(self, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", "/macros.json", params=params)

    async def get_macro(self, macro_id: int) -> Any:
        return await self.request("GET", f"/macros/{macro_id}.json")

    async def create_macro(self, data: dict[str, Any]) -> Any:
        return await self.request("POST", "/macros.json", data={"macro": data})

    async def update_macro(self, macro_id: int, data: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/macros/{macro_id}.json", data={"macro": data})

    async def delete_macro(self, macro_id: int) -> Any:
        return await self.request("DELETE", f"/macros/{macro_id}.json")

    # Views
    async def list_views(self, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", "/views.json", params=params)

    async def get_view(self, view_id: int) -> Any:
        return await self.request("GET", f"/views/{view_id}.json")

    async def create_view(self, data: dict[str, Any]) -> Any:
        return await self.request("POST", "/views.json", data={"view": data})

    async def update_view(self, view_id: int, data: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/views/{view_id}.json", data={"view": data})

    async def delete_view(self, view_id: int) -> Any:
        return await self.request("DELETE", f"/views/{view_id}.json")

    # Triggers
    async def list_triggers(self, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", "/triggers.json", params=params)

    async def get_trigger(self, trigger_id: int) -> Any:
        return await self.request("GET", f"/triggers/{trigger_id}.json")

    async def create_trigger(self, data: dict[str, Any]) -> Any:
        return await self.request("POST", "/triggers.json", data={"trigger": data})

    async def update_trigger(self, trigger_id: int, data: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/triggers/{trigger_id}.json", data={"trigger": data})

    async def delete_trigger(self, trigger_id: int) -> Any:
        return await self.request("DELETE", f"/triggers/{trigger_id}.json")

    # Automations
    async def list_automations(self, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", "/automations.json", params=params)

    async def get_automation(self, automation_id: int) -> Any:
        return await self.request("GET", f"/automations/{automation_id}.json")

    async def create_automation(self, data: dict[str, Any]) -> Any:
        return await self.request("POST", "/automations.json", data={"automation": data})

    async def update_automation(self, automation_id: int, data: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/automations/{automation_id}.json", data={"automation": data})

    async def delete_automation(self, automation_id: int) -> Any:
        return await self.request("DELETE", f"/automations/{automation_id}.json")

    # Search
    async def search(self, query: str, params: dict[str, Any] | None = None) -> Any:
        search_params = {"query": query}
        if params:
            search_params.update(params)
        return await self.request("GET", "/search.json", params=search_params)

    # Help Center
    async def list_articles(self, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", "/help_center/articles.json", params=params)

    async def get_article(self, article_id: int) -> Any:
        return await self.request("GET", f"/help_center/articles/{article_id}.json")

    async def create_article(self, data: dict[str, Any], section_id: int) -> Any:
        return await self.request("POST", f"/help_center/sections/{section_id}/articles.json", data={"article": data})

    async def update_article(self, article_id: int, data: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/help_center/articles/{article_id}.json", data={"article": data})

    async def delete_article(self, article_id: int) -> Any:
        return await self.request("DELETE", f"/help_center/articles/{article_id}.json")

    # Talk
    async def get_talk_stats(self) -> Any:
        return await self.request("GET", "/channels/voice/stats.json")

    # Chat
    async def list_chats(self, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", "/chats.json", params=params)

    # Attachments
    async def get_attachment(self, attachment_id: int) -> Any:
        return await self.request("GET", f"/attachments/{attachment_id}.json")

    async def download_attachment(self, content_url: str) -> dict[str, Any]:
        """Download attachment content and return base64-encoded data."""
        headers = {"Authorization": self.get_auth_header()}

        response = await self.client.get(content_url, headers=headers)

        if response.status_code >= 400:
            raise ValueError(f"Zendesk API Error: {response.status_code} - {response.text}")

        return {
            "data": base64.b64encode(response.content).decode(),
            "content_type": response.headers.get("content-type"),
            "size": len(response.content),
        }


# Singleton instance
zendesk_client = ZendeskClient()
