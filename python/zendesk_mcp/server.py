"""MCP Server for Zendesk API with stdio and HTTP transport support."""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server

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


def create_server() -> Server:
    """Create and configure the MCP server with all tools."""
    server = Server("zendesk-mcp")

    # Register all tools
    register_tickets_tools(server, zendesk_client)
    register_users_tools(server, zendesk_client)
    register_organizations_tools(server, zendesk_client)
    register_groups_tools(server, zendesk_client)
    register_macros_tools(server, zendesk_client)
    register_views_tools(server, zendesk_client)
    register_triggers_tools(server, zendesk_client)
    register_automations_tools(server, zendesk_client)
    register_search_tools(server, zendesk_client)
    register_help_center_tools(server, zendesk_client)
    register_support_tools(server, zendesk_client)
    register_talk_tools(server, zendesk_client)
    register_chat_tools(server, zendesk_client)
    register_attachments_tools(server, zendesk_client)

    return server


async def run_stdio() -> None:
    """Run the server with stdio transport."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def run_http(host: str, port: int) -> None:
    """Run the server with HTTP/SSE transport."""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    import uvicorn

    server = create_server()
    sse = SseServerTransport("/messages")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    app = Starlette(
        debug=True,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ],
    )

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server_instance = uvicorn.Server(config)
    print(f"Starting Zendesk MCP server (HTTP/SSE) on http://{host}:{port}")
    print(f"  SSE endpoint: http://{host}:{port}/sse")
    print(f"  Messages endpoint: http://{host}:{port}/messages")
    await server_instance.serve()


def main() -> None:
    """Main entry point for the Zendesk MCP server."""
    # Load environment variables from .env file
    load_dotenv()

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
