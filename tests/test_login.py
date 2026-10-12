from auth.login import Credential, authenticate, hash_password, verify_password


def make_credentials() -> list[Credential]:
    return [
        Credential(user_id="alice_employee", password_hash=hash_password("alice123")),
        Credential(user_id="bob_manager", password_hash=hash_password("bob123")),
    ]


def test_correct_password_authenticates():
    assert authenticate("alice_employee", "alice123", make_credentials()) == "alice_employee"


def test_wrong_password_is_denied():
    assert authenticate("alice_employee", "wrong-password", make_credentials()) is None


def test_unknown_username_is_denied():
    assert authenticate("mallory", "whatever", make_credentials()) is None


def test_empty_username_or_password_is_denied():
    assert authenticate("", "alice123", make_credentials()) is None
    assert authenticate("alice_employee", "", make_credentials()) is None
    assert authenticate("", "", make_credentials()) is None


def test_password_for_wrong_user_is_denied():
    # bob's password must not authenticate alice's account
    assert authenticate("alice_employee", "bob123", make_credentials()) is None


def test_verify_password_roundtrip():
    hashed = hash_password("super-secret")
    assert verify_password("super-secret", hashed) is True
    assert verify_password("not-it", hashed) is False
