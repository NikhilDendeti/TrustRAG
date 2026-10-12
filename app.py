"""TrustRAG Streamlit application.

Demo-only authentication: the login screen below checks a username/password
against a small hardcoded demo credential set (SHA-256 hashed, no salt/key
stretching). It is a hackathon-demo convenience, not production identity. See
Page 5 (About) for the full list of limitations.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import streamlit as st

from auth.login import authenticate
from auth.permissions import Document, User, get_authorized_document_ids, is_authorized
from audit.hash_chain import HashChainAuditLog
from config import load_settings
from delegation.service import DelegationError, create_delegation, delegation_status, revoke_delegation
from ingestion.loader import (
    load_credentials,
    load_delegations,
    load_document_text,
    load_documents,
    load_users,
    save_delegations,
)
from rag.answerer import answer_question
from rag.indexer import ChromaIndex
from rag.retriever import retrieve_authorized_chunks
from security.context_guard import guard_retrieved_chunks
from security.prompt_scanner import policy_decision, scan_prompt

st.set_page_config(page_title="TrustRAG — Secure Enterprise AI", layout="wide")

SETTINGS = load_settings()


@st.cache_resource
def get_audit_log() -> HashChainAuditLog:
    return HashChainAuditLog(SETTINGS.audit_log_path)


@st.cache_resource
def get_index_and_corpus():
    corpus = load_documents(SETTINGS.acl_path, SETTINGS.documents_dir)
    index = ChromaIndex(
        persist_dir=SETTINGS.chroma_persist_dir, embedding_model=SETTINGS.embedding_model
    )
    texts = {d.document_id: load_document_text(SETTINGS.documents_dir, d) for d in corpus.documents}
    index.ensure_indexed(corpus.documents, texts)
    return index, corpus


def get_users() -> list[User]:
    return load_users(SETTINGS.demo_users_path)


def get_delegations() -> list[Document]:
    return load_delegations(SETTINGS.delegations_path)


audit_log = get_audit_log()
users = get_users()
user_by_id = {u.user_id: u for u in users}

st.sidebar.title("TrustRAG")
st.sidebar.caption("Secure Enterprise AI — hackathon prototype")

# ---------------------------------------------------------------------------
# Login gate — demo-only authentication (see module docstring / About page)
# ---------------------------------------------------------------------------
if "auth_user_id" not in st.session_state:
    st.header("Sign in to TrustRAG")
    st.info(
        "**Demo authentication, not production login.** This checks a "
        "username/password against a small hardcoded demo credential set "
        "(SHA-256 hashed, no salt). It exists to give the demo a real login "
        "flow instead of a bare identity dropdown — it is not a security "
        "boundary. See *About and Limitations* after signing in."
    )

    with st.expander("Demo credentials (for this hackathon demo only)"):
        st.markdown(
            "| Username | Password | Role |\n"
            "|---|---|---|\n"
            "| `alice_employee` | `alice123` | employee |\n"
            "| `bob_manager` | `bob123` | manager, employee |\n"
            "| `casey_admin` | `casey123` | admin |"
        )

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", type="primary")

        if submitted:
            credentials = load_credentials(SETTINGS.demo_users_path)
            user_id = authenticate(username.strip(), password, credentials)
            if user_id is None:
                audit_log.append("login_failed", username.strip() or "<empty>", {"outcome": "denied"})
                st.error("Invalid username or password.")
            else:
                audit_log.append("login", user_id, {"outcome": "success"})
                st.session_state.auth_user_id = user_id
                st.rerun()

    st.stop()

current_user = user_by_id.get(st.session_state.auth_user_id)
if current_user is None:
    # Credential set changed since login (or stale session); fail closed by
    # forcing re-authentication rather than falling back to any default user.
    del st.session_state["auth_user_id"]
    st.rerun()

with st.spinner("Preparing the document index (first run embeds the whole corpus)…"):
    index, corpus = get_index_and_corpus()

if index.embedding_fallback_reason:
    st.sidebar.warning(
        "Using the offline hashing embedding (lower retrieval quality): "
        f"{index.embedding_fallback_reason}"
    )

if corpus.rejected:
    st.sidebar.warning(
        f"{len(corpus.rejected)} document(s) were rejected during ingestion due to "
        f"missing/invalid metadata and are not queryable: {', '.join(corpus.rejected)}"
    )

st.sidebar.success(f"Signed in as **{current_user.display_name}**")
st.sidebar.markdown(f"**Role(s):** {', '.join(current_user.roles)}")
if st.sidebar.button("Log out"):
    audit_log.append("logout", current_user.user_id, {})
    del st.session_state["auth_user_id"]
    st.rerun()

if "delegations" not in st.session_state:
    st.session_state.delegations = get_delegations()

accessible_ids = get_authorized_document_ids(
    current_user, corpus.documents, st.session_state.delegations, datetime.now(timezone.utc)
)
st.sidebar.markdown(f"**Accessible documents:** {len(accessible_ids)} of {len(corpus.documents)}")
st.sidebar.caption(f"Embedding: {index.embedding_name} · {index.count()} chunks indexed")

page = st.sidebar.radio(
    "Page",
    [
        "Secure AI Assistant",
        "Document Access",
        "Temporary Delegation",
        "Security Audit",
        "About and Limitations",
    ],
)

# ---------------------------------------------------------------------------
# Page 1 — Secure AI Assistant
# ---------------------------------------------------------------------------
if page == "Secure AI Assistant":
    st.header("Secure AI Assistant")
    st.caption(
        "Answers are grounded only in documents you are currently authorized to access."
    )

    question = st.text_input("Ask a question about company documents")

    reasoning_mode = st.toggle(
        "🧠 Reasoning mode",
        value=False,
        help=(
            "Uses Gemma 4's thinking_level=\"high\" so the model works through "
            "multi-step reasoning before answering, instead of the default fast "
            "thinking_level=\"minimal\". Slower, but better for questions that "
            "require comparing or synthesizing across multiple authorized "
            "sources rather than a single direct lookup."
        ),
    )
    ask_clicked = st.button("Ask", type="primary")

    if ask_clicked:
        if not question.strip():
            st.error("Please enter a question before submitting.")
        else:
            audit_log.append("query_submitted", current_user.user_id, {"outcome": "received"})

            findings = scan_prompt(question)
            decision = policy_decision(findings)

            if findings:
                audit_log.append(
                    "prompt_risk_detected",
                    current_user.user_id,
                    {
                        "decision": decision,
                        "rule_ids": [f.rule_id for f in findings],
                    },
                )
                for finding in findings:
                    level = st.error if finding.severity.value == "high" else st.warning
                    level(f"**[{finding.rule_id}] {finding.title}** — {finding.explanation}")

            if decision == "block":
                st.stop()

            result = retrieve_authorized_chunks(
                index,
                current_user,
                question,
                corpus.documents,
                st.session_state.delegations,
                top_k=SETTINGS.retrieval_top_k,
                now=datetime.now(timezone.utc),
            )

            if result.rejected_unauthorized_chunk_ids:
                audit_log.append(
                    "unauthorized_chunk_rejected",
                    current_user.user_id,
                    {"count": len(result.rejected_unauthorized_chunk_ids)},
                )

            # Indirect prompt injection guard: authorized chunks whose text
            # tries to give the assistant orders are withheld from the model.
            guard = guard_retrieved_chunks(result.chunks)
            if guard.quarantined:
                audit_log.append(
                    "document_injection_quarantined",
                    current_user.user_id,
                    {
                        "chunk_ids": [q.chunk.chunk_id for q in guard.quarantined],
                        "rule_ids": sorted({f.rule_id for q in guard.quarantined for f in q.findings}),
                    },
                )
                for quarantined in guard.quarantined:
                    rules = ", ".join(f.rule_id for f in quarantined.findings)
                    st.warning(
                        f"**Passage withheld from the AI** — a section of *{quarantined.chunk.title}* "
                        f"contains text that looks like an instruction aimed at the assistant "
                        f"([{rules}]). It was not sent to the model."
                    )
            safe_chunks = guard.clean_chunks

            thinking_level = "high" if reasoning_mode else "minimal"

            if not safe_chunks:
                audit_log.append("retrieval_completed", current_user.user_id, {"outcome": "abstained"})
            else:
                audit_log.append(
                    "retrieval_completed",
                    current_user.user_id,
                    {
                        "outcome": "answered",
                        "chunk_count": len(safe_chunks),
                        "thinking_level": thinking_level,
                    },
                )

            answer = answer_question(SETTINGS, question, safe_chunks, thinking_level=thinking_level)

            if answer.abstained:
                st.info(answer.answer_text)
            else:
                if answer.used_fallback:
                    st.warning(answer.answer_text)
                else:
                    st.markdown(answer.answer_text)
                    if answer.thinking_level == "high":
                        st.caption("🧠 Answered with Gemma 4 reasoning mode (thinking_level=\"high\")")

                if answer.citations:
                    with st.expander("Source evidence"):
                        for chunk in safe_chunks:
                            source_id = f"doc:{chunk.document_id}#{chunk.chunk_index}"
                            st.markdown(f"**[{source_id}]** — *{chunk.title}* ({chunk.classification})")
                            st.text(chunk.text)

# ---------------------------------------------------------------------------
# Page 2 — Document Access
# ---------------------------------------------------------------------------
elif page == "Document Access":
    st.header("Document Access")
    st.caption("Showing only documents visible to the selected demo user.")

    visible_docs = [d for d in corpus.documents if d.document_id in accessible_ids]
    for doc in visible_docs:
        with st.container(border=True):
            st.subheader(doc.title)
            st.markdown(
                f"**Classification:** {doc.classification} · **Owner:** {doc.owner_id}"
            )
            if "admin" in current_user.roles or "manager" in current_user.roles:
                st.caption(f"Allowed roles: {', '.join(doc.allowed_roles) or '—'}")

    if not visible_docs:
        st.info("No documents are currently accessible to this user.")

# ---------------------------------------------------------------------------
# Page 3 — Temporary Delegation
# ---------------------------------------------------------------------------
elif page == "Temporary Delegation":
    st.header("Temporary Delegation")
    st.caption("Grant another user time-limited access to one document you can access.")

    delegatable_docs = [d for d in corpus.documents if d.document_id in accessible_ids]

    with st.form("create_delegation"):
        grantee_id = st.selectbox(
            "Grantee",
            options=[u.user_id for u in users if u.user_id != current_user.user_id],
            format_func=lambda uid: user_by_id[uid].display_name,
        )
        doc_id = st.selectbox(
            "Document",
            options=[d.document_id for d in delegatable_docs],
            format_func=lambda did: next(d.title for d in delegatable_docs if d.document_id == did),
        ) if delegatable_docs else None
        expiry_date = st.date_input("Expires on", value=datetime.now().date() + timedelta(days=1))
        expiry_time = st.time_input("Expires at", value=(datetime.now() + timedelta(hours=1)).time())
        reason = st.text_input("Reason (optional)")
        submitted = st.form_submit_button("Create grant")

        if submitted:
            if not delegatable_docs:
                st.error("You have no document access to delegate.")
            else:
                document = next(d for d in delegatable_docs if d.document_id == doc_id)
                grantee = user_by_id[grantee_id]
                expires_at = datetime.combine(expiry_date, expiry_time, tzinfo=timezone.utc).isoformat()
                try:
                    grant = create_delegation(
                        current_user,
                        grantee,
                        document,
                        expires_at,
                        st.session_state.delegations,
                        reason=reason or None,
                    )
                    st.session_state.delegations.append(grant)
                    save_delegations(SETTINGS.delegations_path, st.session_state.delegations)
                    audit_log.append(
                        "delegation_created",
                        current_user.user_id,
                        {"grant_id": grant.grant_id, "grantee_id": grantee.user_id, "document_id": document.document_id},
                    )
                    st.success(f"Grant {grant.grant_id} created for {grantee.display_name}.")
                except DelegationError as exc:
                    audit_log.append(
                        "delegation_denied",
                        current_user.user_id,
                        {"document_id": doc_id, "reason": str(exc)},
                    )
                    st.error(str(exc))

    st.subheader("Existing grants")
    now = datetime.now(timezone.utc)
    for grant in st.session_state.delegations:
        status = delegation_status(grant, now)
        doc_title = next((d.title for d in corpus.documents if d.document_id == grant.document_id), grant.document_id)
        cols = st.columns([5, 1])
        with cols[0]:
            st.write(
                f"**{grant.grant_id}** — {grant.grantor_id} → {grant.grantee_id} on "
                f"*{doc_title}* — status: **{status}** (expires {grant.expires_at})"
            )
        with cols[1]:
            if status == "active" and grant.grantor_id == current_user.user_id:
                if st.button("Revoke", key=f"revoke_{grant.grant_id}"):
                    try:
                        st.session_state.delegations = revoke_delegation(
                            grant.grant_id, current_user, st.session_state.delegations
                        )
                        save_delegations(SETTINGS.delegations_path, st.session_state.delegations)
                        audit_log.append(
                            "delegation_revoked", current_user.user_id, {"grant_id": grant.grant_id}
                        )
                        st.rerun()
                    except DelegationError as exc:
                        st.error(str(exc))

# ---------------------------------------------------------------------------
# Page 4 — Security Audit
# ---------------------------------------------------------------------------
elif page == "Security Audit":
    st.header("Security Audit")

    if st.button("Verify chain"):
        result = audit_log.verify()
        audit_log.append("audit_verification_run", current_user.user_id, {"valid": result.valid})
        if result.valid:
            st.success(f"Chain verified ✅ ({result.checked_count} events checked)")
        else:
            st.error(
                f"Integrity verification failed ❌ — first invalid sequence: "
                f"{result.first_invalid_sequence}. Reason: {result.reason}"
            )

    st.subheader("Recent events")
    events = audit_log.read_all()
    for event in reversed(events[-50:]):
        st.text(
            f"#{event.sequence} [{event.timestamp}] {event.event_type} — actor={event.actor_id} "
            f"details={event.details}"
        )

# ---------------------------------------------------------------------------
# Page 5 — About and Limitations
# ---------------------------------------------------------------------------
elif page == "About and Limitations":
    st.header("About TrustRAG")
    st.markdown(
        """
TrustRAG is a hackathon prototype demonstrating secure, authorization-filtered
retrieval-augmented generation. It is **not** a production-ready enterprise
security system.

**Role-based access control (RBAC):** every document carries explicit
`allowed_roles` / `allowed_users` metadata. Access is decided centrally in
`auth/permissions.py` before any retrieval happens.

**Retrieval-augmented generation (RAG):** questions are answered only from
document chunks the current user is authorized to see. Every retrieved chunk
is re-validated against the authorization service a second time before it can
enter the model's context, even if it was returned by the vector search.

**Prompt-injection scanning is heuristic.** It flags common attack patterns
(instruction overrides, hidden-prompt extraction, safeguard bypass attempts,
restricted-document requests). The absence of a match does **not** mean a
prompt is safe — this is a mitigation layer, not a guarantee.

**Retrieved documents are scanned too.** A document a user is allowed to read
can still contain text aimed at the assistant (indirect prompt injection).
Each retrieved passage is scanned, and any passage that appears to give the
assistant orders is withheld from the model and recorded in the audit log.
Measured on Microsoft's BIPIA benchmark this heuristic catches only part of
the attacks (see `evaluation/results.md`), so the system prompt additionally
marks every passage as untrusted quoted data.

**The corpus is real content with a demo access policy.** The documents are
pages from the public, MIT-licensed GitLab Handbook. The classifications and
role restrictions were assigned per department for this demo and are not
GitLab's own access rules.

**Time-limited delegation** lets a user who can already access a document
grant another user scoped, expiring access to that one document. Expiry and
revocation are enforced at query time, not only in the UI.

**Hash-chained audit log:** every security-relevant event is appended with a
SHA-256 hash over its canonical payload plus the previous event's hash.
Verification recomputes the whole chain and detects any modification,
deletion, or reordering of the stored events.

**Honest limitation on the audit chain:** this hash chain detects tampering
with the *currently stored* log file. It is **not** immutable against an
attacker who can rewrite the entire log and recompute every hash from
scratch — that requires protected external storage, digital signatures, or
trusted checkpoints, which are out of scope for this MVP.

**When content is sent to the LLM provider:** when a Gemma API key is
configured, only the already-authorized, already-filtered chunk text and your
question are sent to Google's Generative Language API to generate an answer.
No other document content, and no document metadata beyond what's shown in
the UI, is sent. If no key is configured, or the call fails, the app shows the
raw authorized evidence instead of a generated answer, and never fabricates a
citation.
        """
    )
