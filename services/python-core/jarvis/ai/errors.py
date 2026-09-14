"""Normalized, provider-agnostic AI error taxonomy."""

from typing import Any, Dict, Optional
from jarvis.core.exceptions import JarvisError


class AIError(JarvisError):
    """Base exception for all AI provider and routing errors."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        is_retryable: bool = False,
    ) -> None:
        super().__init__(message, details)
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.is_retryable = is_retryable


class AuthenticationError(AIError):
    """Raised on invalid credentials, revoked tokens, or unauthorized requests (401/403)."""

    def __init__(self, message: str, provider: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(message, provider=provider, status_code=401, is_retryable=False, **kwargs)


class InvalidRequestError(AIError):
    """Raised when request payload or parameters violate provider constraints (400)."""

    def __init__(self, message: str, provider: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(message, provider=provider, status_code=400, is_retryable=False, **kwargs)


class ModelNotFoundError(AIError):
    """Raised when requested model name does not exist on provider (404)."""

    def __init__(self, message: str, provider: Optional[str] = None, model: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(message, provider=provider, model=model, status_code=404, is_retryable=False, **kwargs)


class CapabilityNotSupportedError(AIError):
    """Raised when a feature (e.g. tools, vision) is not supported by target model/provider."""

    def __init__(self, message: str, provider: Optional[str] = None, model: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(message, provider=provider, model=model, is_retryable=False, **kwargs)


class RateLimitError(AIError):
    """Raised when provider rate limits, token quotas, or concurrency limits are exceeded (429)."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        retry_after: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, provider=provider, status_code=429, is_retryable=True, **kwargs)
        self.retry_after = retry_after


class ProviderUnavailableError(AIError):
    """Raised when provider infrastructure is down, returning 5xx or connection refused."""

    def __init__(self, message: str, provider: Optional[str] = None, status_code: Optional[int] = 503, **kwargs: Any) -> None:
        super().__init__(message, provider=provider, status_code=status_code, is_retryable=True, **kwargs)


class AITimeoutError(AIError):
    """Raised when provider connect, read, or stream timeout expires."""

    def __init__(self, message: str, provider: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(message, provider=provider, status_code=408, is_retryable=True, **kwargs)


class AIStreamError(AIError):
    """Raised when an active token stream is disrupted or corrupted."""

    def __init__(self, message: str, provider: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(message, provider=provider, is_retryable=True, **kwargs)


class AICancelledError(AIError):
    """Raised when an ongoing generation or stream is cancelled by user or caller."""

    def __init__(self, message: str = "AI generation cancelled by caller", provider: Optional[str] = None) -> None:
        super().__init__(message, provider=provider, is_retryable=False)
