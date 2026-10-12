"""TrustRAG REST API.

A thin FastAPI layer over the existing security/RAG modules — no business
logic lives here. Every endpoint calls straight into auth/, rag/,
delegation/, audit/, and security/, the same modules app.py (the Streamlit
UI) uses. This is what the React frontend talks to.

Session model: a bearer token issued on login, held in an in-memory dict
(token -> user_id). This is a demo session store, not a production auth
system — see README / JUDGES.md for the same caveat that applies to
auth/login.py's password hashing.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from auth.login import authenticate
from auth.permissions import User, get_authorized_document_ids
from audit.hash_chain import HashChainAuditLog
from config import load_settings
from delegation.service import (
    DelegationError,
    create_delegation,
    delegation_status,
    revoke_delegation,
)
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
from security.prompt_scanner import policy_decision, scan_prompt

SETTINGS = load_settings()

app = FastAPI(title="TrustRAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- App-level state, built once at process startup (mirrors app.py's
# st.cache_resource pattern, minus the Streamlit-specific caching). ---
audit_log = HashChainAuditLog(SETTINGS.audit_log_path)
users = load_users(SETTINGS.demo_users_path)
user_by_id: dict[str, User] = {u.user_id: u for u in users}

corpus = load_documents(SETTINGS.acl_path, SETTINGS.documents_dir)
index = ChromaIndex(persist_dir=SETTINGS.chroma_persist_dir)
index.reset()
_texts = {d.document_id: load_document_text(SETTINGS.documents_dir, d) for d in corpus.documents}
index.index_documents(corpus.documents, _texts)

delegations = load_delegations(SETTINGS.delegations_path)

SESSIONS: dict[str, str] = {}  # bearer token -> user_id


def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = SESSIONS.get(token)
    if not user_id or user_id not in user_by_id:
        raise HTTPException(401, "Invalid or expired session")
    return user_by_id[user_id]


def _user_payload(user: User) -> dict:
    return {"user_id": user.user_id, "display_name": user.display_name, "roles": list(user.roles)}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def login(req: LoginRequest):
    credentials = load_credentials(SETTINGS.demo_users_path)
    username = req.username.strip()
    user_id = authenticate(username, req.password, credentials)
    if user_id is None:
        audit_log.append("login_failed", username or "<empty>", {"outcome": "denied"})
        raise HTTPException(401, "Invalid username or password")

    audit_log.append("login", user_id, {"outcome": "success"})
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = user_id
    return {"token": token, "user": _user_payload(user_by_id[user_id])}


@app.post("/api/logout")
def logout(authorization: Optional[str] = Header(None), user: User = Depends(get_current_user)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    SESSIONS.pop(token, None)
    audit_log.append("logout", user.user_id, {})
    return {"ok": True}


@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    accessible = get_authorized_document_ids(user, corpus.documents, delegations, datetime.now(timezone.utc))
    return {
        **_user_payload(user),
        "accessible_count": len(accessible),
        "total_count": len(corpus.documents),
    }


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@app.get("/api/documents")
def list_documents(user: User = Depends(get_current_user)):
    accessible = get_authorized_document_ids(user, corpus.documents, delegations, datetime.now(timezone.utc))
    show_meta = "admin" in user.roles or "manager" in user.roles
    return [
        {
            "document_id": d.document_id,
            "title": d.title,
            "classification": d.classification,
            "owner_id": d.owner_id,
            "allowed_roles": list(d.allowed_roles) if show_meta else None,
        }
        for d in corpus.documents
        if d.document_id in accessible
    ]


@app.get("/api/delegatable-documents")
def delegatable_documents(user: User = Depends(get_current_user)):
    accessible = get_authorized_document_ids(user, corpus.documents, delegations, datetime.now(timezone.utc))
    return [
        {"document_id": d.document_id, "title": d.title}
        for d in corpus.documents
        if d.document_id in accessible
    ]


# ---------------------------------------------------------------------------
# Secure AI Assistant
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str
    thinking_level: str = "minimal"


@app.post("/api/ask")
def ask(req: AskRequest, user: User = Depends(get_current_user)):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Question must not be empty")

    thinking_level = "high" if req.thinking_level == "high" else "minimal"

    audit_log.append("query_submitted", user.user_id, {"outcome": "received"})

    findings = scan_prompt(question)
    decision = policy_decision(findings)
    findings_payload = [
        {
            "rule_id": f.rule_id,
            "title": f.title,
            "severity": f.severity.value,
            "evidence": f.evidence,
            "explanation": f.explanation,
        }
        for f in findings
    ]
    if findings:
        audit_log.append(
            "prompt_risk_detected",
            user.user_id,
            {"decision": decision, "rule_ids": [f.rule_id for f in findings]},
        )

    if decision == "block":
        return {"blocked": True, "findings": findings_payload, "answer": None, "evidence": []}

    result = retrieve_authorized_chunks(
        index, user, question, corpus.documents, delegations,
        top_k=SETTINGS.retrieval_top_k, now=datetime.now(timezone.utc),
    )

    if result.rejected_unauthorized_chunk_ids:
        audit_log.append(
            "unauthorized_chunk_rejected", user.user_id,
            {"count": len(result.rejected_unauthorized_chunk_ids)},
        )

    if not result.chunks:
        audit_log.append("retrieval_completed", user.user_id, {"outcome": "abstained"})
    else:
        audit_log.append(
            "retrieval_completed", user.user_id,
            {"outcome": "answered", "chunk_count": len(result.chunks), "thinking_level": thinking_level},
        )

    answer = answer_question(SETTINGS, question, result.chunks, thinking_level=thinking_level)

    return {
        "blocked": False,
        "findings": findings_payload,
        "answer": {
            "text": answer.answer_text,
            "citations": answer.citations,
            "abstained": answer.abstained,
            "used_fallback": answer.used_fallback,
            "thinking_level": answer.thinking_level,
        },
        "evidence": [
            {
                "source_id": f"doc:{c.document_id}#{c.chunk_index}",
                "title": c.title,
                "classification": c.classification,
                "text": c.text,
            }
            for c in result.chunks
        ],
    }


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------
class DelegationRequest(BaseModel):
    grantee_id: str
    document_id: str
    expires_at: str
    reason: str | None = None


@app.get("/api/users")
def list_users(user: User = Depends(get_current_user)):
    return [{"user_id": u.user_id, "display_name": u.display_name} for u in users if u.user_id != user.user_id]


@app.get("/api/delegations")
def list_delegations(user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    return [
        {
            "grant_id": d.grant_id,
            "grantor_id": d.grantor_id,
            "grantee_id": d.grantee_id,
            "document_id": d.document_id,
            "document_title": next((doc.title for doc in corpus.documents if doc.document_id == d.document_id), d.document_id),
            "expires_at": d.expires_at,
            "status": delegation_status(d, now),
            "can_revoke": d.grantor_id == user.user_id and delegation_status(d, now) == "active",
        }
        for d in delegations
    ]


@app.post("/api/delegations")
def create_delegation_endpoint(req: DelegationRequest, user: User = Depends(get_current_user)):
    global delegations
    grantee = user_by_id.get(req.grantee_id)
    document = next((d for d in corpus.documents if d.document_id == req.document_id), None)
    if grantee is None or document is None:
        raise HTTPException(400, "Unknown grantee or document")

    try:
        grant = create_delegation(user, grantee, document, req.expires_at, delegations, reason=req.reason)
    except DelegationError as exc:
        audit_log.append("delegation_denied", user.user_id, {"document_id": req.document_id, "reason": str(exc)})
        raise HTTPException(400, str(exc)) from exc

    delegations = delegations + [grant]
    save_delegations(SETTINGS.delegations_path, delegations)
    audit_log.append(
        "delegation_created", user.user_id,
        {"grant_id": grant.grant_id, "grantee_id": grantee.user_id, "document_id": document.document_id},
    )
    return {"grant_id": grant.grant_id}


@app.post("/api/delegations/{grant_id}/revoke")
def revoke_delegation_endpoint(grant_id: str, user: User = Depends(get_current_user)):
    global delegations
    try:
        delegations = revoke_delegation(grant_id, user, delegations)
    except DelegationError as exc:
        raise HTTPException(400, str(exc)) from exc
    save_delegations(SETTINGS.delegations_path, delegations)
    audit_log.append("delegation_revoked", user.user_id, {"grant_id": grant_id})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Security Audit
# ---------------------------------------------------------------------------
@app.get("/api/audit/events")
def audit_events(user: User = Depends(get_current_user)):
    events = audit_log.read_all()[-100:]
    return [
        {
            "sequence": e.sequence,
            "timestamp": e.timestamp,
            "event_type": e.event_type,
            "actor_id": e.actor_id,
            "details": e.details,
        }
        for e in reversed(events)
    ]


@app.post("/api/audit/verify")
def audit_verify(user: User = Depends(get_current_user)):
    result = audit_log.verify()
    audit_log.append("audit_verification_run", user.user_id, {"valid": result.valid})
    return {
        "valid": result.valid,
        "checked_count": result.checked_count,
        "first_invalid_sequence": result.first_invalid_sequence,
        "reason": result.reason,
    }


# ---------------------------------------------------------------------------
# Serve the built React app (frontend/dist), if present, as a single
# deployable process alongside the API. In local dev, run the Vite dev
# server separately instead (see frontend/README or BACKEND_LIFECYCLE.md) —
# this only activates once `npm run build` has produced frontend/dist.
# ---------------------------------------------------------------------------
_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if os.path.isdir(_FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        candidate = os.path.join(_FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        # Client-side routes (e.g. /assistant, /audit) fall back to index.html
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))
