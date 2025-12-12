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
- `attachments.js` - Ticket attachment retrieval and download

## Adding New Tools

To add new Zendesk API functionality:

1. Add the API method to `ZendeskClient` in `src/zendesk-client.js`
2. Create or update a tool module in `src/tools/`
3. Follow the tool pattern (name, description, schema, handler)
4. Import and add to `allTools` array in `src/server.js`

## Key Implementation Details

- This is an ES module project (`"type": "module"` in package.json)
- The server communicates via stdio using JSON-RPC
- All Zendesk API responses are returned as stringified JSON to the MCP client
- The Zendesk client automatically wraps request bodies in the appropriate key (e.g., `{ ticket: data }`)
- Authentication uses HTTP Basic Auth with either `email/token:api_token` or `email:password`
