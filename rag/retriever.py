"""Authorized retrieval with a mandatory second ACL safeguard.

Security-critical: this module queries ChromaDB restricted to the caller's
authorized document IDs (the pre-query filter), AND re-validates every single
returned chunk against the authorization service before it is allowed to enter
model context (the post-retrieval safeguard). A chunk that fails the second
check is discarded and never reaches the LLM, even if it was returned due to an
indexing or filtering bug.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from auth.permissions import Delegation, Document, User, get_authorized_document_ids, is_authorized
from rag.indexer import ChromaIndex


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    title: str
    classification: str
    chunk_index: int
    text: str
    distance: float | None


@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    rejected_unauthorized_chunk_ids: list[str]


def _document_lookup(documents: list[Document]) -> dict[str, Document]:
    return {d.document_id: d for d in documents}


def retrieve_authorized_chunks(
    index: ChromaIndex,
    user: User,
    query_text: str,
    documents: list[Document],
    delegations: list[Delegation],
    top_k: int,
    now: datetime | None = None,
) -> RetrievalResult:
    authorized_ids = get_authorized_document_ids(user, documents, delegations, now)
    doc_by_id = _document_lookup(documents)

    raw_hits = index.query(query_text, document_ids=sorted(authorized_ids), top_k=top_k)

    safe_chunks: list[RetrievedChunk] = []
    rejected: list[str] = []

    for hit in raw_hits:
        metadata = hit["metadata"]
        document_id = metadata.get("document_id", "")
        document = doc_by_id.get(document_id)

        # Second, independent safeguard: re-check authorization per chunk,
        # never trust that the pre-query filter alone was sufficient.
        if document is None or not is_authorized(user, document, delegations, now):
            rejected.append(hit["chunk_id"])
            continue

        safe_chunks.append(
            RetrievedChunk(
                chunk_id=hit["chunk_id"],
                document_id=document_id,
                title=metadata.get("title", ""),
                classification=metadata.get("classification", ""),
                chunk_index=metadata.get("chunk_index", 0),
                text=hit["text"],
                distance=hit.get("distance"),
            )
        )

    return RetrievalResult(chunks=safe_chunks, rejected_unauthorized_chunk_ids=rejected)
