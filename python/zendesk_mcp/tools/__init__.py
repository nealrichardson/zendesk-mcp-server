"""Tool modules for Zendesk MCP Server."""

from zendesk_mcp.tools.tickets import register_tickets_tools
from zendesk_mcp.tools.users import register_users_tools
from zendesk_mcp.tools.organizations import register_organizations_tools
from zendesk_mcp.tools.groups import register_groups_tools
from zendesk_mcp.tools.macros import register_macros_tools
from zendesk_mcp.tools.views import register_views_tools
from zendesk_mcp.tools.triggers import register_triggers_tools
from zendesk_mcp.tools.automations import register_automations_tools
from zendesk_mcp.tools.search import register_search_tools
from zendesk_mcp.tools.help_center import register_help_center_tools
from zendesk_mcp.tools.support import register_support_tools
from zendesk_mcp.tools.talk import register_talk_tools
from zendesk_mcp.tools.chat import register_chat_tools
from zendesk_mcp.tools.attachments import register_attachments_tools

__all__ = [
    "register_tickets_tools",
    "register_users_tools",
    "register_organizations_tools",
    "register_groups_tools",
    "register_macros_tools",
    "register_views_tools",
    "register_triggers_tools",
    "register_automations_tools",
    "register_search_tools",
    "register_help_center_tools",
    "register_support_tools",
    "register_talk_tools",
    "register_chat_tools",
    "register_attachments_tools",
]
