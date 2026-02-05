# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that provides comprehensive access to the Zendesk API. It exposes Zendesk functionality as MCP tools and resources for AI assistants to interact with Zendesk Support, Talk, Chat, and Guide products.

## Development Commands

- `uv run python -m zendesk_mcp` - Start with stdio transport
- `uv run python -m zendesk_mcp --http` - Start with HTTP transport (both SSE and streamable HTTP)
- `uv run python -m zendesk_mcp --http --transport sse` - SSE transport only
- `uv run python -m zendesk_mcp --http --transport streamable-http` - Streamable HTTP only
- `uv run python -m zendesk_mcp --http --port 3000` - Custom port

### Configuration

The server uses a `.env` file with these environment variables:
- Domain: Either `ZENDESK_SUBDOMAIN` (e.g., "mycompany") or `ZENDESK_DOMAIN` (e.g., "mycompany.zendesk.com")
- Authentication (choose one):
  - `ZENDESK_OAUTH_TOKEN` - OAuth access token (uses Bearer auth)
  - `ZENDESK_EMAIL` plus either `ZENDESK_API_TOKEN` (recommended) or `ZENDESK_PASSWORD` (uses Basic auth)
- Write mode: `ZENDESK_WRITE_ENABLED=true` to enable create/update/delete tools (default: false, read-only)
- Extended tools: `ZENDESK_EXTENDED_TOOLS=true` to enable macros, views, triggers, automations, help center, support, talk, and chat tools (default: false, core tools only)
- Transport: `MCP_TRANSPORT=stdio|http`, `MCP_HTTP_TRANSPORT=sse|streamable-http|both`, `MCP_HTTP_HOST`, `MCP_HTTP_PORT`
- Remote deployment: `MCP_ALLOWED_HOSTS` - comma-separated list of allowed hosts for HTTP mode (e.g., "example.com:*,*.example.com:*"). Set to "*" to disable host validation (not recommended for production). Required when deploying behind a proxy or with a custom domain.

### Read-Only vs Write Mode

By default, the server runs in **read-only mode** and only exposes tools for listing and retrieving data (e.g., `list_tickets`, `get_user`, `search`). Write tools (`create_*`, `update_*`, `delete_*`) are disabled.

To enable write operations, set `ZENDESK_WRITE_ENABLED=true` in your `.env` file. This adds tools for:
- Creating tickets, users, organizations, groups, macros, views, triggers, automations, and articles
- Updating existing records
- Deleting records

This design allows safe exploration of Zendesk data without risk of accidental modifications.

### Core vs Extended Tools

By default, the server only exposes **core tools**:
- Tickets (list, get, create, update, delete)
- Users (list, get, create, update, delete)
- Organizations (list, get, create, update, delete)
- Groups (list, get, create, update, delete)
- Search
- Attachments

To enable **extended tools**, set `ZENDESK_EXTENDED_TOOLS=true` in your `.env` file. This adds:
- Macros (list, get, create, update, delete, apply)
- Views (list, get, create, update, delete, execute)
- Triggers (list, get, create, update, delete)
- Automations (list, get, create, update, delete)
- Help Center articles (list, get, create, update, delete)
- Support info
- Talk statistics
- Chat conversations

This design keeps the default tool set focused on common support workflows while allowing opt-in to additional functionality.

## Architecture

**Entry Point (`zendesk_mcp/__main__.py` and `server.py`)**
- Loads environment variables via python-dotenv
- Supports stdio, SSE, and streamable HTTP transports
- CLI argument `--http` enables HTTP mode (serves both SSE and streamable HTTP by default)
- CLI argument `--transport` selects specific transport: `sse`, `streamable-http`, or `both`

**MCP Server (`zendesk_mcp/server.py`)**
- Uses the official `mcp` Python SDK with FastMCP
- Creates Server instance and registers all tools
- For HTTP mode: Uses Starlette with configurable transports
- Endpoints:
  - `GET /mcp` - Streamable HTTP transport (recommended)
  - `GET /sse` - SSE stream
  - `POST /messages` - SSE messages

**Zendesk Client (`zendesk_mcp/zendesk_client.py`)**
- Async client using httpx
- Method-per-endpoint pattern (e.g., `list_tickets()`, `create_ticket()`)
- Singleton instance shared across all tools

**Tool Modules (`zendesk_mcp/tools/*.py`)**
- Each module has a `register_*_tools(server, client, enable_write_tools)` function
- Tools use `@server.tool()` decorator
- Parameters use Python type hints for validation
- Docstrings provide parameter descriptions
- Write tools (create/update/delete) are conditionally registered based on `enable_write_tools`

```python
# Tool pattern
@server.tool()
async def list_tickets(
    page: int | None = None,
    per_page: int | None = None,
) -> str:
    """List tickets in Zendesk.

    Args:
        page: Page number for pagination
        per_page: Number of tickets per page (max 100)
    """
    result = await client.list_tickets({"page": page, "per_page": per_page})
    return json.dumps(result, indent=2)
```

### Tool Organization

Tools are organized by Zendesk domain:
- `tickets.py` - Ticket CRUD operations
- `users.py` - User management
- `organizations.py` - Organization management
- `groups.py` - Agent group management
- `macros.py` - Macro management
- `views.py` - View management
- `triggers.py` - Trigger automation
- `automations.py` - Time-based automations
- `search.py` - Cross-entity search
- `help_center.py` - Help Center article management
- `support.py` - Core support functionality
- `talk.py` - Zendesk Talk statistics
- `chat.py` - Zendesk Chat conversations
- `attachments.py` - Ticket attachment retrieval, download to disk, and automatic extraction

## Adding New Tools

1. Add the API method to `ZendeskClient` in `zendesk_mcp/zendesk_client.py`
2. Create or update a tool module in `zendesk_mcp/tools/`
3. Add `@server.tool()` decorated async function
4. Import and call `register_*_tools()` in `server.py`

## Working with Attachments

The attachment tools support downloading files from tickets and making them available for analysis:

### Attachment Workflow

1. **Get metadata** - Use `get_attachment(id)` to retrieve attachment details including the `content_url`
2. **Download options:**
   - `download_attachment(content_url)` - Returns base64-encoded data (for programmatic use)
   - `download_attachment_to_disk(content_url, filename?)` - Saves to `/tmp/zendesk-attachments/` and returns file path
   - `download_and_extract_attachment(content_url, filename?)` - Downloads and auto-extracts archives

### Analyzing Downloaded Files

Files downloaded to disk can be analyzed using standard file tools:
- **Read** - View file contents
- **Grep** - Search within files
- **Glob** - Find files by pattern in extracted directories
- **Bash** - Use command-line tools for further processing

### Archive Extraction

`download_and_extract_attachment` automatically detects and extracts:
- Tarballs: `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`
- Zip files: `.zip`

Returns the extraction directory path where all files can be accessed like regular codebase files.

### Typical Use Case

```
1. list_ticket_comments(ticketId) -> Find comments with attachments
2. get_attachment(attachmentId) -> Get content_url
3. download_and_extract_attachment(content_url) -> Extract to /tmp/zendesk-attachments/extracted-xxx/
4. Use Read/Grep/Glob to analyze extracted files
```

## Optimizing API Responses

The `list_ticket_comments` tool supports filtering to reduce response size and token usage:

### Body Format Control

By default, only `plain_body` is returned. Use `body_format` parameter to control:
- `"plain"` (default) - Returns only plain_body
- `"html"` - Returns only html_body
- `"both"` - Returns all body formats (body, plain_body, html_body)

### Metadata Filtering

Set `include_metadata: false` (default) to exclude `metadata.system` fields like:
- Client information
- IP address
- Geographic location (latitude/longitude)

### Attachment Details

Set `include_attachment_details: false` (default) to return minimal attachment info:
- Only includes: id, file_name, content_url, content_type, size
- Excludes: thumbnails, malware scan results, inline status, etc.

### Example

```python
# Minimal response (default)
list_ticket_comments(ticket_id=123)

# Full response with all details
list_ticket_comments(
    ticket_id=123,
    body_format="both",
    include_metadata=True,
    include_attachment_details=True
)
```

## Key Implementation Details

- The server communicates via stdio or HTTP using JSON-RPC
- All Zendesk API responses are returned as stringified JSON to the MCP client
- The Zendesk client automatically wraps request bodies in the appropriate key (e.g., `{ ticket: data }`)
- Authentication uses HTTP Basic Auth with either `email/token:api_token` or `email:password`, or Bearer auth with OAuth token
- Attachments are downloaded to `/tmp/zendesk-attachments/` and persist for the session
