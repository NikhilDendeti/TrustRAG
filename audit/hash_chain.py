"""Append-only, SHA-256 hash-chained audit log.

Honest limitation (per BRD business rule #10 / FR-8): this detects tampering with
the CURRENT chain as stored. It is not immutable against an attacker who can
rewrite the entire log file and recompute every hash from scratch. Production
deployments should pair this with protected external storage, digital
signatures, or trusted append-only checkpoints.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    timestamp: str
    event_type: str
    actor_id: str
    details: dict[str, Any]
    previous_hash: str
    event_hash: str


class AuditChainError(ValueError):
    pass


def canonicalize(
    sequence: int,
    timestamp: str,
    event_type: str,
    actor_id: str,
    details: dict[str, Any],
    previous_hash: str,
) -> bytes:
    """Deterministic canonical encoding used as the hash input."""
    payload = {
        "sequence": sequence,
        "timestamp": timestamp,
        "event_type": event_type,
        "actor_id": actor_id,
        "details": details,
        "previous_hash": previous_hash,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_event_hash(
    sequence: int,
    timestamp: str,
    event_type: str,
    actor_id: str,
    details: dict[str, Any],
    previous_hash: str,
) -> str:
    canonical = canonicalize(sequence, timestamp, event_type, actor_id, details, previous_hash)
    return hashlib.sha256(canonical).hexdigest()


class HashChainAuditLog:
    """A minimal append-only JSONL-backed hash-chained audit log."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if not os.path.isfile(path):
            open(path, "a", encoding="utf-8").close()

    def _read_events(self) -> list[AuditEvent]:
        events: list[AuditEvent] = []
        with open(self.path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    events.append(
                        AuditEvent(
                            sequence=raw["sequence"],
                            timestamp=raw["timestamp"],
                            event_type=raw["event_type"],
                            actor_id=raw["actor_id"],
                            details=raw["details"],
                            previous_hash=raw["previous_hash"],
                            event_hash=raw["event_hash"],
                        )
                    )
                except (json.JSONDecodeError, KeyError) as exc:
                    raise AuditChainError(
                        f"Malformed audit record at line {line_no}: {exc}"
                    ) from exc
        return events

    def append(self, event_type: str, actor_id: str, details: dict[str, Any] | None = None) -> AuditEvent:
        details = details or {}
        events = self._read_events()
        sequence = events[-1].sequence + 1 if events else 1
        previous_hash = events[-1].event_hash if events else GENESIS_HASH
        timestamp = datetime.now(timezone.utc).isoformat()

        event_hash = compute_event_hash(sequence, timestamp, event_type, actor_id, details, previous_hash)
        event = AuditEvent(
            sequence=sequence,
            timestamp=timestamp,
            event_type=event_type,
            actor_id=actor_id,
            details=details,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sequence": event.sequence,
                        "timestamp": event.timestamp,
                        "event_type": event.event_type,
                        "actor_id": event.actor_id,
                        "details": event.details,
                        "previous_hash": event.previous_hash,
                        "event_hash": event.event_hash,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        return event

    def read_all(self) -> list[AuditEvent]:
        return self._read_events()

    def verify(self) -> "VerificationResult":
        return verify_chain(self._read_events())


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    checked_count: int
    first_invalid_sequence: int | None = None
    reason: str | None = None


def verify_chain(events: list[AuditEvent]) -> VerificationResult:
    """Recomputes every hash and previous-hash link in order.

    Returns the first invalid sequence number without re-exposing full event
    payloads, per FR-8 / Journey 4.
    """
    expected_previous = GENESIS_HASH
    for idx, event in enumerate(events):
        expected_sequence = idx + 1
        if event.sequence != expected_sequence:
            return VerificationResult(
                valid=False,
                checked_count=idx,
                first_invalid_sequence=event.sequence,
                reason="Unexpected sequence number (possible reordering or deletion).",
            )
        if event.previous_hash != expected_previous:
            return VerificationResult(
                valid=False,
                checked_count=idx,
                first_invalid_sequence=event.sequence,
                reason="previous_hash does not match the prior event's hash.",
            )
        recomputed = compute_event_hash(
            event.sequence,
            event.timestamp,
            event.event_type,
            event.actor_id,
            event.details,
            event.previous_hash,
        )
        if recomputed != event.event_hash:
            return VerificationResult(
                valid=False,
                checked_count=idx,
                first_invalid_sequence=event.sequence,
                reason="Recomputed hash does not match stored event_hash (tampered content).",
            )
        expected_previous = event.event_hash

    return VerificationResult(valid=True, checked_count=len(events))
