"""Create, validate, expire, and revoke scoped time-limited access grants."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from auth.permissions import Delegation, Document, User, can_delegate_document


class DelegationError(ValueError):
    pass


def _parse_iso(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def create_delegation(
    grantor: User,
    grantee: User,
    document: Document,
    expires_at: str,
    existing_delegations: list[Delegation],
    reason: str | None = None,
    now: datetime | None = None,
) -> Delegation:
    """Validates and creates a new document-scoped delegation.

    Raises DelegationError (never silently grants) if:
    - the grantor cannot access the document themselves,
    - expires_at is not strictly after created_at,
    - the document_id is missing (no wildcard/all-document grants allowed).
    """
    now = now or datetime.now(timezone.utc)

    if not document.document_id:
        raise DelegationError("A delegation must target a specific document_id.")

    if not can_delegate_document(grantor, document, existing_delegations, now):
        raise DelegationError(
            f"{grantor.user_id} is not authorized to delegate document "
            f"'{document.document_id}'."
        )

    created_at_dt = now
    try:
        expires_at_dt = _parse_iso(expires_at)
    except (ValueError, TypeError) as exc:
        raise DelegationError("expires_at must be a valid ISO-8601 timestamp.") from exc

    if expires_at_dt <= created_at_dt:
        raise DelegationError("expires_at must be strictly after created_at.")

    return Delegation(
        grant_id=f"grant_{uuid.uuid4().hex[:12]}",
        grantor_id=grantor.user_id,
        grantee_id=grantee.user_id,
        document_id=document.document_id,
        created_at=created_at_dt.isoformat(),
        expires_at=expires_at_dt.isoformat(),
        revoked_at=None,
        reason=reason,
    )


def revoke_delegation(
    grant_id: str,
    revoker: User,
    delegations: list[Delegation],
    now: datetime | None = None,
) -> list[Delegation]:
    """Marks a delegation as revoked. Only the original grantor may revoke it.

    Returns a new list with the matching delegation updated; raises if not found
    or if the revoker is not the grantor.
    """
    now = now or datetime.now(timezone.utc)
    updated: list[Delegation] = []
    found = False

    for delegation in delegations:
        if delegation.grant_id == grant_id:
            found = True
            if delegation.grantor_id != revoker.user_id:
                raise DelegationError(
                    "Only the original grantor may revoke this delegation."
                )
            updated.append(
                Delegation(
                    grant_id=delegation.grant_id,
                    grantor_id=delegation.grantor_id,
                    grantee_id=delegation.grantee_id,
                    document_id=delegation.document_id,
                    created_at=delegation.created_at,
                    expires_at=delegation.expires_at,
                    revoked_at=now.isoformat(),
                    reason=delegation.reason,
                )
            )
        else:
            updated.append(delegation)

    if not found:
        raise DelegationError(f"No delegation found with grant_id '{grant_id}'.")

    return updated


def delegation_status(delegation: Delegation, now: datetime | None = None) -> str:
    """Returns 'active', 'expired', or 'revoked' for display purposes."""
    now = now or datetime.now(timezone.utc)
    if delegation.revoked_at is not None:
        return "revoked"
    try:
        if now >= _parse_iso(delegation.expires_at):
            return "expired"
    except (ValueError, TypeError):
        return "expired"
    return "active"
