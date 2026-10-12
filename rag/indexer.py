"""Chunking, embedding, and ChromaDB indexing.

Chunk metadata (document ID, title, classification, owner, allowed roles/users)
travels with every chunk so the retriever can re-validate authorization on each
returned result, independent of the pre-query filter.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import chromadb

from auth.permissions import Document
from rag.embeddings import LOCAL_HASHING_MODEL, resolve_embedding_function

_COLLECTION_NAME = "trustrag_chunks"
_CHUNK_SIZE_CHARS = 600
_CHUNK_OVERLAP_CHARS = 100
_UPSERT_BATCH_SIZE = 500


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    title: str
    classification: str
    owner_id: str
    allowed_roles: tuple[str, ...]
    allowed_users: tuple[str, ...]
    chunk_index: int
    text: str


def _split_oversized(paragraph: str) -> list[str]:
    """Breaks a paragraph longer than the chunk size on line boundaries, then
    on word boundaries. Real documents contain long tables and bullet lists
    that would otherwise become one oversized chunk the embedding model
    silently truncates."""
    if len(paragraph) <= _CHUNK_SIZE_CHARS:
        return [paragraph]

    pieces: list[str] = []
    buffer = ""
    for line in paragraph.split("\n"):
        line = line.strip()
        while len(line) > _CHUNK_SIZE_CHARS:
            if buffer:
                pieces.append(buffer)
                buffer = ""
            cut = line.rfind(" ", 0, _CHUNK_SIZE_CHARS)
            if cut <= 0:
                cut = _CHUNK_SIZE_CHARS
            pieces.append(line[:cut])
            line = line[cut:].strip()
        if not line:
            continue
        candidate = f"{buffer}\n{line}" if buffer else line
        if len(candidate) <= _CHUNK_SIZE_CHARS:
            buffer = candidate
        else:
            pieces.append(buffer)
            buffer = line
    if buffer:
        pieces.append(buffer)
    return pieces


def chunk_text(document_id: str, text: str) -> list[str]:
    """Deterministic fixed-size chunking, split on paragraph boundaries where
    possible; oversized paragraphs are broken up by `_split_oversized`."""
    paragraphs = [
        piece
        for p in re.split(r"\n\s*\n", text)
        if p.strip()
        for piece in _split_oversized(p.strip())
    ]
    if not paragraphs:
        return []

    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
        if len(candidate) <= _CHUNK_SIZE_CHARS:
            buffer = candidate
        else:
            if buffer:
                chunks.append(buffer)
            buffer = paragraph
    if buffer:
        chunks.append(buffer)

    if not chunks:
        chunks = [text[i : i + _CHUNK_SIZE_CHARS] for i in range(0, len(text), _CHUNK_SIZE_CHARS)]

    return chunks


def build_chunks(document: Document, text: str) -> list[Chunk]:
    raw_chunks = chunk_text(document.document_id, text)
    return [
        Chunk(
            chunk_id=f"{document.document_id}::{idx}",
            document_id=document.document_id,
            title=document.title,
            classification=document.classification,
            owner_id=document.owner_id,
            allowed_roles=tuple(document.allowed_roles),
            allowed_users=tuple(document.allowed_users),
            chunk_index=idx,
            text=chunk,
        )
        for idx, chunk in enumerate(raw_chunks)
    ]


def corpus_fingerprint(
    documents: list[Document], texts_by_document_id: dict[str, str], embedding_name: str
) -> str:
    digest = hashlib.sha256()
    digest.update(f"{embedding_name}|{_CHUNK_SIZE_CHARS}".encode("utf-8"))
    for document in sorted(documents, key=lambda d: d.document_id):
        digest.update(repr(document).encode("utf-8"))
        digest.update(texts_by_document_id.get(document.document_id, "").encode("utf-8"))
    return digest.hexdigest()


class ChromaIndex:
    """Thin wrapper around a ChromaDB collection used for authorized retrieval."""

    def __init__(
        self,
        persist_dir: str | None = None,
        in_memory: bool = False,
        embedding_model: str | None = None,
    ):
        if in_memory or not persist_dir:
            self._client = chromadb.Client()
        else:
            self._client = chromadb.PersistentClient(path=persist_dir)

        resolved = resolve_embedding_function(embedding_model)
        self._embedding_function = resolved.function
        self.embedding_name = resolved.name
        self.embedding_fallback_reason = resolved.fallback_reason
        # One collection per embedding model: vectors from different models
        # must never be mixed in the same collection.
        self._collection_name = (
            _COLLECTION_NAME
            if resolved.name == LOCAL_HASHING_MODEL
            else f"{_COLLECTION_NAME}_{resolved.name}"
        )
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._embedding_function,
        )

    def reset(self, fingerprint: str | None = None) -> None:
        try:
            self._client.delete_collection(self._collection_name)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._embedding_function,
            metadata={"fingerprint": fingerprint} if fingerprint else None,
        )

    def index_documents(self, documents: list[Document], texts_by_document_id: dict[str, str]) -> int:
        all_chunks: list[Chunk] = []
        for document in documents:
            text = texts_by_document_id.get(document.document_id, "")
            all_chunks.extend(build_chunks(document, text))

        if not all_chunks:
            return 0

        for start in range(0, len(all_chunks), _UPSERT_BATCH_SIZE):
            batch = all_chunks[start : start + _UPSERT_BATCH_SIZE]
            self._collection.upsert(
                ids=[c.chunk_id for c in batch],
                documents=[c.text for c in batch],
                metadatas=[
                    {
                        "document_id": c.document_id,
                        "title": c.title,
                        "classification": c.classification,
                        "owner_id": c.owner_id,
                        "allowed_roles": ",".join(c.allowed_roles),
                        "allowed_users": ",".join(c.allowed_users),
                        "chunk_index": c.chunk_index,
                    }
                    for c in batch
                ],
            )
        return len(all_chunks)

    def count(self) -> int:
        return self._collection.count()

    def ensure_indexed(self, documents: list[Document], texts_by_document_id: dict[str, str]) -> bool:
        """Rebuilds the index only if the corpus, its ACL metadata, the chunking
        parameters, or the embedding model changed since the persisted index
        was built. Returns True if a rebuild happened.

        A stale index can never widen access: retrieval re-checks every chunk
        against the live ACL. The fingerprint only avoids re-embedding an
        unchanged corpus on every start.
        """
        fingerprint = corpus_fingerprint(documents, texts_by_document_id, self.embedding_name)
        stored = (self._collection.metadata or {}).get("fingerprint")
        if stored == fingerprint and self._collection.count() > 0:
            return False
        self.reset(fingerprint)
        self.index_documents(documents, texts_by_document_id)
        return True

    def query(self, query_text: str, document_ids: list[str], top_k: int) -> list[dict]:
        """Queries restricted to the given authorized document_ids.

        If document_ids is empty, returns no results rather than falling back
        to an unrestricted search.
        """
        if not document_ids:
            return []

        result = self._collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where={"document_id": {"$in": document_ids}},
        )

        hits = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0] if result.get("distances") else [None] * len(ids)

        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            hits.append(
                {
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": metadata,
                    "distance": distance,
                }
            )
        return hits
