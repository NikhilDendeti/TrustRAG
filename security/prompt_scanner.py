"""Heuristic prompt-injection indicator rules.

This is a warning/mitigation layer, not a guarantee (BRD business rule #9).
Absence of a match does NOT mean a prompt is safe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    severity: Severity
    evidence: str
    explanation: str


@dataclass(frozen=True)
class _Rule:
    rule_id: str
    title: str
    severity: Severity
    explanation: str
    pattern: re.Pattern


_RULES: list[_Rule] = [
    _Rule(
        rule_id="PI-001",
        title="Instruction override attempt",
        severity=Severity.HIGH,
        explanation=(
            "The prompt asks the assistant to ignore, forget, or override its "
            "prior instructions or system rules."
        ),
        pattern=re.compile(
            r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|above|all)\b.{0,40}\b(instruction|rule|prompt|policy)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    _Rule(
        rule_id="PI-002",
        title="System/developer prompt extraction attempt",
        severity=Severity.HIGH,
        explanation=(
            "The prompt asks the assistant to reveal its hidden system prompt, "
            "developer instructions, or internal configuration."
        ),
        pattern=re.compile(
            r"\b(reveal|show|print|leak|expose)\b.{0,40}\b(system prompt|developer prompt|hidden (instructions|prompt)|internal (instructions|configuration))",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    _Rule(
        rule_id="PI-003",
        title="Safeguard bypass / secret disclosure attempt",
        severity=Severity.HIGH,
        explanation=(
            "The prompt asks the assistant to bypass its safeguards, act without "
            "restrictions, or disclose secrets/credentials."
        ),
        pattern=re.compile(
            r"\b(bypass|disable|turn off|get around)\b.{0,40}\b(safeguard|restriction|filter|safety|guardrail)"
            r"|\b(reveal|disclose|give me)\b.{0,40}\b(api key|password|secret|credential)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    _Rule(
        rule_id="PI-004",
        title="Request to access restricted/confidential documents",
        severity=Severity.MEDIUM,
        explanation=(
            "The prompt explicitly asks for confidential, restricted, or "
            "unauthorized documents or data."
        ),
        pattern=re.compile(
            r"\b(confidential|restricted|classified|unauthorized)\b.{0,40}\b(document|file|data|information)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    _Rule(
        rule_id="PI-005",
        title="Role-play / persona override attempt",
        severity=Severity.LOW,
        explanation=(
            "The prompt asks the assistant to adopt a persona explicitly "
            "intended to remove its normal rules (e.g. 'DAN', 'no restrictions' "
            "personas)."
        ),
        pattern=re.compile(
            r"\b(pretend|act as|roleplay)\b.{0,40}\b(no (rules|restrictions|limits)|unrestricted|jailbroken)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
]


def scan_prompt(prompt: str) -> list[Finding]:
    """Runs all heuristic rules against the prompt and returns structured findings.

    Findings are ordered by severity (high first) for display convenience.
    """
    findings: list[Finding] = []
    for rule in _RULES:
        match = rule.pattern.search(prompt)
        if match:
            evidence = match.group(0).strip()
            findings.append(
                Finding(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    severity=rule.severity,
                    evidence=evidence[:200],
                    explanation=rule.explanation,
                )
            )

    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    findings.sort(key=lambda finding: order[finding.severity])
    return findings


def policy_decision(findings: list[Finding]) -> str:
    """MVP policy: block on any HIGH severity finding, warn-and-continue otherwise.

    This exact policy must be documented in the UI as well (see app.py / About page).
    """
    if any(finding.severity == Severity.HIGH for finding in findings):
        return "block"
    if findings:
        return "warn"
    return "allow"
