"""Ingestion pipeline: document -> parse -> chunk -> embed -> store.

Supported formats: .md, .txt only (see docs/adr/0003-ingestion-format-scope.md).
Idempotent: re-ingesting an unchanged file (same content hash) is a no-op.

Two entry points share the same chunk/embed/store core (`_store_chunks`):
- `ingest_file`/`ingest_directory`: CLI/operator path, reads local files, one-shot (FR-001/002/003).
- `ingest_uploaded_document`: product/API path (Phase 2) -- ingests a Document row that already
  exists with status="uploaded" (created by the upload endpoint), given content already fetched
  from object storage by the caller. Tracks status transitions (uploaded -> ingesting ->
  ingested/failed) since this path is triggered separately from upload, unlike the CLI's one-shot
  flow.
"""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from enterprise_rag_knowledge_assistant.chunking import chunk_text
from enterprise_rag_knowledge_assistant.config import Settings, get_settings
from enterprise_rag_knowledge_assistant.models import (
    SOURCE_CLI,
    STATUS_FAILED,
    STATUS_INGESTED,
    STATUS_INGESTING,
    Chunk,
    Document,
)
from enterprise_rag_knowledge_assistant.providers import LLMProvider

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".md", ".txt"}
_CONTENT_TYPES_BY_EXTENSION = {".md": "text/markdown", ".txt": "text/plain"}


@dataclass
class IngestResult:
    filename: str
    status: str  # "ingested" | "unchanged" | "skipped" | "failed"
    chunk_count: int = 0


def content_hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def guess_content_type(suffix: str) -> str:
    return _CONTENT_TYPES_BY_EXTENSION.get(suffix.lower(), "text/plain")


def _prepare_chunks_and_embeddings(
    content: str, provider: LLMProvider, settings: Settings
) -> tuple[list[str], list[list[float]]]:
    """Shared chunk+embed preparation for both ingest entry points (see module docstring)."""
    chunks = chunk_text(
        content, chunk_size=settings.chunk_size_chars, overlap=settings.chunk_overlap_chars
    )
    embeddings = provider.embed_batch(chunks)
    return chunks, embeddings


def _store_chunks(
    document_id: int, chunks: list[str], embeddings: list[list[float]], session: Session
) -> None:
    for i, (chunk_content, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
        session.add(
            Chunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk_content,
                embedding=embedding,
            )
        )


def ingest_file(
    path: Path, session: Session, provider: LLMProvider, settings: Settings
) -> IngestResult:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        logger.info("skipping unsupported file type: %s", path.name)
        return IngestResult(filename=path.name, status="skipped")

    file_size = path.stat().st_size
    if file_size > settings.max_ingest_file_size_bytes:
        logger.warning(
            "skipping oversized file: %s (%d bytes > %d byte limit)",
            path.name,
            file_size,
            settings.max_ingest_file_size_bytes,
        )
        return IngestResult(filename=path.name, status="skipped")

    content = path.read_text(encoding="utf-8")
    content_hash = content_hash_bytes(content.encode("utf-8"))

    existing = session.query(Document).filter_by(object_key=path.name).one_or_none()
    if existing is not None and existing.content_hash == content_hash:
        logger.info("unchanged, skipping re-ingest: %s", path.name)
        return IngestResult(filename=path.name, status="unchanged")

    if existing is not None:
        session.delete(existing)
        session.flush()

    chunks, embeddings = _prepare_chunks_and_embeddings(content, provider, settings)
    if not chunks:
        logger.warning("no content extracted from %s", path.name)
        return IngestResult(filename=path.name, status="skipped")

    document = Document(
        object_key=path.name,
        original_filename=path.name,
        content_hash=content_hash,
        content_type=guess_content_type(path.suffix),
        size_bytes=file_size,
        status=STATUS_INGESTED,
        source=SOURCE_CLI,
    )
    session.add(document)
    session.flush()  # assign document.id

    _store_chunks(document.id, chunks, embeddings, session)

    session.commit()
    logger.info("ingested %s (%d chunks)", path.name, len(chunks))
    return IngestResult(filename=path.name, status="ingested", chunk_count=len(chunks))


def ingest_directory(
    directory: Path, session: Session, provider: LLMProvider | None = None
) -> list[IngestResult]:
    settings = get_settings()
    provider = provider or LLMProvider(settings)
    results = []
    for path in sorted(directory.iterdir()):
        if path.is_file():
            results.append(ingest_file(path, session, provider, settings))
    return results


def ingest_uploaded_document(
    document: Document, content: str, session: Session, provider: LLMProvider, settings: Settings
) -> IngestResult:
    """Ingest a Document row created by the upload API (status="uploaded"). `content` is the
    decoded text already fetched from object storage by the caller (api/routes/documents.py) --
    this function only owns chunk/embed/store and the status state machine, never fetches from
    storage itself."""
    document.status = STATUS_INGESTING
    document.ingestion_error = None
    session.commit()

    try:
        # Replace any prior chunks (re-ingest after a fix, e.g. following a failure).
        session.query(Chunk).filter_by(document_id=document.id).delete()

        chunks, embeddings = _prepare_chunks_and_embeddings(content, provider, settings)
        if not chunks:
            document.status = STATUS_FAILED
            document.ingestion_error = "no content extracted"
            session.commit()
            logger.warning("no content extracted from document_id=%s", document.id)
            return IngestResult(filename=document.original_filename, status="failed")

        _store_chunks(document.id, chunks, embeddings, session)

        document.status = STATUS_INGESTED
        session.commit()
        logger.info("ingested document_id=%s (%d chunks)", document.id, len(chunks))
        return IngestResult(
            filename=document.original_filename, status="ingested", chunk_count=len(chunks)
        )
    except Exception:
        session.rollback()
        document.status = STATUS_FAILED
        # Never surface raw exception details to the client/DB (ADR-0008) -- just enough to debug.
        document.ingestion_error = "ingestion failed -- see server logs for detail"
        session.commit()
        logger.exception("ingestion failed for document_id=%s", document.id)
        return IngestResult(filename=document.original_filename, status="failed")
