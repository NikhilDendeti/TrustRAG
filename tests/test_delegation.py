from datetime import datetime, timedelta, timezone

import pytest

from auth.permissions import Document, User
from delegation.service import DelegationError, create_delegation, delegation_status, revoke_delegation

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def make_document(**overrides) -> Document:
    defaults = dict(
        document_id="finance_forecast",
        title="Finance Forecast",
        file_name="finance_forecast.txt",
        classification="confidential",
        owner_id="bob_manager",
        allowed_roles=("manager",),
        allowed_users=(),
        created_at="2026-01-01T00:00:00Z",
    )
    defaults.update(overrides)
    return Document(**defaults)


def test_authorized_grantor_can_delegate_accessible_document():
    grantor = User("bob_manager", "Bob", ("manager",))
    grantee = User("alice_employee", "Alice", ("employee",))
    doc = make_document()
    expires = (NOW + timedelta(days=2)).isoformat()

    grant = create_delegation(grantor, grantee, doc, expires, [], now=NOW)

    assert grant.grantor_id == "bob_manager"
    assert grant.grantee_id == "alice_employee"
    assert grant.document_id == "finance_forecast"
    assert grant.revoked_at is None


def test_grantor_without_access_cannot_delegate():
    grantor = User("alice_employee", "Alice", ("employee",))
    grantee = User("dave_employee", "Dave", ("employee",))
    doc = make_document()  # only managers/admins allowed
    expires = (NOW + timedelta(days=2)).isoformat()

    with pytest.raises(DelegationError):
        create_delegation(grantor, grantee, doc, expires, [], now=NOW)


def test_expires_at_must_be_after_created_at():
    grantor = User("bob_manager", "Bob", ("manager",))
    grantee = User("alice_employee", "Alice", ("employee",))
    doc = make_document()
    past_expiry = (NOW - timedelta(days=1)).isoformat()

    with pytest.raises(DelegationError):
        create_delegation(grantor, grantee, doc, past_expiry, [], now=NOW)


def test_delegation_requires_specific_document_id():
    grantor = User("bob_manager", "Bob", ("manager",))
    grantee = User("alice_employee", "Alice", ("employee",))
    doc = make_document(document_id="")
    expires = (NOW + timedelta(days=1)).isoformat()

    with pytest.raises(DelegationError):
        create_delegation(grantor, grantee, doc, expires, [], now=NOW)


def test_revoke_by_grantor_succeeds_and_status_updates():
    grantor = User("bob_manager", "Bob", ("manager",))
    grantee = User("alice_employee", "Alice", ("employee",))
    doc = make_document()
    expires = (NOW + timedelta(days=2)).isoformat()
    grant = create_delegation(grantor, grantee, doc, expires, [], now=NOW)

    assert delegation_status(grant, NOW) == "active"

    updated = revoke_delegation(grant.grant_id, grantor, [grant], now=NOW)
    revoked_grant = updated[0]

    assert revoked_grant.revoked_at is not None
    assert delegation_status(revoked_grant, NOW) == "revoked"


def test_revoke_by_non_grantor_is_denied():
    grantor = User("bob_manager", "Bob", ("manager",))
    grantee = User("alice_employee", "Alice", ("employee",))
    stranger = User("casey_admin", "Casey", ("admin",))
    doc = make_document()
    expires = (NOW + timedelta(days=2)).isoformat()
    grant = create_delegation(grantor, grantee, doc, expires, [], now=NOW)

    with pytest.raises(DelegationError):
        revoke_delegation(grant.grant_id, stranger, [grant], now=NOW)


def test_delegation_status_reports_expired():
    grantor = User("bob_manager", "Bob", ("manager",))
    grantee = User("alice_employee", "Alice", ("employee",))
    doc = make_document()
    expires = (NOW + timedelta(hours=1)).isoformat()
    grant = create_delegation(grantor, grantee, doc, expires, [], now=NOW)

    later = NOW + timedelta(hours=2)
    assert delegation_status(grant, later) == "expired"
