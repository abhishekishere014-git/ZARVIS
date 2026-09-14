"""Secret Vault abstraction for credential isolation."""

import logging
from abc import ABC, abstractmethod
from typing import Optional
import keyring
from keyring.errors import KeyringError

logger = logging.getLogger("jarvis.security.vault")

JARVIS_KEYRING_SERVICE = "JARVIS_AI_PLATFORM"


class SecretVault(ABC):
    """Abstract interface for local secret management."""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by name."""
        pass

    @abstractmethod
    def set_secret(self, key: str, value: str) -> None:
        """Securely store a secret."""
        pass

    @abstractmethod
    def delete_secret(self, key: str) -> bool:
        """Remove a secret by name. Returns True if deleted."""
        pass

    @abstractmethod
    def has_secret(self, key: str) -> bool:
        """Check if secret exists without exposing its content."""
        pass


class KeyringVault(SecretVault):
    """Secure vault using the host OS Credential Manager (via keyring)."""

    def __init__(self, service_name: str = JARVIS_KEYRING_SERVICE) -> None:
        self.service_name = service_name

    def get_secret(self, key: str) -> Optional[str]:
        try:
            return keyring.get_password(self.service_name, key)
        except KeyringError as e:
            logger.error("Failed to retrieve secret '%s': %s", key, e)
            return None

    def set_secret(self, key: str, value: str) -> None:
        try:
            keyring.set_password(self.service_name, key, value)
            logger.debug("Secret '%s' stored in keyring.", key)
        except KeyringError as e:
            logger.error("Failed to store secret '%s': %s", key, e)
            raise

    def delete_secret(self, key: str) -> bool:
        try:
            keyring.delete_password(self.service_name, key)
            logger.debug("Secret '%s' removed from keyring.", key)
            return True
        except KeyringError:
            return False

    def has_secret(self, key: str) -> bool:
        return self.get_secret(key) is not None


class InMemoryVault(SecretVault):
    """In-memory secret vault for hermetic testing and ephemeral development."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get_secret(self, key: str) -> Optional[str]:
        return self._store.get(key)

    def set_secret(self, key: str, value: str) -> None:
        self._store[key] = value

    def delete_secret(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def has_secret(self, key: str) -> bool:
        return key in self._store


def get_vault(backend: str = "keyring") -> SecretVault:
    """Factory to obtain the configured vault implementation."""
    if backend == "memory":
        return InMemoryVault()
    return KeyringVault()
