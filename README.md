# Zendesk MCP Server

A Model Context Protocol (MCP) server for interacting with the Zendesk API.

This project was originally forked from [mattcoatsworth/zendesk-mcp-server](https://github.com/mattcoatsworth/zendesk-mcp-server) and reimplemented in Python.

## Features

- Full Zendesk API coverage (Support, Talk, Chat, Guide/Help Center)
- Supports both stdio and HTTP/SSE transports
- Async implementation using httpx
- Type-safe with Pydantic

## Installation

### Run directly from GitHub (no install)

```bash
uvx --from "git+https://github.com/nealrichardson/zendesk-mcp-server" zendesk-mcp
```

### Local installation

Using uv (recommended):

```bash
uv sync
```

Or with pip:

```bash
pip install -e .
```

## Configuration

Copy `.env.example` to `.env` and add your Zendesk credentials:

```env
# Domain: Either subdomain OR full domain
ZENDESK_SUBDOMAIN=mycompany
# OR
ZENDESK_DOMAIN=mycompany.zendesk.com

# Authentication
ZENDESK_EMAIL=user@example.com
ZENDESK_API_TOKEN=your_api_token

# Optional: Transport configuration
MCP_TRANSPORT=stdio  # or "http"
MCP_HTTP_HOST=0.0.0.0
MCP_HTTP_PORT=8000
```

### Posit Connect

When deployed on [Posit Connect](https://posit.co/products/enterprise/connect/), the server can use a Zendesk OAuth integration instead of API tokens. Configure a Zendesk OAuth app in Connect, and the server will automatically pick up credentials from the logged-in user's OAuth session. No `ZENDESK_API_TOKEN` or `ZENDESK_EMAIL` environment variables are needed in this case.

## Usage

### Stdio Mode (default)

```bash
# Using uv
uv run python -m zendesk_mcp

# Or if installed
zendesk-mcp
```

### HTTP/SSE Mode

```bash
# Using uv
uv run python -m zendesk_mcp --http

# With custom host/port
uv run python -m zendesk_mcp --http --host 127.0.0.1 --port 3000

# Or if installed
zendesk-mcp --http
```

HTTP mode exposes:
- `GET /sse` - Server-Sent Events stream
- `POST /messages` - Client message endpoint

### VS Code

Use `MCP: Add Server...` from the command palette, or add this to `.vscode/mcp.json`:

```json
{
  "servers": {
    "zendesk": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/zendesk-mcp-server", "python", "-m", "zendesk_mcp"]
    }
  }
}
```

## Available Tools

### Tickets
- `list_tickets` - List tickets with pagination
- `get_ticket` - Get ticket by ID
- `create_ticket` - Create new ticket
- `update_ticket` - Update existing ticket
- `delete_ticket` - Delete ticket
- `list_ticket_comments` - List ticket comments with filtering

### Users
- `list_users` - List users
- `get_user` - Get user by ID
- `create_user` - Create new user
- `update_user` - Update existing user
- `delete_user` - Delete user

### Organizations
- `list_organizations` - List organizations
- `get_organization` - Get organization by ID
- `create_organization` - Create new organization
- `update_organization` - Update existing organization
- `delete_organization` - Delete organization

### Groups
- `list_groups` - List agent groups
- `get_group` - Get group by ID
- `create_group` - Create new group
- `update_group` - Update existing group
- `delete_group` - Delete group

### Macros
- `list_macros` - List macros
- `get_macro` - Get macro by ID
- `create_macro` - Create new macro
- `update_macro` - Update existing macro
- `delete_macro` - Delete macro

### Views
- `list_views` - List views
- `get_view` - Get view by ID
- `create_view` - Create new view
- `update_view` - Update existing view
- `delete_view` - Delete view

### Triggers
- `list_triggers` - List triggers
- `get_trigger` - Get trigger by ID
- `create_trigger` - Create new trigger
- `update_trigger` - Update existing trigger
- `delete_trigger` - Delete trigger

### Automations
- `list_automations` - List automations
- `get_automation` - Get automation by ID
- `create_automation` - Create new automation
- `update_automation` - Update existing automation
- `delete_automation` - Delete automation

### Search
- `search` - Search across Zendesk data

### Help Center
- `list_articles` - List Help Center articles
- `get_article` - Get article by ID
- `create_article` - Create new article
- `update_article` - Update existing article
- `delete_article` - Delete article

### Talk
- `get_talk_stats` - Get Zendesk Talk statistics

### Chat
- `list_chats` - List chat conversations

### Attachments
- `get_attachment` - Get attachment metadata
- `download_attachment` - Download attachment as base64
- `download_attachment_to_disk` - Download attachment to temp directory
- `download_and_extract_attachment` - Download and extract archives

## Development

```bash
# Install dev dependencies
uv sync

# Run the server
uv run python -m zendesk_mcp

# Run with HTTP transport
uv run python -m zendesk_mcp --http
```
