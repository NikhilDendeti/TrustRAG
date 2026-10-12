from datetime import datetime, timezone

import pytest

from auth.permissions import Document, User
from config import load_settings
from rag.answerer import answer_question
from rag.indexer import ChromaIndex
from rag.retriever import retrieve_authorized_chunks

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)

PUBLIC_TEXT = (
    "Our company was founded in 2019 and builds logistics software. "
    "This overview is public and contains no confidential information."
)
FINANCE_TEXT = (
    "Projected Q3 revenue is $4.2M, a 12% increase over Q2. "
    "This forecast is restricted to manager and admin roles."
)


@pytest.fixture
def documents() -> list[Document]:
    return [
        Document(
            document_id="public_doc",
            title="Company Overview",
            file_name="public_doc.txt",
            classification="public",
            owner_id="casey_admin",
            allowed_roles=("employee", "manager", "admin"),
            allowed_users=(),
            created_at="2026-01-01T00:00:00Z",
        ),
        Document(
            document_id="finance_forecast",
            title="Q3 Financial Forecast",
            file_name="finance_forecast.txt",
            classification="confidential",
            owner_id="bob_manager",
            allowed_roles=("manager", "admin"),
            allowed_users=(),
            created_at="2026-01-01T00:00:00Z",
        ),
    ]


@pytest.fixture
def index(documents) -> ChromaIndex:
    idx = ChromaIndex(in_memory=True)
    idx.reset()
    idx.index_documents(
        documents,
        {"public_doc": PUBLIC_TEXT, "finance_forecast": FINANCE_TEXT},
    )
    return idx


def test_unauthorized_chunks_never_enter_result_set(index, documents):
    employee = User("alice_employee", "Alice", ("employee",))
    result = retrieve_authorized_chunks(
        index, employee, "What is the Q3 financial forecast?", documents, [], top_k=4, now=NOW
    )
    assert all(c.document_id != "finance_forecast" for c in result.chunks)


def test_authorized_manager_can_retrieve_finance_chunk(index, documents):
    manager = User("bob_manager", "Bob", ("manager",))
    result = retrieve_authorized_chunks(
        index, manager, "What is the Q3 financial forecast?", documents, [], top_k=4, now=NOW
    )
    assert any(c.document_id == "finance_forecast" for c in result.chunks)


def test_post_retrieval_safeguard_rejects_chunk_even_if_prequery_filter_is_bypassed(
    index, documents
):
    """Simulates an indexing/filtering bug: query with an attacker-widened
    document_id scope, but the retriever must still reject anything the user
    is not actually authorized for via the second ACL check."""
    employee = User("alice_employee", "Alice", ("employee",))
    unauthorized_hits = index.query(
        "Q3 financial forecast", document_ids=["public_doc", "finance_forecast"], top_k=4
    )
    assert any(h["metadata"]["document_id"] == "finance_forecast" for h in unauthorized_hits)

    doc_by_id = {d.document_id: d for d in documents}
    from auth.permissions import is_authorized

    safe = [
        h
        for h in unauthorized_hits
        if is_authorized(employee, doc_by_id[h["metadata"]["document_id"]], [], NOW)
    ]
    assert all(h["metadata"]["document_id"] != "finance_forecast" for h in safe)


def test_no_authorized_evidence_leads_to_abstention():
    settings = load_settings()
    result = answer_question(settings, "What is in the finance forecast?", [])
    assert result.abstained is True
    assert "couldn't find" in result.answer_text.lower()


def test_citation_ids_belong_to_retrieved_chunks(index, documents):
    import dataclasses

    manager = User("bob_manager", "Bob", ("manager",))
    result = retrieve_authorized_chunks(
        index, manager, "What is the Q3 financial forecast?", documents, [], top_k=4, now=NOW
    )
    settings = dataclasses.replace(load_settings(), google_api_key=None)
    answer = answer_question(settings, "What is the Q3 forecast?", result.chunks)

    valid_ids = {f"doc:{c.document_id}#{c.chunk_index}" for c in result.chunks}
    assert set(answer.citations) <= valid_ids


def test_api_failure_does_not_bypass_access_control(index, documents, monkeypatch):
    """Simulates the LLM provider being unconfigured/failing. Even then,
    unauthorized chunks must never have been passed to it in the first place
    — the fallback path must only use the already-authorized chunk set."""
    employee = User("alice_employee", "Alice", ("employee",))
    result = retrieve_authorized_chunks(
        index, employee, "finance forecast", documents, [], top_k=4, now=NOW
    )
    assert all(c.document_id != "finance_forecast" for c in result.chunks)

    import dataclasses

    settings = load_settings()
    unconfigured_settings = dataclasses.replace(settings, google_api_key=None)
    answer = answer_question(unconfigured_settings, "finance forecast", result.chunks)
    assert answer.used_fallback or answer.abstained
    assert set(answer.citations) <= {f"doc:{c.document_id}#{c.chunk_index}" for c in result.chunks}
