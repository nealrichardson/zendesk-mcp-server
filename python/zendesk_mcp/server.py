"""MCP Server for Zendesk API with stdio and HTTP transport support."""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import HTMLResponse

from zendesk_mcp.zendesk_client import zendesk_client
from zendesk_mcp.tools import (
    register_tickets_tools,
    register_users_tools,
    register_organizations_tools,
    register_groups_tools,
    register_macros_tools,
    register_views_tools,
    register_triggers_tools,
    register_automations_tools,
    register_search_tools,
    register_help_center_tools,
    register_support_tools,
    register_talk_tools,
    register_chat_tools,
    register_attachments_tools,
)

# Load environment variables
load_dotenv()

# Check if write tools (create/update/delete) should be enabled
write_enabled = os.getenv("ZENDESK_WRITE_ENABLED", "").lower() == "true"

# Create the FastMCP server instance
mcp = FastMCP("zendesk-mcp")

# Register all tools
register_tickets_tools(mcp, zendesk_client, write_enabled)
register_users_tools(mcp, zendesk_client, write_enabled)
register_organizations_tools(mcp, zendesk_client, write_enabled)
register_groups_tools(mcp, zendesk_client, write_enabled)
register_macros_tools(mcp, zendesk_client, write_enabled)
register_views_tools(mcp, zendesk_client, write_enabled)
register_triggers_tools(mcp, zendesk_client, write_enabled)
register_automations_tools(mcp, zendesk_client, write_enabled)
register_search_tools(mcp, zendesk_client, write_enabled)
register_help_center_tools(mcp, zendesk_client, write_enabled)
register_support_tools(mcp, zendesk_client, write_enabled)
register_talk_tools(mcp, zendesk_client, write_enabled)
register_chat_tools(mcp, zendesk_client, write_enabled)
register_attachments_tools(mcp, zendesk_client, write_enabled)


# Landing page route
@mcp.custom_route("/", methods=["GET"])
async def landing_page(request: Request) -> HTMLResponse:
    """Serve a landing page with server info and setup instructions."""
    # Get list of tools for display
    tools = await mcp.list_tools()
    tools_by_category = {
        "Tickets": [
            t
            for t in tools
            if t.name.startswith(
                (
                    "list_ticket",
                    "get_ticket",
                    "create_ticket",
                    "update_ticket",
                    "delete_ticket",
                )
            )
        ],
        "Users": [t for t in tools if "user" in t.name],
        "Organizations": [t for t in tools if "organization" in t.name],
        "Groups": [t for t in tools if "group" in t.name],
        "Macros": [t for t in tools if "macro" in t.name],
        "Views": [t for t in tools if "view" in t.name],
        "Triggers": [t for t in tools if "trigger" in t.name],
        "Automations": [t for t in tools if "automation" in t.name],
        "Search": [t for t in tools if t.name == "search"],
        "Help Center": [t for t in tools if "article" in t.name],
        "Talk": [t for t in tools if "talk" in t.name],
        "Chat": [t for t in tools if "chat" in t.name],
        "Attachments": [t for t in tools if "attachment" in t.name],
        "Other": [t for t in tools if t.name == "support_info"],
    }

    tools_html = ""
    for category, category_tools in tools_by_category.items():
        if category_tools:
            tools_html += f"<h3>{category}</h3><ul>"
            for tool in category_tools:
                tools_html += f"<li><code>{tool.name}</code> - {tool.description or 'No description'}</li>"
            tools_html += "</ul>"

    # Build base URL, accounting for proxy path prefixes
    # Check for X-Forwarded headers first (common with proxies)
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    forwarded_host = request.headers.get("x-forwarded-host", request.url.netloc)

    # Get the current path and derive base path (strip trailing slash)
    current_path = str(request.url.path).rstrip("/")

    # Build the base URL
    base_url = f"{forwarded_proto}://{forwarded_host}{current_path}"
    sse_url = f"{base_url}/sse"

    # Mode indicator
    if write_enabled:
        mode_badge = '<span class="mode-badge mode-write">Write Mode Enabled</span>'
        mode_description = """
        <p>This server is running in <strong>write mode</strong>. Tools for creating, updating, and
        deleting records are available.</p>
        <p>To switch to read-only mode, set <code>ZENDESK_WRITE_ENABLED=false</code> (or remove it)
        in your environment and restart the server.</p>
        """
    else:
        mode_badge = '<span class="mode-badge mode-readonly">Read-Only Mode</span>'
        mode_description = """
        <p>This server is running in <strong>read-only mode</strong>. Only tools for listing and
        retrieving data are available. Create, update, and delete operations are disabled.</p>
        <p>To enable write operations, set <code>ZENDESK_WRITE_ENABLED=true</code> in your
        environment and restart the server.</p>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Zendesk MCP Server</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 2rem;
                line-height: 1.6;
                color: #333;
            }}
            h1 {{ color: #1a1a1a; border-bottom: 2px solid #0066cc; padding-bottom: 0.5rem; }}
            h2 {{ color: #444; margin-top: 2rem; }}
            h3 {{ color: #666; margin-top: 1.5rem; margin-bottom: 0.5rem; }}
            code {{
                background: #f4f4f4;
                padding: 0.2rem 0.4rem;
                border-radius: 3px;
                font-size: 0.9em;
            }}
            pre {{
                background: #f4f4f4;
                padding: 1rem;
                border-radius: 5px;
                overflow-x: auto;
            }}
            ul {{ margin-top: 0.5rem; }}
            li {{ margin-bottom: 0.3rem; }}
            .endpoint {{
                background: #e7f3ff;
                padding: 1rem;
                border-radius: 5px;
                margin: 1rem 0;
                border-left: 4px solid #0066cc;
            }}
            .tools-section {{ margin-top: 2rem; }}
            .mode-badge {{
                display: inline-block;
                padding: 0.3rem 0.8rem;
                border-radius: 4px;
                font-size: 0.9em;
                font-weight: 600;
                margin-left: 1rem;
                vertical-align: middle;
            }}
            .mode-readonly {{
                background: #e8f5e9;
                color: #2e7d32;
                border: 1px solid #a5d6a7;
            }}
            .mode-write {{
                background: #fff3e0;
                color: #e65100;
                border: 1px solid #ffcc80;
            }}
            .mode-info {{
                background: #f5f5f5;
                padding: 1rem;
                border-radius: 5px;
                margin: 1rem 0;
                border-left: 4px solid #9e9e9e;
            }}
        </style>
    </head>
    <body>
        <h1>Zendesk MCP Server</h1>
        <p>This is a <a href="https://modelcontextprotocol.io">Model Context Protocol (MCP)</a> server
        that provides access to the Zendesk API for AI assistants.</p>

        <h2>Endpoints</h2>
        <div class="endpoint">
            <strong>SSE Stream:</strong> <code>{base_url}/sse</code><br>
            <strong>Messages:</strong> <code>{base_url}/messages</code> (POST)
        </div>

        <h2>Setup Instructions</h2>

        <h3>Claude Code</h3>
        <p>Run this command:</p>
        <pre>claude mcp add zendesk --transport sse --url {sse_url}</pre>

        <h3>Claude Desktop</h3>
        <p>Add to <code>~/Library/Application Support/Claude/claude_desktop_config.json</code> (macOS)
        or <code>%APPDATA%\\Claude\\claude_desktop_config.json</code> (Windows):</p>
        <pre>{{
  "mcpServers": {{
    "zendesk": {{
      "type": "sse",
      "url": "{sse_url}"
    }}
  }}
}}</pre>

        <h3>VS Code with Continue Extension</h3>
        <p>Add to your Continue config:</p>
        <pre>{{
  "mcpServers": [
    {{
      "name": "zendesk",
      "transport": {{
        "type": "sse",
        "url": "{sse_url}"
      }}
    }}
  ]
}}</pre>

        <h3>Cursor</h3>
        <p>Add to your MCP settings in Cursor preferences:</p>
        <pre>{{
  "zendesk": {{
    "url": "{sse_url}"
  }}
}}</pre>

        <h2 class="tools-section">Available Tools ({len(tools)} total) {mode_badge}</h2>

        <div class="mode-info">
            {mode_description}
        </div>

        {tools_html}

        <hr style="margin-top: 3rem;">
        <p style="color: #666; font-size: 0.9em;">
            <a href="https://github.com/nealrichardson/zendesk-mcp-server">GitHub Repository</a>
        </p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# ASGI app for uvicorn: `uvicorn zendesk_mcp.server:app`
app = mcp.sse_app()


async def run_stdio() -> None:
    """Run the server with stdio transport."""
    await mcp.run_stdio_async()


async def run_http(host: str, port: int) -> None:
    """Run the server with HTTP/SSE transport using uvicorn."""
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server_instance = uvicorn.Server(config)
    print(f"Starting Zendesk MCP server (HTTP/SSE) on http://{host}:{port}")
    print(f"  SSE endpoint: http://{host}:{port}/sse")
    print(f"  Messages endpoint: http://{host}:{port}/messages")
    await server_instance.serve()


def main() -> None:
    """Main entry point for the Zendesk MCP server."""
    parser = argparse.ArgumentParser(description="Zendesk MCP Server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run with HTTP/SSE transport instead of stdio",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HTTP_HOST", "0.0.0.0"),
        help="Host to bind to for HTTP mode (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_HTTP_PORT", "8000")),
        help="Port to bind to for HTTP mode (default: 8000)",
    )
    args = parser.parse_args()

    # Check transport mode from env var if not specified via CLI
    use_http = args.http or os.getenv("MCP_TRANSPORT", "stdio").lower() == "http"

    if use_http:
        asyncio.run(run_http(args.host, args.port))
    else:
        print("Starting Zendesk MCP server (stdio)...", file=sys.stderr)
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
