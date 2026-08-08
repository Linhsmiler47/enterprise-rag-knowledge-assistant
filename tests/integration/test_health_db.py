"""FR-008 with a real database available."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.fakes import FakeLLMProvider

from enterprise_rag_knowledge_assistant.config import get_settings
from enterprise_rag_knowledge_assistant.ingestion import ingest_file

pytestmark = pytest.mark.integration


def test_ready_is_200_when_database_reachable(api_client: TestClient) -> None:
    response = api_client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"ready": True, "database": True}


def test_health_reports_zero_chunks_on_empty_index(api_client: TestClient) -> None:
    response = api_client.get("/health")
    body = response.json()
    assert body["database_reachable"] is True
    assert body["indexed_chunks"] == 0
    assert body["has_indexed_content"] is False


def test_health_reports_indexed_content_after_ingestion(
    api_client: TestClient, db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    path = tmp_path / "doc.md"
    path.write_text("Some example content for the health check test.")
    ingest_file(path, db_session, fake_provider, get_settings())

    response = api_client.get("/health")
    body = response.json()
    assert body["indexed_chunks"] >= 1
    assert body["has_indexed_content"] is True
