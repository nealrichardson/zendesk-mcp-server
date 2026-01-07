"""Tests for the attachment store module."""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from zendesk_mcp import attachment_store


@pytest.fixture
def temp_cache_dir(tmp_path, monkeypatch):
    """Create a temporary cache directory and configure the env var."""
    cache_dir = tmp_path / "zendesk-attachments"
    cache_dir.mkdir()
    monkeypatch.setenv("ZENDESK_ATTACHMENT_CACHE_DIR", str(cache_dir))
    yield cache_dir


@pytest.fixture
def sample_attachment(temp_cache_dir):
    """Store a sample text attachment."""
    attachment_id = 12345
    content = b"line 1\nline 2\nline 3\nline 4\nline 5"
    metadata = attachment_store.store_attachment(
        attachment_id=attachment_id,
        content=content,
        filename="sample.txt",
        content_type="text/plain",
        content_url="https://example.com/attachments/12345/sample.txt",
    )
    return attachment_id, metadata


@pytest.fixture
def sample_archive(temp_cache_dir):
    """Store a sample tar.gz archive and extract it."""
    import tarfile
    import io

    attachment_id = 67890

    # Create a tar.gz archive in memory
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add a text file
        content1 = b"This is file1 content\nwith multiple lines"
        file1 = tarfile.TarInfo(name="file1.txt")
        file1.size = len(content1)
        tar.addfile(file1, io.BytesIO(content1))

        # Add a log file
        content2 = b"2024-01-01 ERROR Something went wrong\n2024-01-01 INFO Normal log"
        file2 = tarfile.TarInfo(name="logs/app.log")
        file2.size = len(content2)
        tar.addfile(file2, io.BytesIO(content2))

        # Add another file
        content3 = b"Config value"
        file3 = tarfile.TarInfo(name="config/settings.conf")
        file3.size = len(content3)
        tar.addfile(file3, io.BytesIO(content3))

    tar_content = tar_buffer.getvalue()

    # Store the archive
    attachment_store.store_attachment(
        attachment_id=attachment_id,
        content=tar_content,
        filename="logs.tar.gz",
        content_type="application/gzip",
        content_url="https://example.com/attachments/67890/logs.tar.gz",
    )

    return attachment_id


class TestCacheDirectory:
    """Tests for cache directory management."""

    def test_get_cache_dir_from_env(self, temp_cache_dir):
        """Should return cache dir from environment variable."""
        result = attachment_store.get_cache_dir()
        assert result == temp_cache_dir

    def test_get_cache_dir_fallback(self, monkeypatch):
        """Should fall back to temp directory if env var not set."""
        monkeypatch.delenv("ZENDESK_ATTACHMENT_CACHE_DIR", raising=False)
        result = attachment_store.get_cache_dir()
        assert "zendesk-attachments" in str(result)
        assert result.exists()

    def test_get_attachment_dir(self, temp_cache_dir):
        """Should return correct path for attachment ID."""
        result = attachment_store.get_attachment_dir(12345)
        assert result == temp_cache_dir / "12345"


class TestStoreAttachment:
    """Tests for storing attachments."""

    def test_store_attachment_creates_directory(self, temp_cache_dir):
        """Should create attachment directory structure."""
        attachment_id = 11111
        content = b"test content"

        attachment_store.store_attachment(
            attachment_id=attachment_id,
            content=content,
            filename="test.txt",
            content_type="text/plain",
            content_url="https://example.com/test.txt",
        )

        attachment_dir = temp_cache_dir / "11111"
        assert attachment_dir.exists()
        assert (attachment_dir / "original").exists()
        assert (attachment_dir / "original" / "test.txt").exists()
        assert (attachment_dir / "metadata.json").exists()

    def test_store_attachment_returns_metadata(self, temp_cache_dir):
        """Should return correct metadata."""
        metadata = attachment_store.store_attachment(
            attachment_id=22222,
            content=b"test content",
            filename="test.txt",
            content_type="text/plain",
            content_url="https://example.com/test.txt",
        )

        assert metadata["attachment_id"] == 22222
        assert metadata["filename"] == "test.txt"
        assert metadata["size"] == 12
        assert metadata["content_type"] == "text/plain"
        assert metadata["content_url"] == "https://example.com/test.txt"

    def test_store_attachment_saves_metadata_json(self, temp_cache_dir):
        """Should save metadata to JSON file."""
        attachment_store.store_attachment(
            attachment_id=33333,
            content=b"test",
            filename="test.txt",
            content_type="text/plain",
            content_url="https://example.com/test.txt",
        )

        metadata_path = temp_cache_dir / "33333" / "metadata.json"
        with open(metadata_path) as f:
            saved_metadata = json.load(f)

        assert saved_metadata["attachment_id"] == 33333
        assert saved_metadata["filename"] == "test.txt"


class TestCacheChecks:
    """Tests for cache status checks."""

    def test_is_cached_true(self, sample_attachment):
        """Should return True for cached attachment."""
        attachment_id, _ = sample_attachment
        assert attachment_store.is_cached(attachment_id) is True

    def test_is_cached_false(self, temp_cache_dir):
        """Should return False for non-cached attachment."""
        assert attachment_store.is_cached(99999) is False

    def test_is_extracted_false_before_extraction(self, sample_attachment):
        """Should return False before extraction."""
        attachment_id, _ = sample_attachment
        assert attachment_store.is_extracted(attachment_id) is False

    def test_get_metadata(self, sample_attachment):
        """Should return stored metadata."""
        attachment_id, _ = sample_attachment
        metadata = attachment_store.get_metadata(attachment_id)

        assert metadata["attachment_id"] == attachment_id
        assert metadata["filename"] == "sample.txt"

    def test_get_metadata_not_found(self, temp_cache_dir):
        """Should return None for non-cached attachment."""
        result = attachment_store.get_metadata(99999)
        assert result is None


class TestExtractAttachment:
    """Tests for archive extraction."""

    @pytest.mark.asyncio
    async def test_extract_tar_gz(self, sample_archive):
        """Should extract tar.gz archive."""
        result = await attachment_store.extract_attachment(sample_archive)

        assert result["attachment_id"] == sample_archive
        assert result["extracted"] is True
        # At least 2 files (some tarballs don't create intermediate dirs as separate entries)
        assert result["file_count"] >= 2

    @pytest.mark.asyncio
    async def test_extract_non_archive(self, sample_attachment):
        """Should return extracted=False for non-archive."""
        attachment_id, _ = sample_attachment
        result = await attachment_store.extract_attachment(attachment_id)

        assert result["extracted"] is False
        assert "not an archive" in result.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_extract_not_found(self, temp_cache_dir):
        """Should raise error for non-cached attachment."""
        with pytest.raises(ValueError, match="not found"):
            await attachment_store.extract_attachment(99999)

    @pytest.mark.asyncio
    async def test_is_extracted_true_after_extraction(self, sample_archive):
        """Should return True after extraction."""
        await attachment_store.extract_attachment(sample_archive)
        assert attachment_store.is_extracted(sample_archive) is True


class TestListFiles:
    """Tests for listing files."""

    def test_list_files_original(self, sample_attachment):
        """Should list files in original directory."""
        attachment_id, _ = sample_attachment
        files = attachment_store.list_files(attachment_id)

        assert len(files) == 1
        assert files[0]["path"] == "sample.txt"
        assert files[0]["type"] == "file"

    @pytest.mark.asyncio
    async def test_list_files_extracted(self, sample_archive):
        """Should list files in extracted directory."""
        await attachment_store.extract_attachment(sample_archive)
        files = attachment_store.list_files(sample_archive)

        paths = [f["path"] for f in files if f["type"] == "file"]
        assert "file1.txt" in paths
        assert "logs/app.log" in paths
        assert "config/settings.conf" in paths

    @pytest.mark.asyncio
    async def test_list_files_with_glob_pattern(self, sample_archive):
        """Should filter files by glob pattern."""
        await attachment_store.extract_attachment(sample_archive)
        files = attachment_store.list_files(sample_archive, "*.txt")

        paths = [f["path"] for f in files if f["type"] == "file"]
        assert "file1.txt" in paths
        assert "logs/app.log" not in paths

    @pytest.mark.asyncio
    async def test_list_files_with_recursive_glob(self, sample_archive):
        """Should filter files with recursive glob pattern."""
        await attachment_store.extract_attachment(sample_archive)
        files = attachment_store.list_files(sample_archive, "**/*.log")

        paths = [f["path"] for f in files if f["type"] == "file"]
        assert "logs/app.log" in paths
        assert len([p for p in paths if p.endswith(".log")]) == 1

    def test_list_files_not_found(self, temp_cache_dir):
        """Should raise error for non-cached attachment."""
        with pytest.raises(ValueError, match="not found"):
            attachment_store.list_files(99999)


class TestReadFile:
    """Tests for reading file contents."""

    def test_read_file_text(self, sample_attachment):
        """Should read text file with line numbers."""
        attachment_id, _ = sample_attachment
        result = attachment_store.read_file(attachment_id, "sample.txt")

        assert result["attachment_id"] == attachment_id
        assert result["path"] == "sample.txt"
        assert "1\tline 1" in result["content"]
        assert "5\tline 5" in result["content"]
        assert result["total_lines"] == 5

    def test_read_file_with_offset(self, sample_attachment):
        """Should read file starting at offset."""
        attachment_id, _ = sample_attachment
        result = attachment_store.read_file(attachment_id, "sample.txt", offset=2)

        # Should start at line 3 (0-indexed offset of 2)
        assert "3\tline 3" in result["content"]
        assert "1\tline 1" not in result["content"]

    def test_read_file_with_limit(self, sample_attachment):
        """Should limit number of lines returned."""
        attachment_id, _ = sample_attachment
        result = attachment_store.read_file(attachment_id, "sample.txt", limit=2)

        assert result["lines_returned"] == 2
        assert result["has_more"] is True
        assert "3\tline 3" not in result["content"]

    def test_read_file_not_found(self, sample_attachment):
        """Should raise error for non-existent file."""
        attachment_id, _ = sample_attachment
        with pytest.raises(ValueError, match="not found"):
            attachment_store.read_file(attachment_id, "nonexistent.txt")

    def test_read_attachment_not_found(self, temp_cache_dir):
        """Should raise error for non-cached attachment."""
        with pytest.raises(ValueError, match="not found"):
            attachment_store.read_file(99999, "any.txt")


class TestSearchFiles:
    """Tests for searching file contents."""

    @pytest.mark.asyncio
    async def test_search_files_finds_matches(self, sample_archive):
        """Should find matches with regex pattern."""
        await attachment_store.extract_attachment(sample_archive)
        result = attachment_store.search_files(sample_archive, "ERROR")

        assert result["attachment_id"] == sample_archive
        assert len(result["matches"]) > 0
        assert result["total_matches"] > 0

        # Check match structure
        match = result["matches"][0]
        assert "path" in match
        assert "line" in match
        assert "content" in match
        assert "ERROR" in match["content"]

    @pytest.mark.asyncio
    async def test_search_files_with_glob_filter(self, sample_archive):
        """Should filter search to matching files."""
        await attachment_store.extract_attachment(sample_archive)
        result = attachment_store.search_files(sample_archive, "content", glob="*.txt")

        # Should only search .txt files
        paths = {m["path"] for m in result["matches"]}
        assert all(p.endswith(".txt") for p in paths)

    @pytest.mark.asyncio
    async def test_search_files_with_context(self, sample_archive):
        """Should include context lines."""
        await attachment_store.extract_attachment(sample_archive)
        result = attachment_store.search_files(sample_archive, "ERROR", context_lines=1)

        match = result["matches"][0]
        assert "context_before" in match
        assert "context_after" in match

    @pytest.mark.asyncio
    async def test_search_files_max_results(self, sample_archive):
        """Should limit results to max_results."""
        await attachment_store.extract_attachment(sample_archive)
        result = attachment_store.search_files(sample_archive, ".", max_results=1)

        assert len(result["matches"]) <= 1
        if result["total_matches"] > 1:
            assert result["truncated"] is True

    def test_search_files_invalid_regex(self, sample_attachment):
        """Should raise error for invalid regex."""
        attachment_id, _ = sample_attachment
        with pytest.raises(ValueError, match="Invalid regex"):
            attachment_store.search_files(attachment_id, "[invalid")


class TestDeleteAttachment:
    """Tests for deleting cached attachments."""

    def test_delete_attachment(self, sample_attachment, temp_cache_dir):
        """Should delete cached attachment."""
        attachment_id, _ = sample_attachment

        # Verify it exists
        assert attachment_store.is_cached(attachment_id)

        # Delete it
        result = attachment_store.delete_attachment(attachment_id)

        assert result is True
        assert attachment_store.is_cached(attachment_id) is False
        assert not (temp_cache_dir / str(attachment_id)).exists()

    def test_delete_attachment_not_found(self, temp_cache_dir):
        """Should return False for non-cached attachment."""
        result = attachment_store.delete_attachment(99999)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_extracted_attachment(self, sample_archive, temp_cache_dir):
        """Should delete extracted attachment including all files."""
        await attachment_store.extract_attachment(sample_archive)

        # Verify extraction exists
        assert attachment_store.is_extracted(sample_archive)

        # Delete it
        result = attachment_store.delete_attachment(sample_archive)

        assert result is True
        assert not (temp_cache_dir / str(sample_archive)).exists()
