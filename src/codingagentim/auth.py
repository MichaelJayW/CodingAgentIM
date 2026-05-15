"""Unified authentication framework with keyring credential storage."""

from __future__ import annotations

import keyring

SERVICE_NAME = "codingagentim"


def store_credential(provider: str, key: str, value: str) -> None:
    keyring.set_password(f"{SERVICE_NAME}.{provider}", key, value)


def get_credential(provider: str, key: str) -> str | None:
    return keyring.get_password(f"{SERVICE_NAME}.{provider}", key)


def delete_credential(provider: str, key: str) -> None:
    try:
        keyring.delete_password(f"{SERVICE_NAME}.{provider}", key)
    except keyring.errors.PasswordDeleteError:
        pass
