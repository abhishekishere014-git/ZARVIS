import pytest
from jarvis.security.vault import InMemoryVault, KeyringVault, get_vault


def test_in_memory_vault():
    vault = InMemoryVault()
    assert not vault.has_secret("TEST_KEY")
    assert vault.get_secret("TEST_KEY") is None

    vault.set_secret("TEST_KEY", "super-secret-value-123")
    assert vault.has_secret("TEST_KEY")
    assert vault.get_secret("TEST_KEY") == "super-secret-value-123"

    # Delete
    deleted = vault.delete_secret("TEST_KEY")
    assert deleted is True
    assert not vault.has_secret("TEST_KEY")
    assert vault.get_secret("TEST_KEY") is None

    # Delete non-existent
    assert vault.delete_secret("NON_EXISTENT") is False


def test_vault_factory():
    mem_vault = get_vault("memory")
    assert isinstance(mem_vault, InMemoryVault)

    keyring_vault = get_vault("keyring")
    assert isinstance(keyring_vault, KeyringVault)
