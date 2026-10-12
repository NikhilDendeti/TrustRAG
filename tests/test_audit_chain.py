import json
import os

import pytest

from audit.hash_chain import HashChainAuditLog, verify_chain


@pytest.fixture
def log_path(tmp_path) -> str:
    return str(tmp_path / "audit_log.jsonl")


def test_verification_passes_on_unchanged_chain(log_path):
    log = HashChainAuditLog(log_path)
    log.append("login", "alice_employee", {"outcome": "ok"})
    log.append("query_submitted", "alice_employee", {"query_id": "q1"})
    log.append("retrieval_completed", "alice_employee", {"outcome": "answered"})

    result = log.verify()
    assert result.valid is True
    assert result.checked_count == 3


def test_verification_fails_after_modifying_an_event(log_path):
    log = HashChainAuditLog(log_path)
    log.append("login", "alice_employee", {"outcome": "ok"})
    log.append("query_submitted", "alice_employee", {"query_id": "q1"})

    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()
    tampered = json.loads(lines[0])
    tampered["actor_id"] = "mallory"
    lines[0] = json.dumps(tampered) + "\n"
    with open(log_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    result = HashChainAuditLog(log_path).verify()
    assert result.valid is False
    assert result.first_invalid_sequence == 1


def test_verification_fails_after_deleting_an_event(log_path):
    log = HashChainAuditLog(log_path)
    log.append("login", "alice_employee", {"outcome": "ok"})
    log.append("query_submitted", "alice_employee", {"query_id": "q1"})
    log.append("retrieval_completed", "alice_employee", {"outcome": "answered"})

    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()
    del lines[1]  # remove the middle event
    with open(log_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    result = HashChainAuditLog(log_path).verify()
    assert result.valid is False


def test_verification_fails_after_reordering_events(log_path):
    log = HashChainAuditLog(log_path)
    log.append("login", "alice_employee", {"outcome": "ok"})
    log.append("query_submitted", "alice_employee", {"query_id": "q1"})

    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()
    lines.reverse()
    with open(log_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    result = HashChainAuditLog(log_path).verify()
    assert result.valid is False


def test_genesis_hash_used_for_first_event(log_path):
    from audit.hash_chain import GENESIS_HASH

    log = HashChainAuditLog(log_path)
    event = log.append("login", "alice_employee", {"outcome": "ok"})
    assert event.previous_hash == GENESIS_HASH


def test_empty_chain_verifies_as_valid(log_path):
    log = HashChainAuditLog(log_path)
    result = log.verify()
    assert result.valid is True
    assert result.checked_count == 0


def test_malformed_record_raises_instead_of_silently_passing(log_path):
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("{not valid json\n")

    with pytest.raises(Exception):
        HashChainAuditLog(log_path).read_all()
