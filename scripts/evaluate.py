#!/usr/bin/env python3
"""Evaluation harness (see docs/evaluation.md).

Runs a small curated question set against the live system (real database, real embedding/LLM
provider -- not the test fakes) and prints/records measured results. Deliberately simple and
transparent rather than a heavyweight framework -- see docs/adr/0005-evaluation-approach.md.

Usage:
    make eval
    # or directly:
    uv run python scripts/evaluate.py
"""

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from enterprise_rag_knowledge_assistant.answering import answer_question  # noqa: E402
from enterprise_rag_knowledge_assistant.config import get_settings  # noqa: E402
from enterprise_rag_knowledge_assistant.db import get_session  # noqa: E402
from enterprise_rag_knowledge_assistant.providers import LLMProvider  # noqa: E402


@dataclass
class EvalCase:
    id: str
    question: str
    expect_answerable: bool
    expected_document: str | None = None  # substring match against a citation's document name
    expected_answer_keywords: list[str] = field(default_factory=list)


EVAL_SET: list[EvalCase] = [
    EvalCase(
        id="EVAL-001",
        question="How often are database backups taken?",
        expect_answerable=True,
        expected_document="database-backup-policy.md",
        expected_answer_keywords=["daily", "day"],
    ),
    EvalCase(
        id="EVAL-002",
        question="How long are database backups retained?",
        expect_answerable=True,
        expected_document="database-backup-policy.md",
        expected_answer_keywords=["30", "thirty"],
    ),
    EvalCase(
        id="EVAL-003",
        question="Who is allowed to perform a production database restore?",
        expect_answerable=True,
        expected_document="database-backup-policy.md",
        expected_answer_keywords=["platform"],
    ),
    EvalCase(
        id="EVAL-004",
        question="How should I roll back a bad production deployment?",
        expect_answerable=True,
        expected_document="deployment-runbook.md",
        expected_answer_keywords=["digest", "rollback", "redeploy"],
    ),
    EvalCase(
        id="EVAL-005",
        question="What determines whether a new instance receives traffic during a deploy?",
        expect_answerable=True,
        expected_document="deployment-runbook.md",
        expected_answer_keywords=["ready", "readiness", "probe"],
    ),
    EvalCase(
        id="EVAL-006",
        question="What should a new engineer do in their first week?",
        expect_answerable=True,
        expected_document="onboarding-guide.md",
        expected_answer_keywords=["contribution", "pull request", "pr"],
    ),
    EvalCase(
        id="EVAL-007",
        question="What is Severity 1 in the incident response policy?",
        expect_answerable=True,
        expected_document="incident-response-policy.md",
        expected_answer_keywords=["outage", "customer"],
    ),
    EvalCase(
        id="EVAL-008",
        question="Who is responsible for coordinating a Severity 1 incident?",
        expect_answerable=True,
        expected_document="incident-response-policy.md",
        expected_answer_keywords=["commander"],
    ),
    EvalCase(
        id="EVAL-009",
        question="What is the company's parental leave policy?",
        expect_answerable=False,
    ),
    EvalCase(
        id="EVAL-010",
        question="What programming language should new microservices be written in?",
        expect_answerable=False,
    ),
]


def run_eval() -> int:
    settings = get_settings()
    provider = LLMProvider(settings)

    total = len(EVAL_SET)
    retrieval_hits = 0
    groundedness_correct = 0
    keyword_hits = 0
    keyword_checks = 0
    latencies: list[float] = []
    failures: list[str] = []

    print(f"Running {total} evaluation cases against live provider "
          f"({settings.llm_provider}, chat={settings.llm_chat_model}, "
          f"embed={settings.llm_embedding_model})\n")

    with get_session() as session:
        for case in EVAL_SET:
            start = time.monotonic()
            result = answer_question(case.question, session, provider, settings)
            elapsed = time.monotonic() - start
            latencies.append(elapsed)

            grounded_correct = result.grounded == case.expect_answerable
            groundedness_correct += int(grounded_correct)

            doc_hit = None
            if case.expected_document:
                doc_hit = any(
                    case.expected_document in c.document_filename for c in result.citations
                )
                retrieval_hits += int(bool(doc_hit))

            kw_hit = None
            if case.expected_answer_keywords:
                keyword_checks += 1
                answer_lower = result.answer.lower()
                kw_hit = any(kw.lower() in answer_lower for kw in case.expected_answer_keywords)
                keyword_hits += int(kw_hit)

            status = "OK" if grounded_correct and (doc_hit is not False) and (kw_hit is not False) else "CHECK"
            if status == "CHECK":
                failures.append(case.id)

            print(
                f"[{status}] {case.id} grounded={result.grounded} "
                f"(expected={case.expect_answerable}) "
                f"doc_hit={doc_hit} keyword_hit={kw_hit} latency={elapsed:.2f}s"
            )
            print(f"        Q: {case.question}")
            print(f"        A: {result.answer[:150]}{'...' if len(result.answer) > 150 else ''}")

    denom_retrieval = sum(1 for c in EVAL_SET if c.expected_document)
    denom_keywords = keyword_checks

    print("\n--- Summary (real, measured -- see docs/evaluation.md for the recorded copy) ---")
    print(f"Groundedness accuracy: {groundedness_correct}/{total} "
          f"({100 * groundedness_correct / total:.0f}%)")
    if denom_retrieval:
        print(f"Retrieval hit-rate (correct source document): {retrieval_hits}/{denom_retrieval} "
              f"({100 * retrieval_hits / denom_retrieval:.0f}%)")
    if denom_keywords:
        print(f"Answer keyword presence: {keyword_hits}/{denom_keywords} "
              f"({100 * keyword_hits / denom_keywords:.0f}%)")
    print(f"Latency: min={min(latencies):.2f}s max={max(latencies):.2f}s "
          f"avg={sum(latencies) / len(latencies):.2f}s")
    if failures:
        print(f"Cases needing review: {', '.join(failures)}")

    return 0


if __name__ == "__main__":
    sys.exit(run_eval())
