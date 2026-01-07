# Remote Attachment Handling Proposal

## Problem Statement

The current attachment tools (`download_attachment_to_disk`, `download_and_extract_attachment`) assume the MCP server runs locally with shared filesystem access. They download files to `/tmp/zendesk-attachments/` and expect the client (Claude) to read them directly via `Read`, `Grep`, and `Glob` tools.

When the server runs remotely over HTTP (SSE or streamable HTTP transport), the client cannot access the server's filesystem. We need tools that:
1. Store attachments server-side
2. Provide remote querying capabilities for those stored files
3. Allow reading file contents through the MCP protocol

## Design Goals

1. **Transport-aware tool registration** - Register different tool sets for stdio vs HTTP modes
2. **Familiar interface** - Remote tools should mirror local file operations (list, read, search, glob)
3. **Efficient token usage** - Support pagination, filtering, and partial reads to avoid overwhelming context

## Proposed Architecture

### Tool Registration Changes

Modify `register_attachments_tools()` to accept a `remote_mode` parameter:

```python
def register_attachments_tools(
    mcp: FastMCP,
    client: ZendeskClient,
    enable_write_tools: bool = False,
    remote_mode: bool = False,  # NEW: True when running HTTP transport
) -> None:
```

In `server.py`, pass the transport mode:

```python
# Determine if we're in remote mode
remote_mode = use_http  # or could be a separate flag

register_attachments_tools(mcp, zendesk_client, write_enabled, remote_mode)
```

### Storage Strategy

Use attachment ID as both cache key and directory structure. No in-memory mappings needed - just check filesystem.

```
$ZENDESK_ATTACHMENT_CACHE_DIR/   (or /tmp/zendesk-attachments/ if not set)
└── {attachment_id}/
    ├── metadata.json            # filename, size, content_type, content_url
    ├── original/
    │   └── {filename}           # the downloaded file
    └── extracted/               # only if archive was extracted
        └── ...files...
```

```python
# python/zendesk_mcp/attachment_store.py

def get_cache_dir() -> Path:
    """Get cache directory from env var or fall back to temp."""
    env_dir = os.getenv("ZENDESK_ATTACHMENT_CACHE_DIR")
    if env_dir:
        path = Path(env_dir)
    else:
        path = Path(tempfile.gettempdir()) / "zendesk-attachments"
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_attachment_dir(attachment_id: int) -> Path:
    """Get the directory for a specific attachment."""
    return get_cache_dir() / str(attachment_id)

def is_cached(attachment_id: int) -> bool:
    """Check if attachment is already downloaded."""
    return (get_attachment_dir(attachment_id) / "metadata.json").exists()

def is_extracted(attachment_id: int) -> bool:
    """Check if attachment is already extracted."""
    return (get_attachment_dir(attachment_id) / "extracted").is_dir()

def store_attachment(attachment_id: int, content: bytes, filename: str,
                     content_type: str, content_url: str) -> dict:
    """Store attachment to cache directory."""

def extract_attachment(attachment_id: int) -> dict:
    """Extract archived attachment. Returns extraction info."""

def list_files(attachment_id: int, pattern: str = "*") -> list[dict]:
    """List files in attachment directory matching glob pattern."""

def read_file(attachment_id: int, path: str, offset: int = 0,
              limit: int = 2000) -> dict:
    """Read file contents with pagination. Path is relative to attachment dir."""

def search_files(attachment_id: int, pattern: str, glob: str = "*") -> list[dict]:
    """Search file contents with regex."""

def delete_attachment(attachment_id: int) -> bool:
    """Delete cached attachment."""
```

### Proposed Tools

#### Tools for BOTH modes (unchanged)

| Tool | Description |
|------|-------------|
| `get_attachment` | Get attachment metadata by ID (includes content_url) |

#### Tools for STDIO mode only (current behavior)

| Tool | Description |
|------|-------------|
| `download_attachment` | Download and return base64 content |
| `download_attachment_to_disk` | Download to local `/tmp/zendesk-attachments/` |
| `download_and_extract_attachment` | Download and extract archives locally |

#### Tools for HTTP mode only (NEW)

| Tool | Description |
|------|-------------|
| `store_attachment` | Download attachment by ID and cache server-side |
| `store_and_extract_attachment` | Download and extract archive by attachment ID |
| `list_attachment_files` | List files in a cached attachment (supports glob patterns) |
| `read_attachment_file` | Read contents of a file within a cached attachment |
| `search_attachment_files` | Search file contents with regex within a cached attachment |
| `delete_cached_attachment` | Delete a cached attachment by ID |

### Tool Specifications

#### `store_attachment`

```python
@mcp.tool()
async def store_attachment(
    attachment_id: int,
) -> str:
    """Download a Zendesk attachment and cache it on the server.

    Args:
        attachment_id: The attachment ID from get_attachment or list_ticket_comments

    Returns:
        JSON with cached file info
    """
```

Response:
```json
{
  "attachment_id": 12345,
  "filename": "logs.tar.gz",
  "size": 1048576,
  "content_type": "application/gzip",
  "from_cache": false
}
```

When already cached:
```json
{
  "attachment_id": 12345,
  "filename": "logs.tar.gz",
  "size": 1048576,
  "content_type": "application/gzip",
  "from_cache": true
}
```

#### `store_and_extract_attachment`

```python
@mcp.tool()
async def store_and_extract_attachment(
    attachment_id: int,
) -> str:
    """Download and extract an archive attachment, caching all files on the server.

    Args:
        attachment_id: The attachment ID from get_attachment or list_ticket_comments

    Returns:
        JSON with extraction results including list of extracted files
    """
```

Response:
```json
{
  "attachment_id": 12345,
  "filename": "logs.tar.gz",
  "file_count": 47,
  "files": [
    {"path": "app.log", "size": 52000},
    {"path": "error.log", "size": 8500},
    {"path": "logs/debug.log", "size": 120000}
  ],
  "from_cache": false
}
```

When already downloaded and extracted:
```json
{
  "attachment_id": 12345,
  "filename": "logs.tar.gz",
  "file_count": 47,
  "files": [
    {"path": "app.log", "size": 52000},
    {"path": "error.log", "size": 8500}
  ],
  "from_cache": true
}
```

#### `list_attachment_files`

```python
@mcp.tool()
async def list_attachment_files(
    attachment_id: int,
    pattern: str = "**/*",
) -> str:
    """List files in a cached attachment.

    Args:
        attachment_id: The attachment ID
        pattern: Glob pattern to filter files (e.g., "*.log", "**/*.py")

    Returns:
        JSON array of file info objects
    """
```

Response:
```json
{
  "attachment_id": 12345,
  "files": [
    {"path": "app.log", "size": 52000, "type": "file"},
    {"path": "logs/", "type": "directory"},
    {"path": "logs/debug.log", "size": 120000, "type": "file"}
  ],
  "total": 3
}
```

#### `read_attachment_file`

```python
@mcp.tool()
async def read_attachment_file(
    attachment_id: int,
    path: str,
    offset: int = 0,
    limit: int = 2000,
) -> str:
    """Read contents of a file within a cached attachment.

    Args:
        attachment_id: The attachment ID
        path: Relative path within the attachment (from list_attachment_files)
        offset: Line number to start from (0-indexed)
        limit: Maximum number of lines to return (default 2000)

    Returns:
        File contents with line numbers, or base64 for binary files
    """
```

Response (text):
```json
{
  "attachment_id": 12345,
  "path": "app.log",
  "content": "1\t2024-01-05 10:00:00 INFO Starting application\n2\t2024-01-05 10:00:01 INFO Connected to database\n...",
  "lines_returned": 2000,
  "total_lines": 5000,
  "has_more": true
}
```

Response (binary):
```json
{
  "attachment_id": 12345,
  "path": "screenshot.png",
  "content_base64": "iVBORw0KGgo...",
  "size": 15000,
  "content_type": "image/png"
}
```

#### `search_attachment_files`

```python
@mcp.tool()
async def search_attachment_files(
    attachment_id: int,
    pattern: str,
    glob: str = "*",
    context_lines: int = 2,
    max_results: int = 100,
) -> str:
    """Search for pattern in files within a cached attachment (like grep).

    Args:
        attachment_id: The attachment ID
        pattern: Regex pattern to search for
        glob: File pattern to search within (e.g., "*.log")
        context_lines: Lines of context around matches
        max_results: Maximum matches to return

    Returns:
        JSON with matching lines and context
    """
```

Response:
```json
{
  "attachment_id": 12345,
  "matches": [
    {
      "path": "app.log",
      "line": 142,
      "content": "2024-01-05 10:05:23 ERROR Connection refused",
      "context_before": ["2024-01-05 10:05:22 INFO Attempting reconnect"],
      "context_after": ["2024-01-05 10:05:24 INFO Retry 1 of 3"]
    }
  ],
  "total_matches": 15,
  "files_searched": 3,
  "truncated": false
}
```

#### `delete_cached_attachment`

```python
@mcp.tool()
async def delete_cached_attachment(
    attachment_id: int,
) -> str:
    """Delete a cached attachment to free up space.

    Args:
        attachment_id: The attachment ID to delete

    Returns:
        JSON with deletion result
    """
```

Response:
```json
{
  "attachment_id": 12345,
  "deleted": true
}
```

## Implementation Plan

### Phase 1: Core Infrastructure
1. Create `attachment_store.py` module with filesystem-based caching functions
2. Add `remote_mode` parameter to `register_attachments_tools()`
3. Implement `store_attachment` - check if `{cache_dir}/{attachment_id}/` exists, return cached if so
4. Implement `store_and_extract_attachment` - check for `extracted/` subdirectory

### Phase 2: Query Tools
5. Implement `list_attachment_files` with glob support
6. Implement `read_attachment_file` with line-based pagination
7. Implement `search_attachment_files` with regex

### Phase 3: Cleanup
8. Implement `delete_cached_attachment`

### Phase 4: Testing & Documentation
9. Add tests for attachment caching behavior
10. Update CLAUDE.md with remote attachment workflow

## Design Decisions

1. **Attachment ID as cache key**: Use attachment ID as directory name. No in-memory mapping - just check if `{cache_dir}/{attachment_id}/metadata.json` exists.

2. **Shared storage**: All connections share the same cache directory. Enables caching across requests and server restarts.

3. **Configurable cache directory**: `ZENDESK_ATTACHMENT_CACHE_DIR` env var, falls back to `/tmp/zendesk-attachments/`.

4. **No session management**: Deferred - files persist until manually deleted or cache directory cleared.

5. **No storage limits**: Deferred for now.

6. **STDIO mode unchanged**: Keep existing local filesystem tools (`download_attachment`, `download_attachment_to_disk`, `download_and_extract_attachment`).

7. **`download_attachment` (base64) is STDIO-only**: Doesn't work well over HTTP transport.
