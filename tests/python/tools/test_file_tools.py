"""Tests for file exploration and directory tools."""

from pathlib import Path
import pytest
from jarvis.os.tools.file_tools import (
    file_open_directory,
    file_list_files,
    file_create_text_file,
    KNOWN_DIRECTORIES,
)


def test_known_directories_resolution() -> None:
    assert "downloads" in KNOWN_DIRECTORIES
    assert "documents" in KNOWN_DIRECTORIES
    assert "desktop" in KNOWN_DIRECTORIES
    assert KNOWN_DIRECTORIES["downloads"]().name == "Downloads"


@pytest.mark.asyncio
async def test_file_open_directory_invalid() -> None:
    result = await file_open_directory("nonexistent_folder_xyz_123")
    assert result["opened"] is False
    assert "could not be resolved" in result["error"]


@pytest.mark.asyncio
async def test_file_create_and_list(tmp_path: Path) -> None:
    result = await file_create_text_file("notes.txt", "Hello ZARVIS")
    assert result["created"] is True
    assert result["filename"] == "notes.txt"
    assert result["size_bytes"] > 0
