"""Attachment tools for Zendesk MCP Server."""

import asyncio
import base64
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP

from zendesk_mcp import attachment_store
from zendesk_mcp.zendesk_client import ZendeskClient


def register_attachments_tools(
    mcp: FastMCP,
    client: ZendeskClient,
    enable_write_tools: bool = False,
    remote_mode: bool = False,
) -> None:
    """Register attachment-related tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        client: The Zendesk client
        enable_write_tools: Whether to enable write operations
        remote_mode: When True, register remote-friendly tools instead of local filesystem tools
    """

    # get_attachment is available in both modes
    @mcp.tool()
    async def get_attachment(id: int) -> str:
        """Get attachment metadata by ID, including the download URL.

        Args:
            id: Attachment ID
        """
        try:
            result = await client.get_attachment(id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting attachment: {e}"

    # STDIO mode only tools (local filesystem access)
    if not remote_mode:

        @mcp.tool()
        async def download_attachment(content_url: str) -> str:
            """Download attachment content as base64-encoded data.

            Use get_attachment first to retrieve the content_url.

            Args:
                content_url: The content_url from the attachment metadata
            """
            try:
                result = await client.download_attachment(content_url)
                return json.dumps(
                    {
                        "message": "Attachment downloaded successfully",
                        "contentType": result["content_type"],
                        "size": result["size"],
                        "data": result["data"][:100] + "...",  # Preview only
                    },
                    indent=2,
                ) + "\n\nNote: Full base64 data is available but truncated in this preview."
            except Exception as e:
                return f"Error downloading attachment: {e}"

        @mcp.tool()
        async def download_attachment_to_disk(
            content_url: str,
            filename: str | None = None,
        ) -> str:
            """Download attachment and save to temporary directory on disk.

            Returns file path that can be read, searched, or extracted.
            Ideal for files that need analysis (logs, tarballs, etc.).

            Args:
                content_url: The content_url from the attachment metadata
                filename: Optional filename. If not provided, will be inferred from the URL
            """
            try:
                result = await client.download_attachment(content_url)

                # Create temp directory for zendesk attachments
                tmp_dir = Path(tempfile.gettempdir()) / "zendesk-attachments"
                tmp_dir.mkdir(parents=True, exist_ok=True)

                # Determine filename
                final_filename = filename
                if not final_filename:
                    try:
                        parsed = urlparse(content_url)
                        final_filename = os.path.basename(parsed.path)
                    except Exception:
                        # If URL parsing fails, generate a filename based on content type
                        ext = (result.get("content_type") or "application/octet-stream").split("/")[-1]
                        final_filename = f"attachment-{int(asyncio.get_event_loop().time() * 1000)}.{ext}"

                file_path = tmp_dir / final_filename

                # Write the file
                file_path.write_bytes(base64.b64decode(result["data"]))

                return json.dumps(
                    {
                        "message": "Attachment downloaded to disk",
                        "path": str(file_path),
                        "filename": final_filename,
                        "contentType": result["content_type"],
                        "size": result["size"],
                        "note": "You can now use Read, Grep, or other file tools to analyze this file",
                    },
                    indent=2,
                )
            except Exception as e:
                return f"Error downloading attachment to disk: {e}"

        @mcp.tool()
        async def download_and_extract_attachment(
            content_url: str,
            filename: str | None = None,
        ) -> str:
            """Download attachment and automatically extract if it's a tarball or zip file.

            Returns extraction directory path. Perfect for analyzing archived logs or code.

            Args:
                content_url: The content_url from the attachment metadata
                filename: Optional filename. If not provided, will be inferred from the URL
            """
            try:
                result = await client.download_attachment(content_url)

                # Create temp directory for zendesk attachments
                tmp_dir = Path(tempfile.gettempdir()) / "zendesk-attachments"
                tmp_dir.mkdir(parents=True, exist_ok=True)

                # Determine filename
                final_filename = filename
                if not final_filename:
                    try:
                        parsed = urlparse(content_url)
                        final_filename = os.path.basename(parsed.path)
                    except Exception:
                        ext = (result.get("content_type") or "application/octet-stream").split("/")[-1]
                        final_filename = f"attachment-{int(asyncio.get_event_loop().time() * 1000)}.{ext}"

                file_path = tmp_dir / final_filename

                # Write the file
                file_path.write_bytes(base64.b64decode(result["data"]))

                # Check if it's an archive that should be extracted
                archive_pattern = re.compile(r"\.(tar|tar\.gz|tgz|tar\.bz2|tbz2|zip)$", re.IGNORECASE)
                is_archive = archive_pattern.search(final_filename)

                if not is_archive:
                    return json.dumps(
                        {
                            "message": "Attachment downloaded (not an archive)",
                            "path": str(file_path),
                            "filename": final_filename,
                            "contentType": result["content_type"],
                            "size": result["size"],
                            "extracted": False,
                        },
                        indent=2,
                    )

                # Create extraction directory
                extract_dir = tmp_dir / f"extracted-{int(asyncio.get_event_loop().time() * 1000)}"
                extract_dir.mkdir(parents=True, exist_ok=True)

                # Extract based on file type
                if re.search(r"\.zip$", final_filename, re.IGNORECASE):
                    extract_command = f'unzip -q "{file_path}" -d "{extract_dir}"'
                elif re.search(r"\.(tar\.gz|tgz)$", final_filename, re.IGNORECASE):
                    extract_command = f'tar -xzf "{file_path}" -C "{extract_dir}"'
                elif re.search(r"\.(tar\.bz2|tbz2)$", final_filename, re.IGNORECASE):
                    extract_command = f'tar -xjf "{file_path}" -C "{extract_dir}"'
                elif re.search(r"\.tar$", final_filename, re.IGNORECASE):
                    extract_command = f'tar -xf "{file_path}" -C "{extract_dir}"'
                else:
                    extract_command = None

                if extract_command:
                    proc = await asyncio.create_subprocess_shell(
                        extract_command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await proc.communicate()

                # Count extracted files
                file_count = sum(1 for _ in extract_dir.rglob("*") if _.is_file())

                return json.dumps(
                    {
                        "message": "Attachment downloaded and extracted",
                        "archivePath": str(file_path),
                        "extractionPath": str(extract_dir),
                        "filename": final_filename,
                        "contentType": result["content_type"],
                        "size": result["size"],
                        "extracted": True,
                        "fileCount": file_count,
                        "note": "Use Read, Grep, or Glob tools on the extraction path to analyze contents",
                    },
                    indent=2,
                )
            except Exception as e:
                return f"Error downloading/extracting attachment: {e}"

    # HTTP/Remote mode tools (server-side caching)
    if remote_mode:

        @mcp.tool()
        async def store_attachment(attachment_id: int) -> str:
            """Download a Zendesk attachment and cache it on the server.

            Use get_attachment or list_ticket_comments first to get the attachment_id.

            Args:
                attachment_id: The attachment ID from get_attachment or list_ticket_comments
            """
            try:
                # Check if already cached
                if attachment_store.is_cached(attachment_id):
                    metadata = attachment_store.get_metadata(attachment_id)
                    if metadata:
                        return json.dumps(
                            {
                                "attachment_id": attachment_id,
                                "filename": metadata["filename"],
                                "size": metadata["size"],
                                "content_type": metadata["content_type"],
                                "from_cache": True,
                            },
                            indent=2,
                        )

                # Get attachment metadata from Zendesk
                attachment_info = await client.get_attachment(attachment_id)
                attachment = attachment_info.get("attachment", {})
                content_url = attachment.get("content_url")
                filename = attachment.get("file_name", f"attachment-{attachment_id}")
                content_type = attachment.get("content_type", "application/octet-stream")

                if not content_url:
                    return f"Error: No content_url found for attachment {attachment_id}"

                # Stream directly to disk
                metadata = await attachment_store.download_and_store_attachment(
                    attachment_id=attachment_id,
                    content_url=content_url,
                    filename=filename,
                    content_type=content_type,
                )

                return json.dumps(
                    {
                        "attachment_id": attachment_id,
                        "filename": metadata["filename"],
                        "size": metadata["size"],
                        "content_type": metadata["content_type"],
                        "from_cache": False,
                    },
                    indent=2,
                )
            except Exception as e:
                return f"Error storing attachment: {e}"

        @mcp.tool()
        async def store_and_extract_attachment(attachment_id: int) -> str:
            """Download and extract an archive attachment, caching all files on the server.

            Use get_attachment or list_ticket_comments first to get the attachment_id.

            Args:
                attachment_id: The attachment ID from get_attachment or list_ticket_comments
            """
            try:
                # Check if already extracted
                if attachment_store.is_extracted(attachment_id):
                    metadata = attachment_store.get_metadata(attachment_id)
                    files = attachment_store.list_files(attachment_id, "**/*")
                    file_list = [{"path": f["path"], "size": f.get("size")} for f in files if f["type"] == "file"]
                    return json.dumps(
                        {
                            "attachment_id": attachment_id,
                            "filename": metadata["filename"] if metadata else "unknown",
                            "file_count": len(file_list),
                            "files": file_list[:50],  # Limit to first 50 files
                            "from_cache": True,
                        },
                        indent=2,
                    )

                # If not cached at all, download first
                if not attachment_store.is_cached(attachment_id):
                    # Get attachment metadata from Zendesk
                    attachment_info = await client.get_attachment(attachment_id)
                    attachment = attachment_info.get("attachment", {})
                    content_url = attachment.get("content_url")
                    filename = attachment.get("file_name", f"attachment-{attachment_id}")
                    content_type = attachment.get("content_type", "application/octet-stream")

                    if not content_url:
                        return f"Error: No content_url found for attachment {attachment_id}"

                    # Stream directly to disk
                    await attachment_store.download_and_store_attachment(
                        attachment_id=attachment_id,
                        content_url=content_url,
                        filename=filename,
                        content_type=content_type,
                    )

                # Extract the attachment
                extraction_result = await attachment_store.extract_attachment(attachment_id)

                if not extraction_result.get("extracted"):
                    return json.dumps(
                        {
                            "attachment_id": attachment_id,
                            "filename": extraction_result.get("filename"),
                            "extracted": False,
                            "message": extraction_result.get("message", "File is not an archive"),
                            "from_cache": False,
                        },
                        indent=2,
                    )

                # Get file list
                files = extraction_result.get("files", [])
                file_list = [{"path": f["path"], "size": f.get("size")} for f in files if f["type"] == "file"]

                return json.dumps(
                    {
                        "attachment_id": attachment_id,
                        "filename": extraction_result.get("filename"),
                        "file_count": len(file_list),
                        "files": file_list[:50],  # Limit to first 50 files
                        "from_cache": False,
                    },
                    indent=2,
                )
            except Exception as e:
                return f"Error storing/extracting attachment: {e}"

        @mcp.tool()
        async def list_attachment_files(
            attachment_id: int,
            pattern: str = "**/*",
        ) -> str:
            """List files in a cached attachment.

            Args:
                attachment_id: The attachment ID
                pattern: Glob pattern to filter files (e.g., "*.log", "**/*.py")
            """
            try:
                files = attachment_store.list_files(attachment_id, pattern)

                return json.dumps(
                    {
                        "attachment_id": attachment_id,
                        "files": files,
                        "total": len(files),
                    },
                    indent=2,
                )
            except ValueError as e:
                return f"Error: {e}"
            except Exception as e:
                return f"Error listing files: {e}"

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
            """
            try:
                result = attachment_store.read_file(attachment_id, path, offset, limit)
                return json.dumps(result, indent=2)
            except ValueError as e:
                return f"Error: {e}"
            except Exception as e:
                return f"Error reading file: {e}"

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
            """
            try:
                result = attachment_store.search_files(
                    attachment_id, pattern, glob, context_lines, max_results
                )
                return json.dumps(result, indent=2)
            except ValueError as e:
                return f"Error: {e}"
            except Exception as e:
                return f"Error searching files: {e}"

        @mcp.tool()
        async def delete_cached_attachment(attachment_id: int) -> str:
            """Delete a cached attachment to free up space.

            Args:
                attachment_id: The attachment ID to delete
            """
            try:
                deleted = attachment_store.delete_attachment(attachment_id)
                return json.dumps(
                    {
                        "attachment_id": attachment_id,
                        "deleted": deleted,
                    },
                    indent=2,
                )
            except Exception as e:
                return f"Error deleting attachment: {e}"
