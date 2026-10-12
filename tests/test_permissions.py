from datetime import datetime, timedelta, timezone

from auth.permissions import (
    Delegation,
    Document,
    User,
    get_authorized_document_ids,
    is_authorized,
    validate_document,
)

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def make_document(**overrides) -> Document:
    defaults = dict(
        document_id="doc1",
        title="Doc 1",
        file_name="doc1.txt",
        classification="internal",
        owner_id="bob_manager",
        allowed_roles=("employee",),
        allowed_users=(),
        created_at="2026-01-01T00:00:00Z",
    )
    defaults.update(overrides)
    return Document(**defaults)


def test_role_based_access_allows_matching_role():
    user = User("alice", "Alice", ("employee",))
    doc = make_document(allowed_roles=("employee", "manager"))
    assert is_authorized(user, doc, [], NOW) is True


def test_role_based_access_denies_non_matching_role():
    user = User("alice", "Alice", ("employee",))
    doc = make_document(allowed_roles=("manager",))
    assert is_authorized(user, doc, [], NOW) is False


def test_direct_user_permission_grants_access_regardless_of_role():
    user = User("dave", "Dave", ("employee",))
    doc = make_document(allowed_roles=("manager",), allowed_users=("dave",))
    assert is_authorized(user, doc, [], NOW) is True


def test_admin_bypass_is_explicit_and_applies():
    admin = User("casey_admin", "Casey", ("admin",))
    doc = make_document(allowed_roles=("manager",))
    assert is_authorized(admin, doc, [], NOW) is True


def test_get_authorized_document_ids_filters_correctly():
    user = User("alice", "Alice", ("employee",))
    docs = [
        make_document(document_id="public", allowed_roles=("employee",)),
        make_document(document_id="finance", allowed_roles=("manager",)),
    ]
    assert get_authorized_document_ids(user, docs, [], NOW) == {"public"}


def test_malformed_document_fails_closed():
    bad_doc = make_document(classification="")
    user = User("alice", "Alice", ("employee",))
    assert validate_document(bad_doc) is False
    assert is_authorized(user, bad_doc, [], NOW) is False


def test_invalid_user_fails_closed():
    doc = make_document()
    assert is_authorized(User("", "", ()), doc, [], NOW) is False


def test_valid_delegation_grants_access():
    user = User("alice", "Alice", ("employee",))
    doc = make_document(document_id="finance_forecast", allowed_roles=("manager",))
    delegation = Delegation(
        grant_id="g1",
        grantor_id="bob_manager",
        grantee_id="alice",
        document_id="finance_forecast",
        created_at=(NOW - timedelta(days=1)).isoformat(),
        expires_at=(NOW + timedelta(days=1)).isoformat(),
    )
    assert is_authorized(user, doc, [delegation], NOW) is True


def test_expired_delegation_denies_access():
    user = User("alice", "Alice", ("employee",))
    doc = make_document(document_id="finance_forecast", allowed_roles=("manager",))
    delegation = Delegation(
        grant_id="g1",
        grantor_id="bob_manager",
        grantee_id="alice",
        document_id="finance_forecast",
        created_at=(NOW - timedelta(days=2)).isoformat(),
        expires_at=(NOW - timedelta(days=1)).isoformat(),
    )
    assert is_authorized(user, doc, [delegation], NOW) is False


def test_revoked_delegation_denies_access():
    user = User("alice", "Alice", ("employee",))
    doc = make_document(document_id="finance_forecast", allowed_roles=("manager",))
    delegation = Delegation(
        grant_id="g1",
        grantor_id="bob_manager",
        grantee_id="alice",
        document_id="finance_forecast",
        created_at=(NOW - timedelta(days=2)).isoformat(),
        expires_at=(NOW + timedelta(days=1)).isoformat(),
        revoked_at=(NOW - timedelta(hours=1)).isoformat(),
    )
    assert is_authorized(user, doc, [delegation], NOW) is False


def test_delegation_for_different_document_does_not_grant_access():
    user = User("alice", "Alice", ("employee",))
    doc = make_document(document_id="finance_forecast", allowed_roles=("manager",))
    delegation = Delegation(
        grant_id="g1",
        grantor_id="bob_manager",
        grantee_id="alice",
        document_id="some_other_doc",
        created_at=(NOW - timedelta(days=1)).isoformat(),
        expires_at=(NOW + timedelta(days=1)).isoformat(),
    )
    assert is_authorized(user, doc, [delegation], NOW) is False
