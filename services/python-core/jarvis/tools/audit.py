"""Audit trail and secret scrubbing pipeline for tool executions."""

import logging
import re
from typing import Any, Dict, List, Optional
from jarvis.tools.models import ToolAuditEvent, ToolExecutionStatus

logger = logging.getLogger("jarvis.tools.audit")

# Regex patterns matching API keys, tokens, and authorization credentials
SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"(?:bearer\s+)[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?([^\s'\"]+)['\"]?", re.IGNORECASE),
]

SENSITIVE_KEY_NAMES = {
    "password", "secret", "token", "api_key", "apikey", "access_token",
    "private_key", "authorization", "auth", "credential", "keyring",
}


def scrub_secrets(value: Any) -> Any:
    """Recursively redacts API keys, passwords, and sensitive tokens from audit payloads."""
    if isinstance(value, str):
        cleaned = value
        for pattern in SECRET_PATTERNS:
            cleaned = pattern.sub("[REDACTED_SECRET]", cleaned)
        return cleaned

    if isinstance(value, dict):
        scrubbed_dict: Dict[str, Any] = {}
        for k, v in value.items():
            if str(k).lower() in SENSITIVE_KEY_NAMES:
                scrubbed_dict[k] = "[REDACTED_SECRET]"
            else:
                scrubbed_dict[k] = scrub_secrets(v)
        return scrubbed_dict

    if isinstance(value, list):
        return [scrub_secrets(item) for item in value]

    return value


class AuditLogger:
    """Manages emission and persistence of secure, scrubbed tool execution audit events."""

    def __init__(self) -> None:
        self._audit_records: List[ToolAuditEvent] = []

    def record_event(
        self,
        execution_id: str,
        tool_id: str,
        tool_version: str,
        actor: str,
        policy_decision: str,
        duration_ms: float,
        status: ToolExecutionStatus,
        correlation_id: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
    ) -> ToolAuditEvent:
        """Records an immutable, secret-scrubbed audit event."""
        safe_args = scrub_secrets(arguments or {})
        event = ToolAuditEvent(
            execution_id=execution_id,
            tool_id=tool_id,
            tool_version=tool_version,
            actor=actor,
            policy_decision=policy_decision,
            duration_ms=round(duration_ms, 2),
            status=status,
            correlation_id=correlation_id,
            arguments_summary=safe_args,
            error_code=error_code,
            artifacts=artifacts or [],
        )

        self._audit_records.append(event)
        logger.info(
            "Tool audit: [%s] tool=%s status=%s duration=%.2fms actor=%s correlation_id=%s",
            event.execution_id[:8],
            event.tool_id,
            event.status.value,
            event.duration_ms,
            event.actor,
            event.correlation_id,
        )
        return event

    @property
    def recent_records(self) -> List[ToolAuditEvent]:
        return list(self._audit_records)
