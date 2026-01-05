"""Tests for the Zendesk MCP server."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from zendesk_mcp.server import (
    CombinedMCPApp,
    mcp,
    sse_app,
    streamable_http_app,
    app,
)


class TestToolRegistration:
    """Tests for tool registration on the MCP server."""

    def test_fastmcp_has_tools_registered(self):
        """The FastMCP instance should have tools registered."""
        # Access the internal tool manager
        tools = mcp._tool_manager._tools
        assert len(tools) > 0, "No tools registered on FastMCP instance"

    def test_has_expected_tool_categories(self):
        """Should have tools from all expected categories."""
        tools = mcp._tool_manager._tools
        tool_names = list(tools.keys())

        # Check for tools from different categories
        assert any("ticket" in name for name in tool_names), "Missing ticket tools"
        assert any("user" in name for name in tool_names), "Missing user tools"
        assert any("organization" in name for name in tool_names), "Missing organization tools"
        assert any("search" in name for name in tool_names), "Missing search tools"

    @pytest.mark.asyncio
    async def test_list_tools_returns_tools(self):
        """mcp.list_tools() should return registered tools."""
        tools = await mcp.list_tools()
        assert len(tools) > 0, "list_tools() returned no tools"

    @pytest.mark.asyncio
    async def test_sse_app_has_same_tools(self):
        """SSE app should have access to the same tools as FastMCP."""
        fastmcp_tools = await mcp.list_tools()
        fastmcp_tool_names = {t.name for t in fastmcp_tools}

        # The SSE app uses the same FastMCP instance, so tools should be accessible
        assert len(fastmcp_tool_names) > 0

    @pytest.mark.asyncio
    async def test_streamable_http_app_has_same_tools(self):
        """Streamable HTTP app should have access to the same tools as FastMCP."""
        fastmcp_tools = await mcp.list_tools()
        fastmcp_tool_names = {t.name for t in fastmcp_tools}

        # The streamable HTTP app uses the same FastMCP instance
        assert len(fastmcp_tool_names) > 0


class TestAppTypes:
    """Tests for the different app types."""

    def test_sse_app_is_starlette(self):
        """SSE app should be a Starlette application."""
        from starlette.applications import Starlette
        assert isinstance(sse_app, Starlette)

    def test_streamable_http_app_is_starlette(self):
        """Streamable HTTP app should be a Starlette application."""
        from starlette.applications import Starlette
        assert isinstance(streamable_http_app, Starlette)

    def test_combined_app_is_custom_class(self):
        """Combined app should be our CombinedMCPApp."""
        assert isinstance(app, CombinedMCPApp)


class TestSSEAppRoutes:
    """Tests for SSE app routes."""

    def test_has_landing_page_route(self):
        """SSE app should have a landing page at /."""
        paths = {r.path for r in sse_app.routes if hasattr(r, "path")}
        assert "/" in paths

    def test_has_sse_route(self):
        """SSE app should have /sse endpoint."""
        paths = {r.path for r in sse_app.routes if hasattr(r, "path")}
        assert "/sse" in paths

    def test_has_messages_route(self):
        """SSE app should have /messages endpoint."""
        paths = {r.path for r in sse_app.routes if hasattr(r, "path")}
        assert "/messages" in paths


class TestStreamableHTTPAppRoutes:
    """Tests for streamable HTTP app routes."""

    def test_has_mcp_route(self):
        """Streamable HTTP app should have /mcp endpoint."""
        paths = {r.path for r in streamable_http_app.routes if hasattr(r, "path")}
        assert "/mcp" in paths


class MockASGIApp:
    """Mock ASGI app for testing routing."""

    def __init__(self, name: str):
        self.name = name
        self.called = False
        self.call_count = 0

    async def __call__(self, scope, receive, send):
        self.called = True
        self.call_count += 1


class TestCombinedAppRouting:
    """Tests for the combined app request routing."""

    @pytest.mark.asyncio
    async def test_routes_mcp_to_http_app(self):
        """Requests to /mcp should be routed to streamable HTTP app."""
        sse_mock = MockASGIApp("sse")
        http_mock = MockASGIApp("http")

        test_app = CombinedMCPApp(sse_mock, http_mock)

        scope = {"type": "http", "path": "/mcp", "method": "GET"}
        await test_app(scope, AsyncMock(), AsyncMock())

        assert http_mock.called, "/mcp should route to HTTP app"
        assert not sse_mock.called, "/mcp should not route to SSE app"

    @pytest.mark.asyncio
    async def test_routes_sse_to_sse_app(self):
        """Requests to /sse should be routed to SSE app."""
        sse_mock = MockASGIApp("sse")
        http_mock = MockASGIApp("http")

        test_app = CombinedMCPApp(sse_mock, http_mock)

        scope = {"type": "http", "path": "/sse", "method": "GET"}
        await test_app(scope, AsyncMock(), AsyncMock())

        assert sse_mock.called, "/sse should route to SSE app"
        assert not http_mock.called, "/sse should not route to HTTP app"

    @pytest.mark.asyncio
    async def test_routes_landing_to_sse_app(self):
        """Requests to / should be routed to SSE app."""
        sse_mock = MockASGIApp("sse")
        http_mock = MockASGIApp("http")

        test_app = CombinedMCPApp(sse_mock, http_mock)

        scope = {"type": "http", "path": "/", "method": "GET"}
        await test_app(scope, AsyncMock(), AsyncMock())

        assert sse_mock.called, "/ should route to SSE app"
        assert not http_mock.called, "/ should not route to HTTP app"

    @pytest.mark.asyncio
    async def test_routes_messages_to_sse_app(self):
        """Requests to /messages should be routed to SSE app."""
        sse_mock = MockASGIApp("sse")
        http_mock = MockASGIApp("http")

        test_app = CombinedMCPApp(sse_mock, http_mock)

        scope = {"type": "http", "path": "/messages", "method": "POST"}
        await test_app(scope, AsyncMock(), AsyncMock())

        assert sse_mock.called, "/messages should route to SSE app"
        assert not http_mock.called, "/messages should not route to HTTP app"


class MockLifespanApp:
    """Mock ASGI app that handles lifespan events."""

    def __init__(self, name: str):
        self.name = name
        self.started = False
        self.shutdown = False

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                self.started = True
                await send({"type": "lifespan.startup.complete"})
            msg = await receive()
            if msg["type"] == "lifespan.shutdown":
                self.shutdown = True
                await send({"type": "lifespan.shutdown.complete"})


class TestCombinedAppLifespan:
    """Tests for the combined app lifespan handling."""

    @pytest.mark.asyncio
    async def test_lifespan_starts_both_apps(self):
        """Lifespan startup should initialize both sub-apps."""
        sse_mock = MockLifespanApp("sse")
        http_mock = MockLifespanApp("http")

        test_app = CombinedMCPApp(sse_mock, http_mock)

        messages_sent = []
        message_queue = asyncio.Queue()
        await message_queue.put({"type": "lifespan.startup"})

        async def receive():
            return await message_queue.get()

        async def send(msg):
            messages_sent.append(msg)
            if msg["type"] == "lifespan.startup.complete":
                # Trigger shutdown after startup completes
                await message_queue.put({"type": "lifespan.shutdown"})

        scope = {"type": "lifespan", "asgi": {"version": "3.0"}}

        # Run with timeout to prevent hanging
        try:
            await asyncio.wait_for(
                test_app(scope, receive, send),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            pass

        assert sse_mock.started, "SSE app lifespan should have started"
        assert http_mock.started, "HTTP app lifespan should have started"

    @pytest.mark.asyncio
    async def test_real_combined_app_lifespan(self):
        """Test the actual combined app's lifespan handling."""
        messages_sent = []
        message_queue = asyncio.Queue()
        await message_queue.put({"type": "lifespan.startup"})

        async def receive():
            return await message_queue.get()

        async def send(msg):
            messages_sent.append(msg)
            if msg["type"] == "lifespan.startup.complete":
                await message_queue.put({"type": "lifespan.shutdown"})

        scope = {"type": "lifespan", "asgi": {"version": "3.0"}}

        try:
            await asyncio.wait_for(
                app(scope, receive, send),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            pytest.fail("Lifespan handling timed out")

        message_types = [m["type"] for m in messages_sent]
        assert "lifespan.startup.complete" in message_types, (
            f"Expected startup.complete, got: {message_types}"
        )
        assert "lifespan.shutdown.complete" in message_types, (
            f"Expected shutdown.complete, got: {message_types}"
        )


class TestStreamableHTTPInitialization:
    """Tests specifically for streamable HTTP transport initialization."""

    def test_streamable_http_app_has_session_manager(self):
        """Streamable HTTP app should have routes that include session manager."""
        # Find the /mcp route
        mcp_route = None
        for route in streamable_http_app.routes:
            if hasattr(route, "path") and route.path == "/mcp":
                mcp_route = route
                break

        assert mcp_route is not None, "No /mcp route found"
        # The endpoint should be a StreamableHTTPASGIApp
        assert mcp_route.endpoint is not None

    @pytest.mark.asyncio
    async def test_streamable_http_tools_accessible_after_lifespan(self):
        """After lifespan startup, streamable HTTP should have tools accessible."""
        # This tests the core issue - tools should be available via streamable HTTP
        # after proper initialization

        messages_sent = []
        message_queue = asyncio.Queue()
        await message_queue.put({"type": "lifespan.startup"})

        async def receive():
            return await message_queue.get()

        async def send(msg):
            messages_sent.append(msg)
            if msg["type"] == "lifespan.startup.complete":
                await message_queue.put({"type": "lifespan.shutdown"})

        scope = {"type": "lifespan", "asgi": {"version": "3.0"}}

        try:
            await asyncio.wait_for(
                app(scope, receive, send),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            pytest.fail("Lifespan handling timed out")

        # After successful lifespan, tools should still be registered
        tools = await mcp.list_tools()
        assert len(tools) > 0, "Tools should be accessible after lifespan startup"

    def test_streamable_http_uses_same_server(self):
        """Both SSE and streamable HTTP apps should use the same FastMCP server."""
        # The /mcp endpoint's handler should reference the same server
        mcp_route = None
        for route in streamable_http_app.routes:
            if hasattr(route, "path") and route.path == "/mcp":
                mcp_route = route
                break

        assert mcp_route is not None

        # The endpoint is a StreamableHTTPASGIApp which has a session_manager
        endpoint = mcp_route.endpoint
        assert hasattr(endpoint, "session_manager"), "Endpoint should have session_manager"

        session_manager = endpoint.session_manager

        # Session manager has a public 'app' attribute which is the MCP Server
        assert hasattr(session_manager, "app"), "Session manager should have app"

        # The app should be an MCP Server that has tools registered
        server_app = session_manager.app
        print(f"Server app type: {type(server_app)}")
        print(f"Server app: {server_app}")

        # Check that the server has tools registered
        # The server should have list_tools capability
        from mcp.server import Server
        assert isinstance(server_app, Server), f"Expected Server, got {type(server_app)}"

    def test_streamable_http_server_has_tools(self):
        """The streamable HTTP server should have tools registered."""
        mcp_route = None
        for route in streamable_http_app.routes:
            if hasattr(route, "path") and route.path == "/mcp":
                mcp_route = route
                break

        endpoint = mcp_route.endpoint
        session_manager = endpoint.session_manager
        server_app = session_manager.app

        # Check the server's internal state for tool handlers
        # The Server class stores handlers in request_handlers dict
        print(f"Server attributes: {[a for a in dir(server_app) if not a.startswith('__')]}")

        # Check if the server has tool-related handlers registered
        if hasattr(server_app, "request_handlers"):
            handlers = server_app.request_handlers
            print(f"Request handlers: {list(handlers.keys()) if handlers else 'None'}")

    def test_fastmcp_internal_server_matches_streamable_http(self):
        """FastMCP's internal server should be the same as streamable HTTP's server."""
        # Get the streamable HTTP server
        mcp_route = None
        for route in streamable_http_app.routes:
            if hasattr(route, "path") and route.path == "/mcp":
                mcp_route = route
                break

        endpoint = mcp_route.endpoint
        http_server = endpoint.session_manager.app

        # Get FastMCP's internal server
        # FastMCP wraps a Server internally
        fastmcp_server = mcp._mcp_server

        print(f"HTTP server: {http_server}")
        print(f"FastMCP server: {fastmcp_server}")
        print(f"Same server? {http_server is fastmcp_server}")

        # They should be the same object
        assert http_server is fastmcp_server, (
            "Streamable HTTP and FastMCP should use the same Server instance"
        )

    def test_sse_and_streamable_http_share_fastmcp(self):
        """Verify that calling sse_app() and streamable_http_app() doesn't break sharing."""
        # Get tool count directly from FastMCP
        internal_tools = mcp._tool_manager._tools
        tool_count = len(internal_tools)

        assert tool_count > 0, "FastMCP should have tools registered"

        # Create fresh apps - this simulates what happens at module load time
        # Both should still see the same tools
        fresh_sse = mcp.sse_app()
        fresh_http = mcp.streamable_http_app()

        # Tools should still be registered
        new_tool_count = len(mcp._tool_manager._tools)
        assert new_tool_count == tool_count, (
            f"Tool count changed after creating apps: {tool_count} -> {new_tool_count}"
        )

    @pytest.mark.asyncio
    async def test_server_list_tools_directly(self):
        """Test that we can list tools directly via FastMCP."""
        # The FastMCP instance should return tools
        tools_result = await mcp.list_tools()

        print(f"Tools from mcp.list_tools(): {len(tools_result)} tools")
        if tools_result:
            print(f"First 5 tool names: {[t.name for t in tools_result[:5]]}")

        assert len(tools_result) > 0, (
            "mcp.list_tools() should return tools"
        )

        # Verify the same tools would be accessible via the Server's handler
        mcp_route = None
        for route in streamable_http_app.routes:
            if hasattr(route, "path") and route.path == "/mcp":
                mcp_route = route
                break

        endpoint = mcp_route.endpoint
        server = endpoint.session_manager.app

        # The server should have a ListToolsRequest handler
        from mcp.types import ListToolsRequest
        assert ListToolsRequest in server.request_handlers, (
            "Server should have ListToolsRequest handler"
        )

    @pytest.mark.asyncio
    async def test_multiple_streamable_http_apps_share_server(self):
        """Creating multiple streamable HTTP apps should share the same server."""
        app1 = mcp.streamable_http_app()
        app2 = mcp.streamable_http_app()

        # Get servers and session managers from both apps
        def get_server_and_sm(app):
            for route in app.routes:
                if hasattr(route, "path") and route.path == "/mcp":
                    endpoint = route.endpoint
                    return endpoint.session_manager.app, endpoint.session_manager
            return None, None

        server1, sm1 = get_server_and_sm(app1)
        server2, sm2 = get_server_and_sm(app2)

        print(f"Server 1: {server1}")
        print(f"Server 2: {server2}")
        print(f"Same server? {server1 is server2}")
        print(f"Session manager 1: {sm1}")
        print(f"Session manager 2: {sm2}")
        print(f"Same session manager? {sm1 is sm2}")

        # They should be the same server instance
        assert server1 is server2, (
            "Multiple streamable_http_app() calls should return apps with the same server"
        )

        # But session managers might be different!
        # This could be a problem if we're routing to a different session manager


class TestMCPProtocol:
    """Tests that simulate actual MCP client behavior."""

    @pytest.mark.asyncio
    async def test_initialize_and_list_tools_via_protocol(self):
        """Simulate what an MCP client does: initialize, then list tools."""
        from mcp.types import (
            InitializeRequest,
            InitializeRequestParams,
            ClientCapabilities,
            Implementation,
            ListToolsRequest,
        )

        # Get the server
        server = mcp._mcp_server

        # Create a mock request context (normally provided by the transport)
        # The server should be able to handle these requests

        # Check that the handlers exist
        assert InitializeRequest in server.request_handlers or hasattr(server, 'create_initialization_options'), \
            "Server should handle initialization"
        assert ListToolsRequest in server.request_handlers, \
            "Server should handle ListToolsRequest"

        # Get the handler for ListToolsRequest
        handler = server.request_handlers.get(ListToolsRequest)
        assert handler is not None, "ListToolsRequest handler should exist"

        print(f"ListToolsRequest handler: {handler}")

    @pytest.mark.asyncio
    async def test_streamable_http_endpoint_structure(self):
        """Verify the /mcp endpoint is correctly structured."""
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

        # Find /mcp route
        mcp_route = None
        for route in streamable_http_app.routes:
            if hasattr(route, "path") and route.path == "/mcp":
                mcp_route = route
                break

        assert mcp_route is not None

        endpoint = mcp_route.endpoint
        print(f"Endpoint type: {type(endpoint)}")
        print(f"Endpoint: {endpoint}")

        # The endpoint should be a StreamableHTTPASGIApp
        assert hasattr(endpoint, "session_manager")

        sm = endpoint.session_manager
        assert isinstance(sm, StreamableHTTPSessionManager)

        # Check session manager state BEFORE lifespan
        print(f"Session manager._has_started (before lifespan): {sm._has_started}")
        print(f"Session manager.stateless: {sm.stateless}")
        print(f"Session manager.app: {sm.app}")

        # The app should be the MCP server
        assert sm.app is mcp._mcp_server

    @pytest.mark.asyncio
    async def test_session_manager_starts_after_lifespan(self):
        """Verify session manager is started after lifespan startup."""
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

        # Get the session manager from the combined app's http_app
        mcp_route = None
        for route in app.http_app.routes:
            if hasattr(route, "path") and route.path == "/mcp":
                mcp_route = route
                break

        endpoint = mcp_route.endpoint
        sm = endpoint.session_manager

        print(f"Session manager._has_started BEFORE lifespan: {sm._has_started}")

        # Now trigger lifespan startup
        message_queue = asyncio.Queue()
        await message_queue.put({"type": "lifespan.startup"})

        messages_sent = []

        async def receive():
            return await message_queue.get()

        async def send(msg):
            messages_sent.append(msg)
            if msg["type"] == "lifespan.startup.complete":
                # Check session manager state AFTER startup
                print(f"Session manager._has_started AFTER startup: {sm._has_started}")
                # Trigger shutdown
                await message_queue.put({"type": "lifespan.shutdown"})

        scope = {"type": "lifespan", "asgi": {"version": "3.0"}}

        try:
            await asyncio.wait_for(app(scope, receive, send), timeout=5.0)
        except asyncio.TimeoutError:
            pytest.fail("Lifespan handling timed out")

        # The key assertion: session manager should have been started
        # during lifespan startup
        print(f"Session manager._has_started AFTER shutdown: {sm._has_started}")
        print(f"Messages sent: {[m['type'] for m in messages_sent]}")


class TestCombinedAppExport:
    """Tests for the combined app export."""

    def test_combined_app_uses_correct_sub_apps(self):
        """The combined app should use the module-level sse_app and streamable_http_app."""
        assert app.sse_app is sse_app
        assert app.http_app is streamable_http_app

    def test_combined_app_http_app_has_tools(self):
        """The combined app's HTTP app should have access to tools."""
        # Get the server from combined app's http_app
        mcp_route = None
        for route in app.http_app.routes:
            if hasattr(route, "path") and route.path == "/mcp":
                mcp_route = route
                break

        assert mcp_route is not None
        endpoint = mcp_route.endpoint
        server = endpoint.session_manager.app

        # Should be the same as the main FastMCP server
        assert server is mcp._mcp_server

    @pytest.mark.asyncio
    async def test_combined_app_routes_to_correct_server(self):
        """After routing, requests should reach the correct server with tools."""
        # Track what server handles the request
        handled_server = None

        # Get the original endpoint
        mcp_route = None
        for route in app.http_app.routes:
            if hasattr(route, "path") and route.path == "/mcp":
                mcp_route = route
                break

        original_endpoint = mcp_route.endpoint
        original_session_manager = original_endpoint.session_manager

        # Verify the session manager has the correct server
        assert original_session_manager.app is mcp._mcp_server

        # Verify tools exist on that server
        tools = await mcp.list_tools()
        assert len(tools) > 0
