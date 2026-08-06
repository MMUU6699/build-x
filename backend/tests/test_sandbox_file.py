"""
Integration tests for sandbox file upload and download functionality.

Tests target DaytonaSandbox — the production sandbox implementation used
with Daytona Cloud. They hit a *running* sandbox API endpoint (set
SANDBOX_BASE_URL env var, otherwise tests are skipped).

To run against a live sandbox:
    SANDBOX_BASE_URL=http://localhost:8080 uv run pytest tests/test_sandbox_file.py
"""
import logging
import os
import io

import pytest

from app.infrastructure.external.sandbox.daytona_sandbox import DaytonaSandbox

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SANDBOX_BASE_URL = os.environ.get("SANDBOX_BASE_URL", "")


def _skip_if_no_sandbox():
    """Skip tests when no live sandbox URL is configured."""
    if not SANDBOX_BASE_URL:
        pytest.skip("SANDBOX_BASE_URL not set — skipping live sandbox tests")


@pytest.fixture
def sandbox_instance():
    """Create a DaytonaSandbox instance pointing at the configured endpoint."""
    _skip_if_no_sandbox()
    return DaytonaSandbox(
        sandbox_id="test-sandbox",
        base_url=SANDBOX_BASE_URL,
        vnc_url="",
        cdp_url="",
    )


@pytest.fixture
def sample_file_content():
    """Return sample bytes for upload/download tests."""
    return b"This is a test file content for sandbox testing."


@pytest.fixture
def sample_binary_stream(sample_file_content):
    """Wrap sample content in a BytesIO stream."""
    return io.BytesIO(sample_file_content)


@pytest.fixture
def temp_file_path():
    """Generate a unique temporary path inside the sandbox."""
    import secrets
    return f"/tmp/test_file_{secrets.token_hex(8)}.txt"


# ---------------------------------------------------------------------------
# Upload Tests
# ---------------------------------------------------------------------------

async def test_file_upload_success(sandbox_instance, sample_binary_stream, temp_file_path):
    """DaytonaSandbox: successful file upload returns success ToolResult."""
    result = await sandbox_instance.file_upload(
        file_data=sample_binary_stream,
        path=temp_file_path,
        filename="test_file.txt"
    )
    assert result.success is True
    assert "successfully" in result.message.lower()


async def test_file_upload_without_filename(sandbox_instance, sample_binary_stream, temp_file_path):
    """DaytonaSandbox: upload without explicit filename still succeeds."""
    result = await sandbox_instance.file_upload(
        file_data=sample_binary_stream,
        path=temp_file_path,
    )
    assert result.success is True


async def test_file_upload_large_file(sandbox_instance, temp_file_path):
    """DaytonaSandbox: 1 MB upload succeeds."""
    large_stream = io.BytesIO(b"A" * (1024 * 1024))
    result = await sandbox_instance.file_upload(
        file_data=large_stream,
        path=temp_file_path,
        filename="large_file.bin"
    )
    assert result.success is True


async def test_file_upload_empty_file(sandbox_instance, temp_file_path):
    """DaytonaSandbox: empty-file upload succeeds."""
    result = await sandbox_instance.file_upload(
        file_data=io.BytesIO(b""),
        path=temp_file_path,
        filename="empty_file.txt"
    )
    assert result.success is True


# ---------------------------------------------------------------------------
# Download Tests
# ---------------------------------------------------------------------------

async def test_file_download_success(sandbox_instance, sample_binary_stream, sample_file_content, temp_file_path):
    """DaytonaSandbox: downloaded bytes match what was uploaded."""
    upload_result = await sandbox_instance.file_upload(
        file_data=sample_binary_stream,
        path=temp_file_path,
        filename="download_test.txt"
    )
    assert upload_result.success is True

    result = await sandbox_instance.file_download(temp_file_path)
    content = result.read()
    assert content == sample_file_content

    result.seek(0)
    assert result.read() == sample_file_content


async def test_file_download_nonexistent_file(sandbox_instance):
    """DaytonaSandbox: downloading a missing file raises an exception."""
    import secrets
    nonexistent = f"/tmp/nonexistent_{secrets.token_hex(8)}.txt"
    with pytest.raises(Exception):
        await sandbox_instance.file_download(nonexistent)


async def test_file_download_empty_file(sandbox_instance, temp_file_path):
    """DaytonaSandbox: empty file downloads correctly as zero bytes."""
    await sandbox_instance.file_upload(file_data=io.BytesIO(b""), path=temp_file_path, filename="empty.txt")
    result = await sandbox_instance.file_download(temp_file_path)
    assert result.read() == b""


async def test_file_download_large_file(sandbox_instance, temp_file_path):
    """DaytonaSandbox: 1 MB round-trip is lossless."""
    large_content = b"B" * (1024 * 1024)
    await sandbox_instance.file_upload(
        file_data=io.BytesIO(large_content),
        path=temp_file_path,
        filename="large_download.bin"
    )
    result = await sandbox_instance.file_download(temp_file_path)
    content = result.read()
    assert content == large_content
    assert len(content) == 1024 * 1024


# ---------------------------------------------------------------------------
# Integration / cycle tests
# ---------------------------------------------------------------------------

async def test_upload_then_download_cycle(sandbox_instance, sample_file_content, temp_file_path):
    """DaytonaSandbox: upload → download cycle preserves content."""
    await sandbox_instance.file_upload(
        file_data=io.BytesIO(sample_file_content),
        path=temp_file_path,
        filename="cycle_test.txt"
    )
    result = await sandbox_instance.file_download(temp_file_path)
    assert result.read() == sample_file_content


async def test_multiple_file_operations(sandbox_instance, temp_file_path):
    """DaytonaSandbox: multiple independent uploads/downloads all succeed."""
    import secrets
    files_data = [
        (b"Content of file 1", "file1.txt"),
        (b"Content of file 2", "file2.txt"),
        (b"Content of file 3", "file3.txt"),
    ]
    uploaded_paths = []
    for i, (content, filename) in enumerate(files_data):
        file_path = f"{temp_file_path}_{i}"
        result = await sandbox_instance.file_upload(
            file_data=io.BytesIO(content),
            path=file_path,
            filename=filename
        )
        assert result.success is True
        uploaded_paths.append((file_path, content))

    for file_path, expected in uploaded_paths:
        downloaded = await sandbox_instance.file_download(file_path)
        assert downloaded.read() == expected


async def test_file_overwrite(sandbox_instance, temp_file_path):
    """DaytonaSandbox: writing to the same path overwrites the previous file."""
    initial = b"Initial content"
    await sandbox_instance.file_upload(
        file_data=io.BytesIO(initial),
        path=temp_file_path,
        filename="overwrite_test.txt"
    )

    new_content = b"New content that overwrites the old one"
    await sandbox_instance.file_upload(
        file_data=io.BytesIO(new_content),
        path=temp_file_path,
        filename="overwrite_test.txt"
    )

    result = await sandbox_instance.file_download(temp_file_path)
    downloaded = result.read()
    assert downloaded == new_content
    assert downloaded != initial