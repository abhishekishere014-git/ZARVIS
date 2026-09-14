"""Domain-specific typed exceptions for JARVIS."""

class JarvisError(Exception):
    """Base exception for all JARVIS errors."""
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(JarvisError):
    """Raised when application configuration is invalid or missing."""
    pass


class ServiceError(JarvisError):
    """Raised when a managed service encounters an operational fault."""
    pass


class EventBusError(JarvisError):
    """Raised on event publication, dispatch, or subscription errors."""
    pass


class SecurityError(JarvisError):
    """Raised when security boundaries, permissions, or vault operations fail."""
    pass


class HealthCheckError(JarvisError):
    """Raised when a system component fails a critical health probe."""
    pass
