"""Centralized identity, role resolution, ACL checks, and authorized-document resolution.

Security-critical module: this is the ONLY place that should decide whether a user
may see a document. Retrieval and answer generation must call into this module
rather than re-implementing access logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class User:
    user_id: str
    display_name: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    file_name: str
    classification: str
    owner_id: str
    allowed_roles: tuple[str, ...]
    allowed_users: tuple[str, ...]
    created_at: str


@dataclass(frozen=True)
class Delegation:
    grant_id: str
    grantor_id: str
    grantee_id: str
    document_id: str
    created_at: str
    expires_at: str
    revoked_at: str | None = None
    reason: str | None = None


# Explicit, documented business rule: admins may read every document.
# This is a deliberate, testable policy choice rather than an implicit assumption.
ADMIN_ROLE = "admin"
ADMIN_BYPASS_ALL_DOCUMENTS = True


def _parse_iso(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class AuthorizationError(ValueError):
    """Raised when identity or ACL data is malformed and access must fail closed."""


def validate_user(user: User | None) -> User:
    if user is None or not user.user_id or not user.roles:
        raise AuthorizationError("Invalid or missing user identity.")
    return user


def validate_document(document: Document) -> bool:
    """Returns True if the document metadata is well-formed enough to evaluate.

    Malformed documents must be treated as inaccessible by default (fail closed),
    never raise and silently grant access.
    """
    if not document.document_id or not document.title:
        return False
    if not isinstance(document.classification, str) or not document.classification.strip():
        return False
    if not isinstance(document.allowed_roles, (list, tuple)):
        return False
    if not isinstance(document.allowed_users, (list, tuple)):
        return False
    return True


def _delegation_grants_access(
    delegation: Delegation,
    user: User,
    document_id: str,
    now: datetime,
) -> bool:
    if delegation.grantee_id != user.user_id:
        return False
    if delegation.document_id != document_id:
        return False
    if delegation.revoked_at is not None:
        return False
    try:
        expires_at = _parse_iso(delegation.expires_at)
        created_at = _parse_iso(delegation.created_at)
    except (ValueError, TypeError):
        return False
    if expires_at <= created_at:
        return False
    if now >= expires_at:
        return False
    return True


def is_authorized(
    user: User,
    document: Document,
    delegations: list[Delegation],
    now: datetime | None = None,
) -> bool:
    """Single source of truth for whether `user` may access `document`.

    Fails closed: any malformed input results in False, never an exception that
    could be mishandled upstream into an accidental allow.
    """
    now = now or datetime.now(timezone.utc)

    try:
        validate_user(user)
    except AuthorizationError:
        return False

    if not validate_document(document):
        return False

    if ADMIN_BYPASS_ALL_DOCUMENTS and ADMIN_ROLE in user.roles:
        return True

    if user.user_id in document.allowed_users:
        return True

    if set(user.roles) & set(document.allowed_roles):
        return True

    for delegation in delegations:
        if _delegation_grants_access(delegation, user, document.document_id, now):
            return True

    return False


def get_authorized_document_ids(
    user: User,
    documents: list[Document],
    delegations: list[Delegation],
    now: datetime | None = None,
) -> set[str]:
    """Returns the set of document_ids the user is currently authorized to access."""
    now = now or datetime.now(timezone.utc)
    return {
        document.document_id
        for document in documents
        if is_authorized(user, document, delegations, now)
    }


def can_delegate_document(
    grantor: User,
    document: Document,
    delegations: list[Delegation],
    now: datetime | None = None,
) -> bool:
    """A user may only delegate access to a document they themselves can access.

    This enforces business rule: "The application must not allow a user to grant
    access they do not possess."
    """
    return is_authorized(grantor, document, delegations, now)
