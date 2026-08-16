"""FR-004, FR-005, FR-006, FR-007."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.fakes import FakeLLMProvider

from enterprise_rag_knowledge_assistant.config import get_settings
from enterprise_rag_knowledge_assistant.ingestion import ingest_file

pytestmark = pytest.mark.integration


def _ingest(db_session: Session, fake_provider: FakeLLMProvider, tmp_path, name: str, content: str):
    path = tmp_path / name
    path.write_text(content)
    ingest_file(path, db_session, fake_provider, get_settings())


def test_query_with_relevant_content_returns_grounded_answer_with_citations(
    api_client: TestClient, db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    _ingest(
        db_session,
        fake_provider,
        tmp_path,
        "backup.md",
        "Database backups run daily and are retained for thirty days. "
        "Backup restore access is limited to the platform team.",
    )

    response = api_client.post("/query", json={"question": "How often do database backups run?"})

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert len(body["citations"]) >= 1
    assert body["citations"][0]["document"] == "backup.md"
    # FR-005: the model was called with the retrieved context, not the bare question.
    assert fake_provider.chat_calls
    _, user_prompt = fake_provider.chat_calls[-1]
    assert "backup" in user_prompt.lower()


def test_query_with_no_relevant_content_reports_insufficient_evidence(
    api_client: TestClient, db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    _ingest(
        db_session,
        fake_provider,
        tmp_path,
        "unrelated.md",
        "This document is about quarterly gardening club meeting schedules.",
    )

    response = api_client.post(
        "/query", json={"question": "What is our Kubernetes upgrade cadence policy?"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is False
    assert body["citations"] == []
    # FR-007: must not fabricate -- the LLM must not even be called when evidence is insufficient.
    assert fake_provider.chat_calls == []


def test_query_with_empty_index_reports_insufficient_evidence(
    api_client: TestClient,
) -> None:
    response = api_client.post("/query", json={"question": "Anything at all?"})
    assert response.status_code == 200
    assert response.json()["grounded"] is False


def test_query_rejects_empty_question(api_client: TestClient) -> None:
    response = api_client.post("/query", json={"question": ""})
    assert response.status_code == 422


def test_grounded_answer_sends_hardened_system_prompt(
    api_client: TestClient, db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    """ADR-0008: the system prompt actually sent to the provider treats context as data,
    not instructions -- the real injection-resistance check (does a live model comply) is
    EVAL-011/EVAL-012 in scripts/evaluate.py, not reproducible with the fake provider."""
    _ingest(
        db_session,
        fake_provider,
        tmp_path,
        "backup.md",
        "Database backups run daily and are retained for thirty days.",
    )

    api_client.post("/query", json={"question": "How often do database backups run?"})

    assert fake_provider.chat_calls
    system_prompt, _ = fake_provider.chat_calls[-1]
    assert "data" in system_prompt.lower()
    assert "never" in system_prompt.lower()
