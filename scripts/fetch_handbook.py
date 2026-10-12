"""Fetch a curated subset of the public GitLab Handbook and build its ACL file.

The GitLab Handbook (https://handbook.gitlab.com) is MIT licensed, real-world
company policy content. This script downloads a pinned snapshot of selected
pages, strips Hugo front matter / shortcodes, and writes:

    data/handbook/<document_id>.md   cleaned page text
    data/handbook_acl.json           document metadata + access control
    data/handbook/NOTICE.md          attribution and licence notice

IMPORTANT: the handbook is public in reality. The classifications and
allowed_roles below are a DEMO access policy assigned by department so that
TrustRAG's authorization layer has something realistic to enforce. They are
not GitLab's own access rules.

Usage:
    python scripts/fetch_handbook.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PROJECT = "gitlab-com/content-sites/handbook"
# Pinned commit so the corpus (and evaluation numbers) are reproducible.
PINNED_REF = "6f045e41f4c7e4e28cfb72271d01cf0b87dc5533"
PINNED_DATE = "2026-10-12T10:24:04Z"
API_BASE = "https://gitlab.com/api/v4/projects/" + urllib.parse.quote(PROJECT, safe="")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "data", "handbook")
ACL_PATH = os.path.join(ROOT, "data", "handbook_acl.json")
FIXTURE_SOURCE = os.path.join(ROOT, "data", "sample_docs", "prompt_injection_test.md")

MIN_CHARS = 800
MAX_CHARS = 65_000

ALL_ROLES = ["employee", "manager", "admin"]

# Demo access policy, assigned per department (see module docstring).
DEPARTMENTS = [
    {
        "key": "people",
        "classification": "internal",
        "owner_id": "casey_admin",
        "allowed_roles": ALL_ROLES,
        "pages": [
            "people-group/anti-harassment.md",
            "people-group/promotions-transfers.md",
            "people-group/relocation.md",
            "people-group/contracts-probation-periods.md",
            "people-group/guidance-on-feedback.md",
            "people-group/360-feedback.md",
            "people-group/visas.md",
            "people-group/team-member-relations.md",
            "people-group/celebrations.md",
            "people-group/time-off-and-absence/_index.md",
            "people-group/time-off-and-absence/leave-types.md",
            "people-group/time-off-and-absence/time-off-types.md",
            "people-group/time-off-and-absence/time-away-philosophy.md",
        ],
    },
    {
        "key": "engineering",
        "classification": "internal",
        "owner_id": "casey_admin",
        "allowed_roles": ALL_ROLES,
        "pages": [
            "engineering/incident-management.md",
            "engineering/on-call.md",
            "engineering/performance.md",
            "engineering/recognition.md",
            "engineering/error-budgets/_index.md",
            "engineering/open-source/_index.md",
            "engineering/releases/_index.md",
        ],
    },
    {
        "key": "finance",
        "classification": "restricted",
        "owner_id": "bob_manager",
        "allowed_roles": ["manager", "admin"],
        "pages": [
            "finance/expenses.md",
            "finance/spending-company-money.md",
            "finance/authorization-matrix.md",
            "finance/payroll.md",
            "finance/sales-comp-plan.md",
            "finance/investor-relations.md",
            "finance/committee-composition.md",
            "finance/travel/_index.md",
            "finance/procurement/_index.md",
            "finance/procurement/virtual-cards.md",
            "finance/procurement/consultants.md",
            "finance/procurement/contingent-worker-policy.md",
            "finance/procurement/individual-use-software.md",
        ],
    },
    {
        "key": "security",
        "classification": "restricted",
        "owner_id": "casey_admin",
        "allowed_roles": ["manager", "admin"],
        "pages": [
            "security/password-guidelines.md",
            "security/responding-to-ransomware.md",
            "security/root-cause-analysis.md",
            "security/information-system-contingency-plan-iscp.md",
            "security/external-secret-storage.md",
            "security/network-isolation.md",
            "security/security-change-management-procedure.md",
            "security/isms.md",
            "security/controlled-document-procedure.md",
            "security/security-and-technology-policy-exception.md",
            "security/security-observations-risk-management.md",
            "security/pgp_process.md",
        ],
    },
    {
        "key": "legal",
        "classification": "confidential",
        "owner_id": "casey_admin",
        "allowed_roles": ["admin"],
        "pages": [
            "legal/anti-corruption-policy.md",
            "legal/anti-fraud-policy.md",
            "legal/anti-retaliation-policy.md",
            "legal/whistleblowing.md",
            "legal/record-retention-policy.md",
            "legal/trade-compliance.md",
            "legal/employment-law.md",
            "legal/gitlab-related-party-transactions-policy.md",
            "legal/risk-management-dispute-resolution.md",
            "legal/competitor-discussion-guidelines.md",
        ],
    },
    {
        "key": "compensation",
        "classification": "confidential",
        "owner_id": "casey_admin",
        "allowed_roles": ["admin"],
        "pages": [
            "total-rewards/incentives.md",
            "total-rewards/stock-options.md",
            "total-rewards/compensation/_index.md",
            "total-rewards/benefits/_index.md",
            "total-rewards/benefits/parental-leave-toolkit.md",
        ],
    },
]

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TITLE_RE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)
_SHORTCODE_RE = re.compile(r"\{\{[<%].*?[>%]\}\}", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>\n]*>")
_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\([^)]*\)")
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


def fetch_raw(path: str) -> str | None:
    file_path = urllib.parse.quote(f"content/handbook/{path}", safe="")
    url = f"{API_BASE}/repository/files/{file_path}/raw?ref={PINNED_REF}"
    request = urllib.request.Request(url, headers={"User-Agent": "trustrag-fetch-handbook"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code == 429 or exc.code >= 500:
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError:
            time.sleep(2 * (attempt + 1))
    return None


def clean_page(raw: str, fallback_title: str) -> tuple[str, str]:
    """Returns (title, cleaned_markdown)."""
    title = fallback_title
    body = raw
    match = _FRONT_MATTER_RE.match(raw)
    if match:
        title_match = _TITLE_RE.search(match.group(1))
        if title_match:
            title = title_match.group(1).strip().strip("\"'")
        body = raw[match.end():]

    body = _HTML_COMMENT_RE.sub("", body)
    body = _SHORTCODE_RE.sub("", body)
    body = _IMAGE_RE.sub("", body)
    body = _LINK_RE.sub(r"\1", body)
    body = _HTML_TAG_RE.sub("", body)
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return title, f"# {title}\n\n{body}\n"


def document_id_for(dept_key: str, page: str) -> str:
    parts = page[: -len(".md")].split("/")[1:]
    if parts and parts[-1] == "_index":
        parts = parts[:-1] or ["overview"]
    slug = re.sub(r"[^a-z0-9]+", "_", "_".join(parts).lower()).strip("_")
    return f"{dept_key}_{slug}"


def main() -> int:
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    documents = []
    skipped = []

    for dept in DEPARTMENTS:
        for page in dept["pages"]:
            raw = fetch_raw(page)
            if raw is None:
                skipped.append((page, "not found"))
                continue
            document_id = document_id_for(dept["key"], page)
            title, text = clean_page(raw, fallback_title=document_id)
            if len(text) < MIN_CHARS:
                skipped.append((page, f"too short ({len(text)} chars)"))
                continue
            if len(text) > MAX_CHARS:
                skipped.append((page, f"too long ({len(text)} chars)"))
                continue

            file_name = f"{document_id}.md"
            with open(os.path.join(OUT_DIR, file_name), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            documents.append(
                {
                    "document_id": document_id,
                    "title": title,
                    "file_name": file_name,
                    "classification": dept["classification"],
                    "owner_id": dept["owner_id"],
                    "allowed_roles": dept["allowed_roles"],
                    "allowed_users": [],
                    "created_at": PINNED_DATE,
                    "department": dept["key"],
                    "source_url": f"https://handbook.gitlab.com/handbook/{page[:-3].removesuffix('_index')}",
                }
            )
            print(f"  ok   {document_id:55s} {len(text):6d} chars")

    # Deliberately malicious, TrustRAG-authored test fixture (not GitLab
    # content) so the document-injection quarantine can be demonstrated live.
    fixture_name = "fixture_vendor_faq_injection.md"
    shutil.copyfile(FIXTURE_SOURCE, os.path.join(OUT_DIR, fixture_name))
    documents.append(
        {
            "document_id": "fixture_vendor_faq_injection",
            "title": "Vendor FAQ — Security Test Fixture",
            "file_name": fixture_name,
            "classification": "internal_untrusted_test_fixture",
            "owner_id": "casey_admin",
            "allowed_roles": ALL_ROLES,
            "allowed_users": [],
            "created_at": PINNED_DATE,
            "department": "fixture",
            "source_url": "",
        }
    )

    with open(ACL_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"documents": documents}, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with open(os.path.join(OUT_DIR, "NOTICE.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "# Attribution\n\n"
            "The Markdown files in this directory (except `fixture_vendor_faq_injection.md`,\n"
            "which is a TrustRAG-authored security test fixture) are cleaned copies of pages\n"
            "from the GitLab Handbook.\n\n"
            f"- Source: https://gitlab.com/{PROJECT}\n"
            f"- Snapshot commit: `{PINNED_REF}` ({PINNED_DATE})\n"
            "- Licence: MIT, Copyright (c) GitLab B.V.\n"
            "  https://gitlab.com/gitlab-com/content-sites/handbook/-/blob/main/LICENSE\n\n"
            "Front matter, Hugo shortcodes, images, HTML tags and link targets were removed\n"
            "by `scripts/fetch_handbook.py`; the wording is otherwise unchanged.\n\n"
            "The handbook is public. The classifications and role restrictions in\n"
            "`data/handbook_acl.json` are a demo access policy invented for TrustRAG and do\n"
            "not reflect GitLab's own access rules.\n"
        )

    print(f"\nWrote {len(documents)} documents to {os.path.relpath(OUT_DIR, ROOT)}")
    for page, reason in skipped:
        print(f"  skip {page}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
