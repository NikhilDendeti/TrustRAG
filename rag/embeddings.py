"""Embedding provider, isolated so it can be swapped without touching indexing
or retrieval logic.

Default: a deterministic local hashing embedding (no network calls, no API key
required) so indexing/retrieval/tests work fully offline. This keeps the
authorization-critical retrieval path testable without any external API key
(NFR: "no external AI key should be needed to run authorization and audit unit
tests").
"""
from __future__ import annotations

import hashlib
import math
import re
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
