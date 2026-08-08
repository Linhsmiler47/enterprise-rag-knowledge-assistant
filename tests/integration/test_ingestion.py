"""FR-001, FR-002, FR-003."""

import pytest
from sqlalchemy.orm import Session
from tests.fakes import FakeLLMProvider

from enterprise_rag_knowledge_assistant.ingestion import ingest_directory, ingest_file
from enterprise_rag_knowledge_assistant.models import Chunk, Document

pytestmark = pytest.mark.integration


def test_ingest_directory_creates_documents_and_chunks(
    db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    (tmp_path / "a.md").write_text("# Title\n\nSome content about deployments.")
    (tmp_path / "b.txt").write_text("Some content about backups.")

    results = ingest_directory(tmp_path, db_session, fake_provider)

    assert {r.filename for r in results} == {"a.md", "b.txt"}
    assert all(r.status == "ingested" for r in results)
    assert db_session.query(Document).count() == 2
    assert db_session.query(Chunk).count() >= 2


def test_unsupported_extension_is_skipped_not_crashed(
    db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    (tmp_path / "notes.pdf").write_bytes(b"%PDF-1.4 fake binary content")

    results = ingest_directory(tmp_path, db_session, fake_provider)

    assert len(results) == 1
    assert results[0].status == "skipped"
    assert db_session.query(Document).count() == 0


def test_reingesting_unchanged_document_is_idempotent(
    db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    from enterprise_rag_knowledge_assistant.config import get_settings

    path = tmp_path / "policy.md"
    path.write_text("Our backup policy runs daily.")
    settings = get_settings()

    first = ingest_file(path, db_session, fake_provider, settings)
    second = ingest_file(path, db_session, fake_provider, settings)

    assert first.status == "ingested"
    assert second.status == "unchanged"
    assert db_session.query(Document).count() == 1
    assert db_session.query(Chunk).count() == first.chunk_count


def test_changed_document_is_reingested(
    db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    from enterprise_rag_knowledge_assistant.config import get_settings

    path = tmp_path / "policy.md"
    settings = get_settings()

    path.write_text("Version one of the content.")
    ingest_file(path, db_session, fake_provider, settings)

    path.write_text("Version two, completely different and longer content about something else.")
    second = ingest_file(path, db_session, fake_provider, settings)

    assert second.status == "ingested"
    assert db_session.query(Document).count() == 1  # replaced, not duplicated
