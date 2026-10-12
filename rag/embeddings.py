"""Embedding provider, isolated so it can be swapped without touching indexing
or retrieval logic.

The app uses `all-MiniLM-L6-v2` (see `resolve_embedding_function`). Tests and
the fallback path use a deterministic local hashing embedding (no network
calls, no API key) so indexing/retrieval work fully offline. This keeps the
authorization-critical retrieval path testable without any external API key
(NFR: "no external AI key should be needed to run authorization and audit unit
tests").
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_DIMENSIONS = 256


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _hash_embed_one(text: str) -> list[float]:
    vector = [0.0] * _DIMENSIONS
    tokens = _tokenize(text)
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % _DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class EmbeddingFunction(Protocol):
    def __call__(self, input: list[str]) -> list[list[float]]: ...


class LocalHashingEmbeddingFunction:
    """Deterministic, offline, dependency-free embedding function.

    Not a semantic embedding model — it is a reproducible bag-of-tokens hash
    projection, good enough for small-corpus demo retrieval without any
    external API or large model download.
    """

    def name(self) -> str:
        return "trustrag-local-hashing-v1"

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [_hash_embed_one(text) for text in input]

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self(input)

    def get_config(self) -> dict:
        return {}

    @staticmethod
    def build_from_config(config: dict) -> "LocalHashingEmbeddingFunction":
        return LocalHashingEmbeddingFunction()


def get_default_embedding_function() -> LocalHashingEmbeddingFunction:
    return LocalHashingEmbeddingFunction()


LOCAL_HASHING_MODEL = "trustrag-local-hashing-v1"
MINILM_MODEL = "all-MiniLM-L6-v2"


@dataclass(frozen=True)
class ResolvedEmbedding:
    function: EmbeddingFunction
    name: str
    fallback_reason: str | None = None


def resolve_embedding_function(model_name: str | None) -> ResolvedEmbedding:
    """Maps a configured model name to an embedding function.

    `all-MiniLM-L6-v2` is a real semantic sentence-embedding model, run locally
    through ONNX Runtime (bundled with ChromaDB — no API key, no PyTorch). The
    model weights (~80 MB) are downloaded once on first use. If it cannot be
    loaded (e.g. no network on first run), we fall back to the offline hashing
    embedding and report why, so the app still starts. Retrieval quality is a
    usability concern only: authorization never depends on the embedding.
    """
    if not model_name or model_name == LOCAL_HASHING_MODEL:
        return ResolvedEmbedding(LocalHashingEmbeddingFunction(), LOCAL_HASHING_MODEL)

    if model_name == MINILM_MODEL:
        try:
            from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

            function = ONNXMiniLM_L6_V2()
            function(["warm-up"])  # forces the one-time model download/load
            return ResolvedEmbedding(function, MINILM_MODEL)
        except Exception as exc:  # network/model failure must not stop the app
            return ResolvedEmbedding(
                LocalHashingEmbeddingFunction(),
                LOCAL_HASHING_MODEL,
                fallback_reason=f"{MINILM_MODEL} could not be loaded: {exc}",
            )

    return ResolvedEmbedding(
        LocalHashingEmbeddingFunction(),
        LOCAL_HASHING_MODEL,
        fallback_reason=f"Unknown EMBEDDING_MODEL '{model_name}'.",
    )
