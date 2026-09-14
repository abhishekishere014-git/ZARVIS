"""Tests for secret redaction, credential detection, and sanitization."""

from jarvis.memory.security.sanitizer import SecretRedactor, sanitize_content, sanitize_metadata


def test_redacts_openai_key() -> None:
    text = "My key is sk-1234567890abcdefghijklmnopqrstuv"
    clean = sanitize_content(text)
    assert "sk-1234567890abcdefghijklmnopqrstuv" not in clean
    assert "[REDACTED_OPENAI_KEY]" in clean


def test_redacts_anthropic_key() -> None:
    text = "Claude key: sk-ant-api03-abcdefghijklmnopqrstuvwxyz12345"
    clean = sanitize_content(text)
    assert "sk-ant-" not in clean
    assert "[REDACTED_ANTHROPIC_KEY]" in clean


def test_redacts_google_key() -> None:
    text = "Gemini key: AIzaSyD1234567890abcdefghijklmnopqrstuv"
    clean = sanitize_content(text)
    assert "AIzaSyD1234567890abcdefghijklmnopqrstuv" not in clean
    assert "[REDACTED_GOOGLE_KEY]" in clean


def test_redacts_bearer_token_and_passwords() -> None:
    text = "Authorization: Bearer mySecretToken1234567890\npassword=superSecret123"
    clean = sanitize_content(text)
    assert "mySecretToken" not in clean
    assert "superSecret123" not in clean
    assert "[REDACTED_AUTH_HEADER]" in clean
    assert "[REDACTED_PASSWORD]" in clean


def test_removes_null_bytes() -> None:
    text = "Hello\x00World\x00Injection"
    clean = sanitize_content(text)
    assert "\x00" not in clean
    assert clean == "HelloWorldInjection"


def test_recursive_metadata_sanitization() -> None:
    meta = {
        "user": "alice",
        "api_key": "sk-1234567890abcdefghijklmnopqrstuv",
        "nested": {
            "password": "secretPassword!",
            "token": "ghp_1234567890abcdefghijklmnopqrstuvwxyz",
        },
    }
    cleaned = sanitize_metadata(meta)
    assert cleaned["user"] == "alice"
    assert "secretPassword!" not in str(cleaned)
    assert "sk-" not in str(cleaned)
