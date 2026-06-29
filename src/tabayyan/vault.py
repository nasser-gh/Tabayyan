"""Encrypted persistence for the tokenize vault.

`RedactionMode.TOKENIZE` produces a vault (token -> original value). That vault
is the **reversal key**: anyone who holds it can de-anonymize the redacted
text. Keeping it as a plaintext dict on disk defeats the purpose, so this
module persists it as an authenticated, password-encrypted blob.

Design choice: we do **not** roll our own crypto. Encryption uses the vetted
`cryptography` library (Fernet = AES-128-CBC + HMAC-SHA256, authenticated),
with a key derived from the password via PBKDF2-HMAC-SHA256. It is an optional
extra so the detection core stays zero-dependency:

    pip install "tabayyan[crypto]"

Envelope format (JSON, versioned):
    {"v": 1, "kdf": "pbkdf2-sha256", "iterations": N, "salt": b64, "token": fernet}
"""
from __future__ import annotations

import base64
import json
import os

_PBKDF2_ITERATIONS = 600_000  # OWASP 2023 guidance for PBKDF2-HMAC-SHA256
_INSTALL_HINT = (
    "encrypted vault requires the 'cryptography' package. Install with: "
    'pip install "tabayyan[crypto]"'
)


def _require_crypto():
    try:
        from cryptography.fernet import Fernet, InvalidToken
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError as exc:  # pragma: no cover - exercised via test skip
        raise ImportError(_INSTALL_HINT) from exc
    return Fernet, InvalidToken, hashes, PBKDF2HMAC


def _derive_key(password: str, salt: bytes, iterations: int) -> bytes:
    _, _, hashes, PBKDF2HMAC = _require_crypto()
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_vault(vault: dict, password: str, *, iterations: int = _PBKDF2_ITERATIONS) -> bytes:
    """Return an encrypted, authenticated envelope (bytes) for `vault`."""
    if not password:
        raise ValueError("a non-empty password is required to encrypt the vault")
    Fernet, _, _, _ = _require_crypto()
    salt = os.urandom(16)
    token = Fernet(_derive_key(password, salt, iterations)).encrypt(
        json.dumps(vault, ensure_ascii=False).encode("utf-8")
    )
    envelope = {
        "v": 1,
        "kdf": "pbkdf2-sha256",
        "iterations": iterations,
        "salt": base64.b64encode(salt).decode("ascii"),
        "token": token.decode("ascii"),
    }
    return json.dumps(envelope).encode("utf-8")


def decrypt_vault(blob: bytes, password: str) -> dict:
    """Reverse `encrypt_vault`. Raises ValueError on a wrong password or
    tampered/corrupted blob."""
    Fernet, InvalidToken, _, _ = _require_crypto()
    try:
        envelope = json.loads(blob)
        salt = base64.b64decode(envelope["salt"])
        iterations = int(envelope["iterations"])
        token = envelope["token"].encode("ascii")
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("not a valid tabayyan vault envelope") from exc
    try:
        plaintext = Fernet(_derive_key(password, salt, iterations)).decrypt(token)
    except InvalidToken as exc:
        raise ValueError("wrong password or corrupted vault") from exc
    return json.loads(plaintext)


def save_vault(vault: dict, path: str, password: str, *, iterations: int = _PBKDF2_ITERATIONS) -> None:
    """Encrypt `vault` and write it to `path` with owner-only permissions."""
    blob = encrypt_vault(vault, password, iterations=iterations)
    # Create with 0600 so the envelope is not world-readable even before write.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(blob)


def load_vault(path: str, password: str) -> dict:
    """Read and decrypt a vault written by `save_vault`."""
    with open(path, "rb") as fh:
        return decrypt_vault(fh.read(), password)
