"""Tests for FileSystemSandbox path confinement and attack prevention."""

from pathlib import Path
import pytest
from jarvis.tools.errors import SandboxViolationError
from jarvis.tools.sandbox import FileSystemSandbox


def test_sandbox_safe_relative_path(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    safe_path = sandbox.resolve_safe_path("documents/report.docx")

    assert safe_path.is_relative_to(tmp_path)
    assert safe_path.name == "report.docx"


def test_sandbox_blocks_parent_directory_traversal(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)

    with pytest.raises(SandboxViolationError) as exc_info:
        sandbox.resolve_safe_path("../../secret.txt")
    assert "Path traversal" in str(exc_info.value) or "escapes workspace" in str(exc_info.value)


def test_sandbox_blocks_absolute_escape_paths(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)

    with pytest.raises(SandboxViolationError) as exc_info:
        sandbox.resolve_safe_path("C:/Windows/System32/calc.exe")
    assert "Sandbox path escape" in str(exc_info.value) or "outside workspace" in str(exc_info.value)


def test_sandbox_blocks_null_byte(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)

    with pytest.raises(SandboxViolationError):
        sandbox.resolve_safe_path("doc\x00.txt")

    with pytest.raises(SandboxViolationError):
        sandbox.sanitize_filename("doc\x00.txt")


def test_sandbox_sanitize_filename() -> None:
    sandbox = FileSystemSandbox(workspace_root=Path("./workspace"))

    assert sandbox.sanitize_filename("my_report.docx") == "my_report.docx"
    assert sandbox.sanitize_filename("  test document.xlsx  ") == "test document.xlsx"

    # Directory components stripped
    assert sandbox.sanitize_filename("foo/bar.pptx") == "bar.pptx"

    # Illegal filesystem characters
    with pytest.raises(SandboxViolationError):
        sandbox.sanitize_filename("report:stream.docx")

    with pytest.raises(SandboxViolationError):
        sandbox.sanitize_filename("bad|name.pdf")


def test_sandbox_enforces_extension_whitelist(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)

    # Allowed
    p = sandbox.resolve_safe_path("report.docx", allowed_extensions={"docx", "pdf"})
    assert p.suffix == ".docx"

    # Disallowed
    with pytest.raises(SandboxViolationError) as exc_info:
        sandbox.resolve_safe_path("script.exe", allowed_extensions={"docx", "pdf"})
    assert "File extension '.exe' not permitted" in str(exc_info.value)
