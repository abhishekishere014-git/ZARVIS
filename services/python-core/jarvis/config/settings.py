"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class JarvisSettings(BaseSettings):
    """Runtime configuration for JARVIS Python Core."""

    model_config = SettingsConfigDict(
        env_prefix="JARVIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["development", "production", "test"] = "development"
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Security: loopback binding only by default
    core_host: str = Field(default="127.0.0.1", description="Bind IP for core IPC")
    core_port: int = Field(default=8765, description="Port for core IPC")

    data_dir: Path = Field(default=Path("./data"), description="Directory for persistent data")
    workspace_dir: Path = Field(
        default=Path("./data/workspace"),
        description="Directory for restricted sandboxed tool execution and generated files",
    )
    vault_backend: Literal["keyring", "memory"] = Field(
        default="keyring",
        description="Backend for credential isolation (Windows Credential Manager via keyring, or memory for tests)"
    )

    # Memory Engine Configuration (Phase 06)
    memory_enabled: bool = Field(default=True, description="Enable tri-tier memory engine")
    memory_db_path: Path | None = Field(default=None, description="Custom path to SQLite memory DB (defaults to data_dir/memory/jarvis-memory.db)")
    memory_max_working_messages: int = Field(default=50, description="Max messages in working memory buffer")
    memory_max_working_tokens: int = Field(default=8192, description="Max tokens in working memory buffer")
    memory_retention_days: int = Field(default=90, description="Durable retention window in days")
    memory_semantic_enabled: bool = Field(default=True, description="Enable vector semantic retrieval")
    memory_top_k: int = Field(default=5, description="Default top-K memories retrieved")
    memory_embedding_provider: str = Field(default="hash", description="Embedding provider: 'hash', 'mock', 'openai'")

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def is_test(self) -> bool:
        return self.env == "test"
