"""Ingestion pipeline: document -> parse -> chunk -> embed -> store.

Supported formats: .md, .txt only (see docs/adr/0003-ingestion-format-scope.md).
Idempotent: re-ingesting an unchanged file (same content hash) is a no-op.
"""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from enterprise_rag_knowledge_assistant.chunking import chunk_text
from enterprise_rag_knowledge_assistant.config import Settings, get_settings
from enterprise_rag_knowledge_assistant.models import Chunk, Document
from enterprise_rag_knowledge_assistant.providers import LLMProvider

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".md", ".txt"}


@dataclass
class IngestResult:
    filename: str
    status: str  # "ingested" | "unchanged" | "skipped"
    chunk_count: int = 0


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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
    content_hash = _content_hash(content)

    existing = session.query(Document).filter_by(filename=path.name).one_or_none()
    if existing is not None and existing.content_hash == content_hash:
        logger.info("unchanged, skipping re-ingest: %s", path.name)
        return IngestResult(filename=path.name, status="unchanged")

    if existing is not None:
        session.delete(existing)
        session.flush()

    chunks = chunk_text(
        content, chunk_size=settings.chunk_size_chars, overlap=settings.chunk_overlap_chars
    )
    if not chunks:
        logger.warning("no content extracted from %s", path.name)
        return IngestResult(filename=path.name, status="skipped")

    embeddings = provider.embed_batch(chunks)

    document = Document(filename=path.name, content_hash=content_hash)
    session.add(document)
    session.flush()  # assign document.id

    for i, (chunk_content, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
        session.add(
            Chunk(
                document_id=document.id,
                chunk_index=i,
                content=chunk_content,
                embedding=embedding,
            )
        )

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
