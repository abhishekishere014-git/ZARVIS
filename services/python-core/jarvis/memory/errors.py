"""Domain exception hierarchy for JARVIS Memory Engine."""


class MemoryError(Exception):
    """Base exception for all memory-related subsystem errors."""


class StorageError(MemoryError):
    """Raised when SQLite or persistence operations fail."""


class SanitizationError(MemoryError):
    """Raised when secret sanitization detects irrecoverable leaks."""


class ScopeViolationError(MemoryError):
    """Raised when an operation attempts to violate memory isolation boundaries."""


class CapacityExceededError(MemoryError):
    """Raised when working or structured memory exceeds hard bounds."""


class MigrationError(MemoryError):
    """Raised when SQLite schema migrations fail to apply cleanly."""


class VectorStoreError(MemoryError):
    """Raised when vector indexing or similarity search encounters failures."""


class MemoryPoisoningError(MemoryError):
    """Raised when untrusted content attempts to poison permanent system preferences."""
