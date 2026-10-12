"""Demo-only username/password authentication.

This is explicitly NOT production authentication: passwords are SHA-256
hashed (no per-user salt, no key stretching) and stored in a plain JSON file
alongside the demo corpus. It exists only to give the hackathon demo a real
login screen instead of a bare identity dropdown, per FR-1 ("do not present a
user-select dropdown as production authentication"). Swap this module for a
real identity provider before using TrustRAG outside a controlled demo.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    return hash_password(password) == password_hash


@dataclass(frozen=True)
class Credential:
    user_id: str
    password_hash: str


def authenticate(username: str, password: str, credentials: list[Credential]) -> str | None:
    """Returns the matching user_id on success, None on any failure.

    Fails closed: empty username/password, or no matching credential, both
    return None rather than raising.
    """
    if not username or not password:
        return None
    for credential in credentials:
        if credential.user_id == username and verify_password(password, credential.password_hash):
            return credential.user_id
    return None
