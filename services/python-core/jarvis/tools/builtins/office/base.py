"""Base configuration, resource limits, and common utilities for office document generators."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from jarvis.tools.errors import ArtifactVerificationError, ResourceLimitExceededError


class OfficeLimits(BaseModel):
    """Resource boundaries to prevent denial-of-service memory exhaustion during document generation."""

    max_file_size_bytes: int = Field(default=50 * 1024 * 1024, description="50 MB maximum file size")
    max_table_rows: int = Field(default=10_000, description="Max allowed rows per table or sheet")
    max_table_cols: int = Field(default=200, description="Max allowed columns per table or sheet")
    max_slides: int = Field(default=100, description="Max allowed slides in presentation")
    max_pages: int = Field(default=200, description="Max allowed pages in PDF document")
    max_text_length: int = Field(default=1_000_000, description="Max total characters per document payload")


DEFAULT_LIMITS = OfficeLimits()


def verify_file_size_within_limit(path: Path, max_bytes: int = DEFAULT_LIMITS.max_file_size_bytes) -> int:
    """Verifies that the generated file exists and does not exceed file size limits."""
    if not path.exists():
        raise ArtifactVerificationError(f"Artifact does not exist: '{path}'")

    size = path.stat().st_size
    if size == 0:
        raise ArtifactVerificationError(f"Generated artifact is empty (0 bytes): '{path}'")

    if size > max_bytes:
        raise ResourceLimitExceededError(f"Generated file size {size} bytes exceeds limit of {max_bytes} bytes.")

    return size
