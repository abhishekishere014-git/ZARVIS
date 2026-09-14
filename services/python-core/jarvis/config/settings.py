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

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def is_test(self) -> bool:
        return self.env == "test"
