"""Secret sanitization and redaction engine for persistent memory."""

import re
from typing import Any, Dict, List, Union

# Common credential and API key regex signatures
SECRET_PATTERNS = [
    # Anthropic API Keys (must precede OpenAI sk- prefix)
    (re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}", re.IGNORECASE), "[REDACTED_ANTHROPIC_KEY]"),
    # OpenAI API Keys
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE), "[REDACTED_OPENAI_KEY]"),
    # Google API Keys
    (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "[REDACTED_GOOGLE_KEY]"),
    # GitHub Tokens
    (re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{30,})"), "[REDACTED_GITHUB_TOKEN]"),
    # Authorization Headers (Bearer / Basic)
    (re.compile(r"(?i)Authorization:\s*(Bearer|Basic)\s+[^\s\"'\n\r]+"), "Authorization: [REDACTED_AUTH_HEADER]"),
    (re.compile(r"(?i)Bearer\s+[a-zA-Z0-9_\-\.]{20,}"), "[REDACTED_BEARER_TOKEN]"),
    # Password key-value pairs
    (re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*[^\s\"',;]+"), r"\1=[REDACTED_PASSWORD]"),
    # API key assignments
    (re.compile(r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*[^\s\"',;]+"), r"\1=[REDACTED_KEY]"),
    # Secret Env Vars
    (
        re.compile(r"(?i)(OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|AWS_SECRET_ACCESS_KEY)\s*=\s*[^\s\"',;]+"),
        r"\1=[REDACTED_ENV_VAR]",
    ),
]


class SecretRedactor:
    """Detects and recursively redacts secrets from strings, dictionaries, and lists."""

    @classmethod
    def redact_text(cls, text: str) -> str:
        """Redacts all known credential patterns from a string and strips null bytes."""
        if not text:
            return ""

        # Remove null bytes to prevent injection or database corruption
        sanitized = text.replace("\x00", "")

        for pattern, replacement in SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized

    @classmethod
    def redact_data(cls, data: Any) -> Any:
        """Recursively traverses nested dictionaries, lists, and primitives redacting secrets."""
        if isinstance(data, str):
            return cls.redact_text(data)
        elif isinstance(data, dict):
            clean_dict: Dict[str, Any] = {}
            for k, v in data.items():
                clean_key = cls.redact_text(str(k))
                # If key itself suggests sensitive data, redact value completely
                if any(sec in clean_key.lower() for sec in ("password", "secret", "token", "api_key", "credential")):
                    clean_dict[clean_key] = "[REDACTED_SENSITIVE_FIELD]"
                else:
                    clean_dict[clean_key] = cls.redact_data(v)
            return clean_dict
        elif isinstance(data, list):
            return [cls.redact_data(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(cls.redact_data(item) for item in data)
        elif isinstance(data, set):
            return {cls.redact_data(item) for item in data}
        return data


def sanitize_content(text: str) -> str:
    """Functional shortcut to redact secrets from text."""
    return SecretRedactor.redact_text(text)


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Functional shortcut to recursively redact secrets from metadata dictionaries."""
    sanitized = SecretRedactor.redact_data(metadata)
    return sanitized if isinstance(sanitized, dict) else {}
