"""Quarantine retrieved chunks that look like indirect prompt injection.

Authorization decides which chunks a user MAY see. This guard is a separate,
later step: among the chunks the user is allowed to see, it withholds any whose
text appears to be giving orders to the assistant, so that text never enters
the model's context. It is a heuristic mitigation layered on top of the
system-prompt rule that passages are untrusted data — not a guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass

from rag.retriever import RetrievedChunk
from security.prompt_scanner import Finding, Severity, scan_document_text


@dataclass(frozen=True)
class QuarantinedChunk:
    chunk: RetrievedChunk
    findings: list[Finding]


@dataclass(frozen=True)
class GuardResult:
    clean_chunks: list[RetrievedChunk]
    quarantined: list[QuarantinedChunk]


def guard_retrieved_chunks(chunks: list[RetrievedChunk]) -> GuardResult:
    """Splits chunks into those safe to pass to the model and those withheld.

    A chunk is quarantined on any HIGH severity document finding.
    """
    clean: list[RetrievedChunk] = []
    quarantined: list[QuarantinedChunk] = []
    for chunk in chunks:
        findings = [f for f in scan_document_text(chunk.text) if f.severity == Severity.HIGH]
        if findings:
            quarantined.append(QuarantinedChunk(chunk=chunk, findings=findings))
        else:
            clean.append(chunk)
    return GuardResult(clean_chunks=clean, quarantined=quarantined)
