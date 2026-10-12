"""Authenticated local archives and explicitly selected operating-system key stores."""

import base64
import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from ..contracts import ContractError


def encrypt_archive(content: bytes, key: bytes) -> bytes:
    return Fernet(key).encrypt(content)


def decrypt_archive(content: bytes, key: bytes) -> bytes:
    try:
        return Fernet(key).decrypt(content)
    except (InvalidToken, ValueError) as error:
        raise ContractError("archive authentication failed") from error


def archive_key(identity: str) -> bytes | None:
    """Bound key-store access; missing/locked stores never fall back to local plaintext."""
    child = """import sys,base64
import keyring
backend=keyring.get_keyring()
allowed={"keyring.backends.macOS", "keyring.backends.Windows", "keyring.backends.SecretService"}
if type(backend).__module__ not in allowed: sys.exit(2)
if type(backend).__module__ == "keyring.backends.SecretService":
    import secretstorage
    bus=secretstorage.dbus_init()
    if secretstorage.get_default_collection(bus).is_locked(): sys.exit(2)
value=backend.get_password("jevdrill.archive.v1",sys.argv[1])
if value is None: sys.exit(2)
sys.stdout.write(value)
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", child, identity],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=2,
            check=False,
        )
        if result.returncode != 0 or len(result.stdout) > 128:
            return None
        key = result.stdout.strip()
        if len(base64.urlsafe_b64decode(key)) != 32:
            return None
        Fernet(key)
        return key
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


@contextmanager
def maintenance_lock(
    path: Path, *, acquired_fd: Callable[[int], None] | None = None
) -> Iterator[bool]:
    """OS-owned custody survives time changes and releases when the worker exits."""
    with path.open("a+b") as stream:
        if stream.seek(0, os.SEEK_END) == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            if acquired_fd is not None:
                acquired_fd(stream.fileno())
            yield True
        finally:
            stream.seek(0)
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def encode_archive(value: object, key: bytes) -> bytes:
    return encrypt_archive(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(), key
    )
