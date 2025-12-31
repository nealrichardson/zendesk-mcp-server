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

from zendesk_mcp.zendesk_client import ZendeskClient


def register_attachments_tools(mcp: FastMCP, client: ZendeskClient, enable_write_tools: bool = False) -> None:
    """Register attachment-related tools with the MCP server."""

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
