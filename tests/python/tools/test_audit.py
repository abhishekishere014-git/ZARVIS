"""Tests for AuditLogger and secret scrubbing."""

from jarvis.tools.audit import AuditLogger, scrub_secrets
from jarvis.tools.models import ToolExecutionStatus


def test_scrub_secrets_redacts_keys_and_tokens() -> None:
    payload = {
        "api_key": "sk-1234567890abcdef1234567890abcdef",
        "authorization": "Bearer ya29.a0AfH6SMDI82736182736182",
        "nested": {
            "password": "SuperSecretPassword123!",
            "normal_field": "hello world",
        },
        "list_data": [
            "sk-9999999999999999999999999999",
            "safe string",
        ],
    }

    scrubbed = scrub_secrets(payload)

    assert scrubbed["api_key"] == "[REDACTED_SECRET]"
    assert scrubbed["authorization"] == "[REDACTED_SECRET]"
    assert scrubbed["nested"]["password"] == "[REDACTED_SECRET]"
    assert scrubbed["nested"]["normal_field"] == "hello world"
    assert scrubbed["list_data"][0] == "[REDACTED_SECRET]"
    assert scrubbed["list_data"][1] == "safe string"


def test_audit_logger_records_sanitized_event() -> None:
    logger = AuditLogger()

    event = logger.record_event(
        execution_id="exec_123",
        tool_id="test.tool",
        tool_version="1.0.0",
        actor="agent",
        policy_decision="allowed",
        duration_ms=45.2,
        status=ToolExecutionStatus.SUCCESS,
        correlation_id="corr_456",
        arguments={"token": "secret_token_val", "query": "status report"},
        artifacts=["/path/to/report.docx"],
    )

    assert event.execution_id == "exec_123"
    assert event.arguments_summary["token"] == "[REDACTED_SECRET]"
    assert event.arguments_summary["query"] == "status report"
    assert event.artifacts == ["/path/to/report.docx"]
    assert len(logger.recent_records) == 1
