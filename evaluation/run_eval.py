"""Reproducible offline evaluation of TrustRAG's security and retrieval layers.

Measures, without any LLM or API key:

1. Access-control leak rate  — for every demo user and every test question,
   how many unauthorized chunks reach the would-be model context (must be 0),
   and how many the second ACL check catches when the pre-query filter is
   deliberately bypassed.
2. Retrieval quality          — how often the expected document is in the
   top-k for an authorized user, for each embedding model.
3. Injection-scanner quality  — detection rate on Microsoft's BIPIA text
   attacks inserted into real handbook passages, and the false-positive rate
   on the unmodified handbook.

What this does NOT measure: whether the LLM itself obeys an injection that
slips past the scanner. That needs live model calls and a per-attack judge.

Usage:
    python evaluation/run_eval.py
"""
from __future__ import annotations

import json
import os
import random
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from auth.permissions import get_authorized_document_ids, is_authorized  # noqa: E402
from config import load_settings  # noqa: E402
from ingestion.loader import load_document_text, load_documents, load_users  # noqa: E402
from rag.embeddings import LOCAL_HASHING_MODEL, MINILM_MODEL  # noqa: E402
from rag.indexer import ChromaIndex, build_chunks  # noqa: E402
from rag.retriever import retrieve_authorized_chunks  # noqa: E402
from security.prompt_scanner import scan_document_text  # noqa: E402

BIPIA_BASE = "https://raw.githubusercontent.com/microsoft/BIPIA/main/benchmark/"
BIPIA_DIR = os.path.join(ROOT, "data", "bipia")
RESULTS_PATH = os.path.join(ROOT, "evaluation", "results.md")
SEED = 20261012
HOST_CHUNKS_PER_ATTACK = 5

# (question, document_ids that count as a correct retrieval)
QUESTIONS: list[tuple[str, set[str]]] = [
    ("What should I do if I am being harassed by a colleague?", {"people_anti_harassment"}),
    ("Will my pay change if I move to a different country?", {"people_relocation"}),
    ("How does the 360 feedback process work?", {"people_360_feedback"}),
    ("How long is the probation period for new hires?", {"people_contracts_probation_periods"}),
    ("How much paid time off can I take?",
     {"people_time_off_and_absence", "people_time_off_and_absence_time_off_types",
      "people_time_off_and_absence_time_away_philosophy", "people_time_off_and_absence_leave_types"}),
    ("How is an error budget calculated for a service?", {"engineering_error_budgets"}),
    ("How can I nominate an engineer for recognition?", {"engineering_recognition"}),
    ("When is a new GitLab version released?", {"engineering_releases"}),
    ("Which travel costs can I claim back from the company?", {"finance_expenses", "finance_spending_company_money"}),
    ("Who is permitted to talk to investors and analysts?", {"finance_investor_relations"}),
    ("What are the rules for engaging contingent workers?", {"finance_procurement_contingent_worker_policy"}),
    ("How do I buy software that only I will use?", {"finance_procurement_individual_use_software", "finance_procurement"}),
    ("What makes a strong password?", {"security_password_guidelines"}),
    ("What do we do if we are hit by ransomware?", {"security_responding_to_ransomware"}),
    ("How do I request an exception to a security policy?", {"security_security_and_technology_policy_exception"}),
    ("How should secrets be stored in Vault?", {"security_external_secret_storage"}),
    ("Am I allowed to give a gift to a government official?", {"legal_anti_corruption_policy"}),
    ("How do I report wrongdoing anonymously?", {"legal_whistleblowing", "legal_anti_retaliation_policy", "legal_anti_fraud_policy"}),
    ("How many years must we keep business records?", {"legal_record_retention_policy"}),
    ("Which countries are we not allowed to export to?", {"legal_trade_compliance"}),
    ("When do my stock options vest?", {"compensation_stock_options"}),
    ("How is my salary determined?", {"compensation_compensation"}),
    ("What do I need to arrange before going on parental leave?",
     {"compensation_benefits_parental_leave_toolkit", "people_time_off_and_absence_leave_types"}),
]


def fetch_bipia(name: str) -> dict[str, list[str]]:
    os.makedirs(BIPIA_DIR, exist_ok=True)
    path = os.path.join(BIPIA_DIR, name)
    if not os.path.isfile(path):
        with urllib.request.urlopen(BIPIA_BASE + name, timeout=30) as response:
            data = response.read()
        with open(path, "wb") as f:
            f.write(data)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def insert_attack(text: str, attack: str, position: str) -> str:
    if position == "start":
        return f"{attack}\n\n{text}"
    if position == "end":
        return f"{text}\n\n{attack}"
    lines = text.split("\n")
    middle = len(lines) // 2
    return "\n".join(lines[:middle] + [attack] + lines[middle:])


def evaluate_access_control(index, users, documents, top_k: int, now) -> dict:
    doc_by_id = {d.document_id: d for d in documents}
    all_ids = sorted(doc_by_id)
    queries = 0
    chunks_returned = 0
    leaked = 0
    rejected_by_second_check = 0
    bypass_unauthorized_hits = 0
    bypass_leaked = 0

    for user in users:
        authorized = get_authorized_document_ids(user, documents, [], now)
        for question, _expected in QUESTIONS:
            queries += 1
            result = retrieve_authorized_chunks(index, user, question, documents, [], top_k, now)
            chunks_returned += len(result.chunks)
            leaked += sum(1 for c in result.chunks if c.document_id not in authorized)
            rejected_by_second_check += len(result.rejected_unauthorized_chunk_ids)

            # Simulated filter bug: search the WHOLE corpus, then apply only
            # the per-chunk second check, exactly as the retriever does.
            for hit in index.query(question, document_ids=all_ids, top_k=top_k):
                document = doc_by_id.get(hit["metadata"].get("document_id", ""))
                allowed = document is not None and is_authorized(user, document, [], now)
                if document is None or document.document_id not in authorized:
                    bypass_unauthorized_hits += 1
                    if allowed:
                        bypass_leaked += 1

    return {
        "queries": queries,
        "chunks_returned": chunks_returned,
        "leaked": leaked,
        "rejected_by_second_check": rejected_by_second_check,
        "bypass_unauthorized_hits": bypass_unauthorized_hits,
        "bypass_leaked": bypass_leaked,
    }


def evaluate_retrieval(index, admin, documents, top_k: int, now) -> dict:
    hits = 0
    misses = []
    for question, expected in QUESTIONS:
        result = retrieve_authorized_chunks(index, admin, question, documents, [], top_k, now)
        if any(c.document_id in expected for c in result.chunks):
            hits += 1
        else:
            misses.append(question)
    return {"hits": hits, "total": len(QUESTIONS), "misses": misses}


def evaluate_scanner(clean_chunks: list[str], attacks: dict[str, list[str]], rng: random.Random) -> dict:
    by_category = {}
    detected_total = 0
    total = 0
    for category, attack_texts in attacks.items():
        detected = 0
        count = 0
        for attack in attack_texts:
            for host in rng.sample(clean_chunks, HOST_CHUNKS_PER_ATTACK):
                for position in ("start", "middle", "end"):
                    count += 1
                    if scan_document_text(insert_attack(host, attack, position)):
                        detected += 1
        by_category[category] = (detected, count)
        detected_total += detected
        total += count
    return {"by_category": by_category, "detected": detected_total, "total": total}


def pct(numerator: int, denominator: int) -> str:
    return f"{100 * numerator / denominator:.1f}%" if denominator else "n/a"


def main() -> int:
    settings = load_settings()
    now = datetime.now(timezone.utc)
    users = load_users(settings.demo_users_path)
    corpus = load_documents(settings.acl_path, settings.documents_dir)
    documents = corpus.documents
    texts = {d.document_id: load_document_text(settings.documents_dir, d) for d in documents}
    admin = next(u for u in users if "admin" in u.roles)

    handbook_docs = [d for d in documents if not d.document_id.startswith("fixture_")]
    clean_chunks = [c.text for d in handbook_docs for c in build_chunks(d, texts[d.document_id])]

    lines = [
        "# TrustRAG evaluation results",
        "",
        f"Generated by `python evaluation/run_eval.py` on {now.date().isoformat()}.",
        "",
        f"- Corpus: {len(handbook_docs)} GitLab Handbook pages + 1 injection fixture "
        f"({len(clean_chunks)} handbook chunks)",
        f"- Users: {', '.join(u.user_id for u in users)}",
        f"- Questions: {len(QUESTIONS)}, top_k = {settings.retrieval_top_k}",
        "",
    ]

    lines += ["## 1. Access control", ""]
    lines += [
        "| Embedding | Queries | Chunks sent to context | Unauthorized chunks in context | "
        "Unauthorized hits when filter bypassed | Of those, passed the second check |",
        "|---|---|---|---|---|---|",
    ]
    retrieval_rows = []
    failed = False
    for model in (LOCAL_HASHING_MODEL, MINILM_MODEL):
        index = ChromaIndex(in_memory=True, embedding_model=model)
        if index.embedding_name != model:
            lines.append(f"| {model} | not run: {index.embedding_fallback_reason} | | | | |")
            continue
        index.reset()
        index.index_documents(documents, texts)
        ac = evaluate_access_control(index, users, documents, settings.retrieval_top_k, now)
        failed = failed or ac["leaked"] > 0 or ac["bypass_leaked"] > 0
        lines.append(
            f"| {model} | {ac['queries']} | {ac['chunks_returned']} | **{ac['leaked']}** | "
            f"{ac['bypass_unauthorized_hits']} | **{ac['bypass_leaked']}** |"
        )
        retrieval_rows.append((model, evaluate_retrieval(index, admin, documents, settings.retrieval_top_k, now)))
        print(f"[access control] {model}: {ac}")

    lines += [
        "",
        "\"Filter bypassed\" searches the whole corpus as if the pre-query filter had a bug; "
        "the per-chunk second check must then reject every unauthorized hit.",
        "",
        "## 2. Retrieval quality (admin user, expected document in top-k)",
        "",
        "| Embedding | Hit rate |",
        "|---|---|",
    ]
    for model, r in retrieval_rows:
        lines.append(f"| {model} | {r['hits']}/{r['total']} ({pct(r['hits'], r['total'])}) |")
        print(f"[retrieval] {model}: {r['hits']}/{r['total']}; misses: {r['misses']}")
    lines += ["", "Questions are paraphrased, so they share few exact words with the target page.", ""]

    false_positives = sum(1 for chunk in clean_chunks if scan_document_text(chunk))
    lines += [
        "## 3. Document-injection scanner (BIPIA text attacks)",
        "",
        f"Each attack string is inserted at the start, middle and end of "
        f"{HOST_CHUNKS_PER_ATTACK} randomly chosen handbook chunks (seed {SEED}).",
        "",
        f"- False positives on the unmodified handbook: **{false_positives}/{len(clean_chunks)}** "
        f"({pct(false_positives, len(clean_chunks))})",
    ]
    print(f"[scanner] false positives: {false_positives}/{len(clean_chunks)}")

    for split, name in (("train (rules were written against this split)", "text_attack_train.json"),
                        ("test (not used to write the rules)", "text_attack_test.json")):
        try:
            attacks = fetch_bipia(name)
        except Exception as exc:
            lines.append(f"- BIPIA {split}: not run ({exc})")
            continue
        result = evaluate_scanner(clean_chunks, attacks, random.Random(SEED))
        lines += [
            f"- BIPIA {split}: **{result['detected']}/{result['total']}** poisoned chunks detected "
            f"({pct(result['detected'], result['total'])})",
        ]
        print(f"[scanner] {name}: {result['detected']}/{result['total']}")
        if name == "text_attack_test.json":
            lines += ["", "Test split by attack category:", "", "| Category | Detected |", "|---|---|"]
            for category, (detected, count) in result["by_category"].items():
                lines.append(f"| {category} | {detected}/{count} ({pct(detected, count)}) |")

    lines += [
        "",
        "The scanner is a regular-expression heuristic. It catches attacks that address the "
        "assistant's output (\"...in your response\") and misses attacks phrased as an ordinary "
        "question or task. Whether the model obeys an attack that slips through was not measured.",
        "",
    ]

    with open(RESULTS_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print(f"\nWrote {os.path.relpath(RESULTS_PATH, ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
