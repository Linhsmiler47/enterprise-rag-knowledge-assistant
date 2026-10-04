"""FR-001, FR-002, FR-003."""

import pytest
from sqlalchemy.orm import Session
from tests.fakes import FakeLLMProvider

from enterprise_rag_knowledge_assistant.config import get_settings
from enterprise_rag_knowledge_assistant.ingestion import (
    ingest_directory,
    ingest_file,
    ingest_uploaded_document,
)
from enterprise_rag_knowledge_assistant.models import (
    SOURCE_UPLOAD,
    STATUS_UPLOADED,
    Chunk,
    Document,
)

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


def test_oversized_file_is_skipped_not_ingested(
    db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    """ADR-0008 guardrail: files over max_ingest_file_size_bytes are rejected before embedding."""
    from enterprise_rag_knowledge_assistant.config import get_settings

    settings = get_settings().model_copy(update={"max_ingest_file_size_bytes": 10})
    path = tmp_path / "huge.md"
    path.write_text("This content is definitely longer than ten bytes.")

    result = ingest_file(path, db_session, fake_provider, settings)

    assert result.status == "skipped"
    assert db_session.query(Document).count() == 0


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


def test_cli_and_upload_paths_produce_the_same_chunks_for_the_same_text(
    db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    """Characterizes the invariant R2 (docs/refactor-plan.md) relies on: both ingest entry
    points call chunk_text/embed_batch the same way, so consolidating their chunk+embed
    preparation into one helper must not change the chunks or embeddings either path produces."""
    content = (
        "# Backup policy\n\n"
        "Database backups run nightly and are retained for thirty days.\n\n"
        "Backup restore access is limited to the platform team."
    )
    settings = get_settings()

    cli_path = tmp_path / "policy.md"
    cli_path.write_text(content)
    cli_result = ingest_file(cli_path, db_session, fake_provider, settings)
    assert cli_result.status == "ingested"
    cli_document = db_session.query(Document).filter_by(object_key="policy.md").one()

    uploaded_document = Document(
        object_key="uploads/policy-upload.md",
        original_filename="policy.md",
        content_hash="irrelevant-for-this-test",
        content_type="text/markdown",
        size_bytes=len(content.encode("utf-8")),
        status=STATUS_UPLOADED,
        source=SOURCE_UPLOAD,
    )
    db_session.add(uploaded_document)
    db_session.flush()
    upload_result = ingest_uploaded_document(
        uploaded_document, content, db_session, fake_provider, settings
    )
    assert upload_result.status == "ingested"

    cli_chunks = (
        db_session.query(Chunk)
        .filter_by(document_id=cli_document.id)
        .order_by(Chunk.chunk_index)
        .all()
    )
    upload_chunks = (
        db_session.query(Chunk)
        .filter_by(document_id=uploaded_document.id)
        .order_by(Chunk.chunk_index)
        .all()
    )

    assert [c.content for c in cli_chunks] == [c.content for c in upload_chunks]
    assert [c.embedding for c in cli_chunks] == [c.embedding for c in upload_chunks]
