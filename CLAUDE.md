# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that provides comprehensive access to the Zendesk API. It exposes Zendesk functionality as MCP tools and resources for AI assistants to interact with Zendesk Support, Talk, Chat, and Guide products.

## Development Commands

### Running the Server
- `npm start` - Start the MCP server
- `npm run dev` - Start with auto-restart (uses Node's --watch flag)
- `npm run inspect` - Test the server with MCP Inspector

### Configuration
The server requires environment variables in a `.env` file:
- Domain: Either `ZENDESK_SUBDOMAIN` (e.g., "mycompany") or `ZENDESK_DOMAIN` (e.g., "mycompany.zendesk.com")
- Authentication: `ZENDESK_EMAIL` plus either `ZENDESK_API_TOKEN` (recommended) or `ZENDESK_PASSWORD`

## Architecture

### Core Components

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

## Key Implementation Details

- This is an ES module project (`"type": "module"` in package.json)
- The server communicates via stdio using JSON-RPC
- All Zendesk API responses are returned as stringified JSON to the MCP client
- The Zendesk client automatically wraps request bodies in the appropriate key (e.g., `{ ticket: data }`)
- Authentication uses HTTP Basic Auth with either `email/token:api_token` or `email:password`
- Attachments are downloaded to `/tmp/zendesk-attachments/` and persist for the session
