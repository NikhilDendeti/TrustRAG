import dataclasses

from auth.permissions import Document, User, get_authorized_document_ids
from ingestion.loader import load_documents, load_users
from rag.embeddings import LOCAL_HASHING_MODEL, resolve_embedding_function
from rag.indexer import _CHUNK_SIZE_CHARS, ChromaIndex, chunk_text

DOC = Document(
    document_id="policy",
    title="Policy",
    file_name="policy.md",
    classification="internal",
    owner_id="casey_admin",
    allowed_roles=("employee",),
    allowed_users=(),
    created_at="2026-01-01T00:00:00Z",
)


def test_oversized_paragraph_is_split_within_chunk_size():
    table = "\n".join(f"| row {i} | " + "value " * 12 + "|" for i in range(40))
    long_sentence = "word " * 400
    chunks = chunk_text("doc", f"Intro paragraph.\n\n{table}\n\n{long_sentence}")

    assert len(chunks) > 3
    assert all(len(chunk) <= _CHUNK_SIZE_CHARS for chunk in chunks)
    assert "row 39" in "\n".join(chunks)


def test_unknown_embedding_model_falls_back_to_offline_hashing():
    resolved = resolve_embedding_function("no-such-model")
    assert resolved.name == LOCAL_HASHING_MODEL
    assert resolved.fallback_reason


def test_ensure_indexed_rebuilds_only_when_corpus_changes():
    index = ChromaIndex(in_memory=True)
    index.reset()
    texts = {"policy": "Annual leave is 25 days."}

    assert index.ensure_indexed([DOC], texts) is True
    assert index.ensure_indexed([DOC], texts) is False

    assert index.ensure_indexed([DOC], {"policy": "Annual leave is 30 days."}) is True

    # An ACL change must also invalidate the index fingerprint.
    restricted = dataclasses.replace(DOC, allowed_roles=("admin",))
    assert index.ensure_indexed([restricted], {"policy": "Annual leave is 30 days."}) is True


def test_shipped_handbook_corpus_loads_and_enforces_department_policy():
    corpus = load_documents("data/handbook_acl.json", "data/handbook")
    users = {u.user_id: u for u in load_users("data/demo_users.json")}

    assert corpus.rejected == []
    assert len(corpus.documents) >= 50

    def departments(user: User) -> set[str]:
        ids = get_authorized_document_ids(user, corpus.documents, [])
        return {document_id.split("_")[0] for document_id in ids}

    assert departments(users["alice_employee"]) == {"people", "engineering", "fixture"}
    assert departments(users["bob_manager"]) == {
        "people", "engineering", "fixture", "finance", "security",
    }
    assert departments(users["casey_admin"]) == {
        "people", "engineering", "fixture", "finance", "security", "legal", "compensation",
    }
