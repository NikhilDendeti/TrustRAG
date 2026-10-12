"""Read and validate sample documents, demo users, and ACL metadata from disk."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from auth.permissions import Delegation, Document, User, validate_document


class IngestionError(ValueError):
    pass


@dataclass(frozen=True)
class LoadedCorpus:
    documents: list[Document]
    rejected: list[str]


def load_users(path: str) -> list[User]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    users = []
    for entry in raw.get("users", []):
        user_id = entry.get("user_id")
        roles = entry.get("roles")
        if not user_id or not roles:
            continue
        users.append(
            User(
                user_id=user_id,
                display_name=entry.get("display_name", user_id),
                roles=tuple(roles),
            )
        )
    return users


def load_documents(acl_path: str, documents_dir: str) -> LoadedCorpus:
    """Loads document ACL metadata and validates it; invalid entries are rejected
    rather than silently granted default access, per the fail-closed business rule.
    """
    with open(acl_path, encoding="utf-8") as f:
        raw = json.load(f)

    documents: list[Document] = []
    rejected: list[str] = []

    for entry in raw.get("documents", []):
        try:
            document = Document(
                document_id=entry["document_id"],
                title=entry["title"],
                file_name=entry["file_name"],
                classification=entry["classification"],
                owner_id=entry["owner_id"],
                allowed_roles=tuple(entry.get("allowed_roles", [])),
                allowed_users=tuple(entry.get("allowed_users", [])),
                created_at=entry.get("created_at", ""),
            )
        except KeyError:
            rejected.append(entry.get("document_id", "<unknown>"))
            continue

        if not validate_document(document):
            rejected.append(document.document_id)
            continue

        file_path = os.path.join(documents_dir, document.file_name)
        if not os.path.isfile(file_path):
            rejected.append(document.document_id)
            continue

        documents.append(document)

    return LoadedCorpus(documents=documents, rejected=rejected)


def load_document_text(documents_dir: str, document: Document) -> str:
    file_path = os.path.join(documents_dir, document.file_name)
    with open(file_path, encoding="utf-8") as f:
        return f.read()


def load_delegations(path: str) -> list[Delegation]:
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    delegations = []
    for entry in raw.get("delegations", []):
        try:
            delegations.append(
                Delegation(
                    grant_id=entry["grant_id"],
                    grantor_id=entry["grantor_id"],
                    grantee_id=entry["grantee_id"],
                    document_id=entry["document_id"],
                    created_at=entry["created_at"],
                    expires_at=entry["expires_at"],
                    revoked_at=entry.get("revoked_at"),
                    reason=entry.get("reason"),
                )
            )
        except KeyError:
            continue
    return delegations


def save_delegations(path: str, delegations: list[Delegation]) -> None:
    payload = {
        "delegations": [
            {
                "grant_id": d.grant_id,
                "grantor_id": d.grantor_id,
                "grantee_id": d.grantee_id,
                "document_id": d.document_id,
                "created_at": d.created_at,
                "expires_at": d.expires_at,
                "revoked_at": d.revoked_at,
                "reason": d.reason,
            }
            for d in delegations
        ]
    }
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp_path, path)
