"""Filesystem sandbox providing strict confinement, path normalization, and jailbreak prevention."""

import os
import re
from pathlib import Path
from typing import Optional, Set
from jarvis.tools.errors import SandboxViolationError

# Disallow null bytes, alternate data streams, and illegal Windows/POSIX path characters in base names
ILLEGAL_CHARACTERS_REGEX = re.compile(r'[\x00<>:"|?*]')


class FileSystemSandbox:
    """Enforces strict path confinement within a designated workspace root."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        """Sanitizes a bare filename, stripping illegal characters and directory separators."""
        if not filename or not isinstance(filename, str):
            raise SandboxViolationError("Filename must be a non-empty string.")

        # Check for null bytes or traversal sequences
        if "\x00" in filename:
            raise SandboxViolationError("Filename contains forbidden null byte.")

        # Normalize slashes and disallow directory traversal in pure filenames
        cleaned = os.path.basename(filename.strip())
        if not cleaned or cleaned in (".", ".."):
            raise SandboxViolationError(f"Invalid filename: '{filename}'")

        if ILLEGAL_CHARACTERS_REGEX.search(cleaned):
            raise SandboxViolationError(f"Filename contains illegal filesystem characters: '{cleaned}'")

        return cleaned

    def resolve_safe_path(
        self,
        target_path: str | Path,
        allowed_extensions: Optional[Set[str]] = None,
        must_exist: bool = False,
    ) -> Path:
        """Resolves a target path against the sandbox workspace root and guarantees confinement.

        Raises:
            SandboxViolationError: if the path attempts traversal, escapes workspace, or uses forbidden syntax.
        """
        raw_str = str(target_path).strip()
        if not raw_str:
            raise SandboxViolationError("Target path cannot be empty.")

        if "\x00" in raw_str:
            raise SandboxViolationError("Target path contains forbidden null byte.")

        path_obj = Path(raw_str)

        # Disallow explicit traversal tokens in the raw string before resolution
        parts = path_obj.parts
        if ".." in parts:
            raise SandboxViolationError(f"Path traversal sequence '..' detected in path: '{raw_str}'")

        try:
            if path_obj.is_absolute():
                # If absolute, it MUST resolve inside the sandbox workspace_root
                resolved = path_obj.resolve()
            else:
                # Relative paths are appended directly to workspace_root
                resolved = (self.workspace_root / path_obj).resolve()

            # Verify resolved path is strictly contained within workspace_root
            if not resolved.is_relative_to(self.workspace_root):
                raise SandboxViolationError(
                    f"Sandbox path escape detected! Path '{raw_str}' resolves outside workspace '{self.workspace_root}'"
                )

            # Check if resolving symlinks would escape the workspace
            real_path = Path(os.path.realpath(str(resolved)))
            if not real_path.is_relative_to(self.workspace_root):
                raise SandboxViolationError(
                    f"Symlink jailbreak detected! Path '{raw_str}' points outside workspace '{self.workspace_root}'"
                )

        except (ValueError, RuntimeError) as exc:
            raise SandboxViolationError(f"Failed to resolve safe sandbox path: {exc}") from exc

        # Optional extension verification
        if allowed_extensions is not None:
            ext = resolved.suffix.lower().lstrip(".")
            if ext not in {e.lower().lstrip(".") for e in allowed_extensions}:
                raise SandboxViolationError(
                    f"File extension '.{ext}' not permitted. Allowed: {allowed_extensions}"
                )

        if must_exist and not resolved.exists():
            raise SandboxViolationError(f"Requested file does not exist in sandbox: '{resolved.name}'")

        return resolved

    def ensure_subdirectory(self, sub_dir: str) -> Path:
        """Safely creates and returns a verified sub-directory within the workspace."""
        sub_path = self.resolve_safe_path(sub_dir)
        sub_path.mkdir(parents=True, exist_ok=True)
        return sub_path
