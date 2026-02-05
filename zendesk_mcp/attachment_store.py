"""Attachment store for caching attachments server-side in HTTP mode.

This module provides filesystem-based caching for attachments when running
in HTTP/remote mode where the client cannot access the server's filesystem.
"""

import asyncio
import fnmatch
import json
import mimetypes
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


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


def get_metadata(attachment_id: int) -> dict[str, Any] | None:
    """Get cached metadata for an attachment."""
    metadata_path = get_attachment_dir(attachment_id) / "metadata.json"
    if metadata_path.exists():
        return json.loads(metadata_path.read_text())
    return None


async def download_and_store_attachment(
    attachment_id: int,
    content_url: str,
    filename: str,
    content_type: str,
) -> dict[str, Any]:
    """Download attachment and stream directly to cache directory.

    Args:
        attachment_id: The Zendesk attachment ID
        content_url: URL to download from (pre-signed, no auth needed)
        filename: Original filename
        content_type: MIME content type

    Returns:
        dict with cached file info
    """
    import httpx

    attachment_dir = get_attachment_dir(attachment_id)
    attachment_dir.mkdir(parents=True, exist_ok=True)

    # Create original subdirectory
    original_dir = attachment_dir / "original"
    original_dir.mkdir(exist_ok=True)

    file_path = original_dir / filename
    size = 0

    # Stream directly to disk
    async with httpx.AsyncClient(follow_redirects=True) as client:
        async with client.stream("GET", content_url) as response:
            response.raise_for_status()
            with open(file_path, "wb") as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
                    size += len(chunk)

    # Write metadata
    metadata = {
        "attachment_id": attachment_id,
        "filename": filename,
        "size": size,
        "content_type": content_type,
        "content_url": content_url,
    }
    metadata_path = attachment_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return metadata


def store_attachment(
    attachment_id: int,
    content: bytes,
    filename: str,
    content_type: str,
    content_url: str,
) -> dict[str, Any]:
    """Store attachment bytes to cache directory.

    Args:
        attachment_id: The Zendesk attachment ID
        content: The raw file content bytes
        filename: Original filename
        content_type: MIME content type
        content_url: Original content URL

    Returns:
        dict with cached file info
    """
    attachment_dir = get_attachment_dir(attachment_id)
    attachment_dir.mkdir(parents=True, exist_ok=True)

    # Create original subdirectory
    original_dir = attachment_dir / "original"
    original_dir.mkdir(exist_ok=True)

    # Write the file
    file_path = original_dir / filename
    file_path.write_bytes(content)

    # Write metadata
    metadata = {
        "attachment_id": attachment_id,
        "filename": filename,
        "size": len(content),
        "content_type": content_type,
        "content_url": content_url,
    }
    metadata_path = attachment_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return metadata


async def extract_attachment(attachment_id: int) -> dict[str, Any]:
    """Extract archived attachment. Returns extraction info.

    Args:
        attachment_id: The Zendesk attachment ID

    Returns:
        dict with extraction results including file list
    """
    attachment_dir = get_attachment_dir(attachment_id)
    metadata = get_metadata(attachment_id)

    if not metadata:
        raise ValueError(f"Attachment {attachment_id} not found in cache")

    filename = metadata["filename"]
    original_dir = attachment_dir / "original"
    file_path = original_dir / filename

    if not file_path.exists():
        raise ValueError(f"Original file not found for attachment {attachment_id}")

    # Check if it's an archive that should be extracted
    archive_pattern = re.compile(r"\.(tar|tar\.gz|tgz|tar\.bz2|tbz2|zip)$", re.IGNORECASE)
    is_archive = archive_pattern.search(filename)

    if not is_archive:
        return {
            "attachment_id": attachment_id,
            "filename": filename,
            "extracted": False,
            "message": "File is not an archive",
        }

    # Create extraction directory
    extract_dir = attachment_dir / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    # Extract based on file type
    if re.search(r"\.zip$", filename, re.IGNORECASE):
        extract_command = f'unzip -q "{file_path}" -d "{extract_dir}"'
    elif re.search(r"\.(tar\.gz|tgz)$", filename, re.IGNORECASE):
        extract_command = f'tar -xzf "{file_path}" -C "{extract_dir}"'
    elif re.search(r"\.(tar\.bz2|tbz2)$", filename, re.IGNORECASE):
        extract_command = f'tar -xjf "{file_path}" -C "{extract_dir}"'
    elif re.search(r"\.tar$", filename, re.IGNORECASE):
        extract_command = f'tar -xf "{file_path}" -C "{extract_dir}"'
    else:
        return {
            "attachment_id": attachment_id,
            "filename": filename,
            "extracted": False,
            "message": "Unsupported archive format",
        }

    proc = await asyncio.create_subprocess_shell(
        extract_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise ValueError(f"Extraction failed: {stderr.decode()}")

    # Get list of extracted files
    files = list_files(attachment_id, "**/*")

    return {
        "attachment_id": attachment_id,
        "filename": filename,
        "file_count": len([f for f in files if f["type"] == "file"]),
        "files": files,
        "extracted": True,
    }


def list_files(attachment_id: int, pattern: str = "**/*") -> list[dict[str, Any]]:
    """List files in attachment directory matching glob pattern.

    Args:
        attachment_id: The Zendesk attachment ID
        pattern: Glob pattern to filter files (e.g., "*.log", "**/*.py")

    Returns:
        List of file info dicts with path, size, type
    """
    attachment_dir = get_attachment_dir(attachment_id)

    if not attachment_dir.exists():
        raise ValueError(f"Attachment {attachment_id} not found in cache")

    # Determine which directory to search
    extracted_dir = attachment_dir / "extracted"
    original_dir = attachment_dir / "original"

    if extracted_dir.exists():
        search_dir = extracted_dir
    elif original_dir.exists():
        search_dir = original_dir
    else:
        return []

    files = []

    # Use Path.glob for pattern matching (supports ** for recursive)
    for path in search_dir.glob(pattern):
        # Get relative path from search directory
        rel_path = path.relative_to(search_dir)

        file_info: dict[str, Any] = {
            "path": str(rel_path),
            "type": "directory" if path.is_dir() else "file",
        }

        if path.is_file():
            file_info["size"] = path.stat().st_size

        files.append(file_info)

    # Sort by path
    files.sort(key=lambda f: f["path"])
    return files


def read_file(
    attachment_id: int, path: str, offset: int = 0, limit: int = 2000
) -> dict[str, Any]:
    """Read file contents with pagination.

    Args:
        attachment_id: The Zendesk attachment ID
        path: Relative path within the attachment directory
        offset: Line number to start from (0-indexed)
        limit: Maximum number of lines to return

    Returns:
        dict with file content, line info, and metadata
    """
    attachment_dir = get_attachment_dir(attachment_id)

    if not attachment_dir.exists():
        raise ValueError(f"Attachment {attachment_id} not found in cache")

    # Determine which directory to search
    extracted_dir = attachment_dir / "extracted"
    original_dir = attachment_dir / "original"

    if extracted_dir.exists():
        search_dir = extracted_dir
    elif original_dir.exists():
        search_dir = original_dir
    else:
        raise ValueError(f"No files found for attachment {attachment_id}")

    file_path = search_dir / path

    if not file_path.exists():
        raise ValueError(f"File not found: {path}")

    if file_path.is_dir():
        raise ValueError(f"Cannot read directory: {path}")

    # Check if binary file
    mime_type, _ = mimetypes.guess_type(str(file_path))
    is_text = mime_type is None or mime_type.startswith("text/") or mime_type in (
        "application/json",
        "application/xml",
        "application/javascript",
        "application/x-sh",
        "application/x-python",
    )

    if not is_text:
        # Return binary content as base64
        import base64

        content = file_path.read_bytes()
        return {
            "attachment_id": attachment_id,
            "path": path,
            "content_base64": base64.b64encode(content).decode(),
            "size": len(content),
            "content_type": mime_type or "application/octet-stream",
        }

    # Read text file with line pagination
    try:
        lines = file_path.read_text(errors="replace").splitlines()
    except Exception as e:
        raise ValueError(f"Error reading file: {e}") from e

    total_lines = len(lines)
    selected_lines = lines[offset : offset + limit]

    # Format with line numbers (1-indexed for display)
    content_lines = []
    for i, line in enumerate(selected_lines, start=offset + 1):
        content_lines.append(f"{i}\t{line}")

    return {
        "attachment_id": attachment_id,
        "path": path,
        "content": "\n".join(content_lines),
        "lines_returned": len(selected_lines),
        "total_lines": total_lines,
        "has_more": offset + limit < total_lines,
    }


def search_files(
    attachment_id: int,
    pattern: str,
    glob: str = "*",
    context_lines: int = 2,
    max_results: int = 100,
) -> dict[str, Any]:
    """Search file contents with regex.

    Args:
        attachment_id: The Zendesk attachment ID
        pattern: Regex pattern to search for
        glob: File pattern to search within (e.g., "*.log")
        context_lines: Lines of context around matches
        max_results: Maximum matches to return

    Returns:
        dict with matches and search metadata
    """
    attachment_dir = get_attachment_dir(attachment_id)

    if not attachment_dir.exists():
        raise ValueError(f"Attachment {attachment_id} not found in cache")

    # Determine which directory to search
    extracted_dir = attachment_dir / "extracted"
    original_dir = attachment_dir / "original"

    if extracted_dir.exists():
        search_dir = extracted_dir
    elif original_dir.exists():
        search_dir = original_dir
    else:
        raise ValueError(f"No files found for attachment {attachment_id}")

    # Compile regex
    try:
        regex = re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e

    matches = []
    files_searched = 0
    total_matches = 0

    for file_path in search_dir.rglob("*"):
        if not file_path.is_file():
            continue

        rel_path = str(file_path.relative_to(search_dir))

        # Apply glob filter
        if not fnmatch.fnmatch(rel_path, glob):
            continue

        # Skip binary files
        mime_type, _ = mimetypes.guess_type(str(file_path))
        is_text = mime_type is None or mime_type.startswith("text/") or mime_type in (
            "application/json",
            "application/xml",
            "application/javascript",
            "application/x-sh",
            "application/x-python",
        )

        if not is_text:
            continue

        files_searched += 1

        try:
            lines = file_path.read_text(errors="replace").splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines):
            if regex.search(line):
                total_matches += 1

                if len(matches) < max_results:
                    # Get context
                    context_before = lines[max(0, i - context_lines) : i]
                    context_after = lines[i + 1 : i + 1 + context_lines]

                    matches.append({
                        "path": rel_path,
                        "line": i + 1,  # 1-indexed
                        "content": line,
                        "context_before": context_before,
                        "context_after": context_after,
                    })

    return {
        "attachment_id": attachment_id,
        "matches": matches,
        "total_matches": total_matches,
        "files_searched": files_searched,
        "truncated": total_matches > max_results,
    }


def delete_attachment(attachment_id: int) -> bool:
    """Delete cached attachment.

    Args:
        attachment_id: The Zendesk attachment ID to delete

    Returns:
        True if deleted, False if not found
    """
    attachment_dir = get_attachment_dir(attachment_id)

    if not attachment_dir.exists():
        return False

    shutil.rmtree(attachment_dir)
    return True
