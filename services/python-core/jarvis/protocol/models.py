"""JARVIS Protocol v1.0 Pydantic models (Python mirror of shared protocol)."""

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, model_validator

PROTOCOL_VERSION: Literal["1.0"] = "1.0"


class ProtocolError(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class JarvisRequest(BaseModel):
    id: str
    type: str
    version: Literal["1.0"] = PROTOCOL_VERSION
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    payload: Dict[str, Any] = Field(default_factory=dict)


class JarvisResponse(BaseModel):
    id: str
    type: str
    version: Literal["1.0"] = PROTOCOL_VERSION
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    success: bool
    payload: Optional[Dict[str, Any]] = None
    error: Optional[ProtocolError] = None

    @model_validator(mode="after")
    def validate_error_contract(self) -> "JarvisResponse":
        if self.success and self.error is not None:
            raise ValueError("Successful response must not contain an error object")
        if not self.success and self.error is None:
            raise ValueError("Failed response must contain a non-null error object")
        return self


class JarvisEvent(BaseModel):
    id: str
    type: str
    version: Literal["1.0"] = PROTOCOL_VERSION
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    correlation_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
