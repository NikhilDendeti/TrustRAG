"""Chunking, embedding, and ChromaDB indexing.

Chunk metadata (document ID, title, classification, owner, allowed roles/users)
travels with every chunk so the retriever can re-validate authorization on each
returned result, independent of the pre-query filter.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import chromadb

from auth.permissions import Document
from rag.embeddings import get_default_embedding_function

_COLLECTION_NAME = "trustrag_chunks"
_CHUNK_SIZE_CHARS = 600
_CHUNK_OVERLAP_CHARS = 100


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


def chunk_text(document_id: str, text: str) -> list[str]:
    """Deterministic fixed-size chunking with overlap, split on paragraph
    boundaries where possible for a small demo corpus."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
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


class ChromaIndex:
    """Thin wrapper around a ChromaDB collection used for authorized retrieval."""

    def __init__(self, persist_dir: str | None = None, in_memory: bool = False):
        if in_memory or not persist_dir:
            self._client = chromadb.Client()
        else:
            self._client = chromadb.PersistentClient(path=persist_dir)
        self._embedding_function = get_default_embedding_function()
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=self._embedding_function,
        )

    def reset(self) -> None:
        try:
            self._client.delete_collection(_COLLECTION_NAME)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=self._embedding_function,
        )

    def index_documents(self, documents: list[Document], texts_by_document_id: dict[str, str]) -> int:
        all_chunks: list[Chunk] = []
        for document in documents:
            text = texts_by_document_id.get(document.document_id, "")
            all_chunks.extend(build_chunks(document, text))

        if not all_chunks:
            return 0

        self._collection.upsert(
            ids=[c.chunk_id for c in all_chunks],
            documents=[c.text for c in all_chunks],
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
                for c in all_chunks
            ],
        )
        return len(all_chunks)

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
