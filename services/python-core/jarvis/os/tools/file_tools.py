"""File and directory exploration tools registered with Phase 04."""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from jarvis.tools.decorator import tool
from jarvis.tools.models import RiskLevel, ToolExecutionContext, ToolPermission

logger = logging.getLogger("jarvis.os.tools.file")

KNOWN_DIRECTORIES = {
    "downloads": lambda: Path.home() / "Downloads",
    "documents": lambda: Path.home() / "Documents",
    "desktop": lambda: Path.home() / "Desktop",
    "pictures": lambda: Path.home() / "Pictures",
    "music": lambda: Path.home() / "Music",
    "videos": lambda: Path.home() / "Videos",
    "home": lambda: Path.home(),
}


@tool(
    name="file_open_directory",
    tool_id="file.open_directory",
    description="Opens an approved user directory (Downloads, Documents, Desktop, Workspace) in Windows File Explorer.",
    category="file",
    version="1.0.0",
    permissions={ToolPermission.READ, ToolPermission.EXECUTE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=10.0,
)
async def file_open_directory(
    directory_name: str,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Opens a directory in Windows Explorer.

    :param directory_name: Name of standard directory ('downloads', 'documents', 'desktop', 'workspace')
    """
    normalized = directory_name.strip().lower()

    target_dir: Optional[Path] = None
    if normalized in KNOWN_DIRECTORIES:
        target_dir = KNOWN_DIRECTORIES[normalized]()
    elif normalized in ("workspace", "project"):
        target_dir = Path.cwd() / "data" / "workspace"
        target_dir.mkdir(parents=True, exist_ok=True)
    else:
        # Check if it resolves to a safe directory in home
        candidate = Path.home() / directory_name.strip()
        if candidate.exists() and candidate.is_dir():
            target_dir = candidate

    if not target_dir or not target_dir.exists():
        allowed_list = list(KNOWN_DIRECTORIES.keys()) + ["workspace"]
        return {
            "opened": False,
            "error": f"Directory '{directory_name}' could not be resolved or does not exist. Supported: {', '.join(allowed_list)}",
            "message": f"Could not find folder '{directory_name}'. Supported folders: {', '.join(allowed_list)}.",
        }

    try:
        if sys.platform == "win32":
            os.startfile(str(target_dir))
        return {
            "opened": True,
            "directory": str(target_dir),
            "message": f"Opened '{target_dir.name}' in File Explorer.",
        }
    except Exception as exc:
        if sys.platform == "win32":
            try:
                subprocess.Popen(["explorer.exe", str(target_dir)])
                return {
                    "opened": True,
                    "directory": str(target_dir),
                    "message": f"Opened '{target_dir.name}' in File Explorer.",
                }
            except Exception as e2:
                logger.error("Explorer launch failed: %s", e2)

        logger.error("Failed to open directory %s: %s", target_dir, exc)
        return {
            "opened": False,
            "directory": str(target_dir),
            "error": str(exc),
            "message": f"Failed to open '{target_dir.name}' in File Explorer: {exc}",
        }


@tool(
    name="file_list_files",
    tool_id="file.list_files",
    description="Lists files in the workspace or a specified directory.",
    category="file",
    version="1.0.0",
    permissions={ToolPermission.READ},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def file_list_files(
    directory_name: Optional[str] = None,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Lists files in the target directory."""
    if directory_name and directory_name.lower() in KNOWN_DIRECTORIES:
        target_dir = KNOWN_DIRECTORIES[directory_name.lower()]()
    else:
        target_dir = Path.cwd() / "data" / "workspace"

    if not target_dir.exists():
        return {"files": [], "directory": str(target_dir), "count": 0}

    files = []
    try:
        for entry in target_dir.iterdir():
            files.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size_bytes": entry.stat().st_size if entry.is_file() else 0,
            })
        return {
            "files": files[:50],
            "count": len(files),
            "directory": str(target_dir),
            "message": f"Found {len(files)} items in {target_dir.name}.",
        }
    except Exception as exc:
        return {
            "files": [],
            "error": str(exc),
            "directory": str(target_dir),
            "message": f"Failed to list directory contents: {exc}",
        }


@tool(
    name="file_create_text_file",
    tool_id="file.create_text_file",
    description="Creates a safe text or markdown file inside the workspace sandbox.",
    category="file",
    version="1.0.0",
    permissions={ToolPermission.WRITE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def file_create_text_file(
    file_name: str,
    content: str,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Creates a text file inside workspace."""
    clean_name = os.path.basename(file_name.strip())
    workspace = Path.cwd() / "data" / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    target_file = workspace / clean_name

    try:
        target_file.write_text(content, encoding="utf-8")
        return {
            "created": True,
            "filename": clean_name,
            "path": str(target_file),
            "size_bytes": len(content.encode("utf-8")),
            "message": f"Created file '{clean_name}' successfully.",
        }
    except Exception as exc:
        return {
            "created": False,
            "filename": clean_name,
            "error": str(exc),
            "message": f"Failed to create file '{clean_name}': {exc}",
        }
