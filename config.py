"""Configuration and environment loading for TrustRAG."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    google_api_key: str | None
    gemma_model: str
    embedding_model: str
    chroma_persist_dir: str
    audit_log_path: str
    demo_users_path: str
    documents_dir: str
    acl_path: str
    delegations_path: str
    retrieval_top_k: int

    @property
    def llm_configured(self) -> bool:
        return bool(self.google_api_key)


def load_settings() -> Settings:
    return Settings(
        google_api_key=os.environ.get("GOOGLE_API_KEY") or None,
        gemma_model=os.environ.get("GEMMA_MODEL", "gemma-4-26b-a4b-it"),
        embedding_model=os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        chroma_persist_dir=os.environ.get("CHROMA_PERSIST_DIR", "data/chroma_store"),
        audit_log_path=os.environ.get("AUDIT_LOG_PATH", "data/audit_log.jsonl"),
        demo_users_path=os.environ.get("DEMO_USERS_PATH", "data/demo_users.json"),
        documents_dir=os.environ.get("DOCUMENTS_DIR", "data/handbook"),
        acl_path=os.environ.get("ACL_PATH", "data/handbook_acl.json"),
        delegations_path=os.environ.get("DELEGATIONS_PATH", "data/delegations.json"),
        retrieval_top_k=int(os.environ.get("RETRIEVAL_TOP_K", "4")),
    )
