# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that provides comprehensive access to the Zendesk API. It exposes Zendesk functionality as MCP tools and resources for AI assistants to interact with Zendesk Support, Talk, Chat, and Guide products.

**This repository contains two implementations:**
- **JavaScript** (`src/`) - Original implementation, stdio transport only
- **Python** (`python/`) - Full implementation with stdio, SSE, and streamable HTTP transports

## Development Commands

### JavaScript Server
- `npm start` - Start the MCP server (stdio)
- `npm run dev` - Start with auto-restart (uses Node's --watch flag)
- `npm run inspect` - Test the server with MCP Inspector

### Python Server
- `cd python && uv run python -m zendesk_mcp` - Start with stdio transport
- `cd python && uv run python -m zendesk_mcp --http` - Start with HTTP transport (both SSE and streamable HTTP)
- `cd python && uv run python -m zendesk_mcp --http --transport sse` - SSE transport only
- `cd python && uv run python -m zendesk_mcp --http --transport streamable-http` - Streamable HTTP only
- `cd python && uv run python -m zendesk_mcp --http --port 3000` - Custom port

### Configuration
Both servers use the same `.env` file with these environment variables:
- Domain: Either `ZENDESK_SUBDOMAIN` (e.g., "mycompany") or `ZENDESK_DOMAIN` (e.g., "mycompany.zendesk.com")
- Authentication (choose one):
  - `ZENDESK_OAUTH_TOKEN` - OAuth access token (uses Bearer auth)
  - `ZENDESK_EMAIL` plus either `ZENDESK_API_TOKEN` (recommended) or `ZENDESK_PASSWORD` (uses Basic auth)
- Write mode: `ZENDESK_WRITE_ENABLED=true` to enable create/update/delete tools (default: false, read-only)
- Python-only: `MCP_TRANSPORT=stdio|http`, `MCP_HTTP_TRANSPORT=sse|streamable-http|both`, `MCP_HTTP_HOST`, `MCP_HTTP_PORT`
- Remote deployment: `MCP_ALLOWED_HOSTS` - comma-separated list of allowed hosts for HTTP mode (e.g., "example.com:*,*.example.com:*"). Set to "*" to disable host validation (not recommended for production). Required when deploying behind a proxy or with a custom domain.

### Read-Only vs Write Mode

By default, the server runs in **read-only mode** and only exposes tools for listing and retrieving data (e.g., `list_tickets`, `get_user`, `search`). Write tools (`create_*`, `update_*`, `delete_*`) are disabled.

To enable write operations, set `ZENDESK_WRITE_ENABLED=true` in your `.env` file. This adds tools for:
- Creating tickets, users, organizations, groups, macros, views, triggers, automations, and articles
- Updating existing records
- Deleting records

This design allows safe exploration of Zendesk data without risk of accidental modifications.

## Architecture

### JavaScript Implementation (`src/`)

**Entry Point (`src/index.js`)**
- Loads environment variables via dotenv
- Creates a StdioServerTransport for MCP communication
- Connects the server to stdio for JSON-RPC messaging

**MCP Server (`src/server.js`)**
- Instantiates McpServer from the MCP SDK
- Aggregates all tool modules and registers them with the server
- Provides a resource template (`zendesk://docs/{section}`) for API documentation

**Zendesk Client (`src/zendesk-client.js`)**
- Singleton class that handles all HTTP communication with Zendesk API
- Manages authentication (API token or password-based Basic Auth)
- Provides method-per-endpoint interface (e.g., `listTickets()`, `createTicket()`)
- All API calls go through the `request()` method which handles errors uniformly

### Tool Module Pattern

Each file in `src/tools/` exports a `*Tools` array containing tool definitions:

```javascript
export const exampleTools = [
  {
    name: "tool_name",           // MCP tool identifier
    description: "...",           // User-facing description
    schema: {                     // Zod schema for parameters
      param: z.string().describe("...")
    },
    handler: async (params) => {  // Implementation
      const result = await zendeskClient.someMethod(params);
      return { content: [{ type: "text", text: JSON.stringify(result) }] };
    }
  }
];
```

All tools follow this structure:
- Use Zod schemas for parameter validation
- Call methods on the shared `zendeskClient` instance
- Return MCP-compliant response objects with `content` array
- Handle errors by returning `{ content: [...], isError: true }`

### Tool Organization

Tools are organized by Zendesk domain:
- `tickets.js` - Ticket CRUD operations
- `users.js` - User management
- `organizations.js` - Organization management
- `groups.js` - Agent group management
- `macros.js` - Macro management
- `views.js` - View management
- `triggers.js` - Trigger automation
- `automations.js` - Time-based automations
- `search.js` - Cross-entity search
- `help-center.js` - Help Center article management
- `support.js` - Core support functionality
- `talk.js` - Zendesk Talk statistics
- `chat.js` - Zendesk Chat conversations
- `attachments.js` - Ticket attachment retrieval, download to disk, and automatic extraction

## Adding New Tools

To add new Zendesk API functionality:

1. Add the API method to `ZendeskClient` in `src/zendesk-client.js`
2. Create or update a tool module in `src/tools/`
3. Follow the tool pattern (name, description, schema, handler)
4. Import and add to `allTools` array in `src/server.js`

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
1. list_ticket_comments(ticketId) → Find comments with attachments
2. get_attachment(attachmentId) → Get content_url
3. download_and_extract_attachment(content_url) → Extract to /tmp/zendesk-attachments/extracted-xxx/
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

```javascript
// Minimal response (default)
list_ticket_comments(ticket_id: 123)

// Full response with all details
list_ticket_comments(
  ticket_id: 123,
  body_format: "both",
  include_metadata: true,
  include_attachment_details: true
)
```

## Key Implementation Details

- This is an ES module project (`"type": "module"` in package.json)
- The server communicates via stdio using JSON-RPC
- All Zendesk API responses are returned as stringified JSON to the MCP client
- The Zendesk client automatically wraps request bodies in the appropriate key (e.g., `{ ticket: data }`)
- Authentication uses HTTP Basic Auth with either `email/token:api_token` or `email:password`
- Attachments are downloaded to `/tmp/zendesk-attachments/` and persist for the session

### Python Implementation (`python/`)

**Entry Point (`python/zendesk_mcp/__main__.py` and `server.py`)**
- Loads environment variables via python-dotenv
- Supports stdio, SSE, and streamable HTTP transports
- CLI argument `--http` enables HTTP mode (serves both SSE and streamable HTTP by default)
- CLI argument `--transport` selects specific transport: `sse`, `streamable-http`, or `both`

**MCP Server (`python/zendesk_mcp/server.py`)**
- Uses the official `mcp` Python SDK with FastMCP
- Creates Server instance and registers all tools
- For HTTP mode: Uses Starlette with configurable transports
- Endpoints:
  - `GET /mcp` - Streamable HTTP transport (recommended)
  - `GET /sse` - SSE stream
  - `POST /messages` - SSE messages

**Zendesk Client (`python/zendesk_mcp/zendesk_client.py`)**
- Async client using httpx
- Same method-per-endpoint pattern as JavaScript
- Singleton instance shared across all tools

**Tool Modules (`python/zendesk_mcp/tools/*.py`)**
- Each module has a `register_*_tools(server, client, enable_write_tools)` function
- Tools use `@server.tool()` decorator
- Parameters use Python type hints for validation
- Docstrings provide parameter descriptions
- Write tools (create/update/delete) are conditionally registered based on `enable_write_tools`

```python
# Python tool pattern
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

## Adding New Tools (Python)

1. Add the API method to `ZendeskClient` in `python/zendesk_mcp/zendesk_client.py`
2. Create or update a tool module in `python/zendesk_mcp/tools/`
3. Add `@server.tool()` decorated async function
4. Import and call `register_*_tools()` in `server.py`
