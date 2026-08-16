"""Phase 2 product API: document upload, listing, manual ingestion trigger, deletion.

Adds the product workflow around the existing v0.1 ingestion core -- chunk_text/embed_batch/
Chunk storage are unchanged, only reached from a new entry point (see ingestion.py's
ingest_uploaded_document). /query is untouched. See docs/adr/0011-phase2-stack.md.

Upload size protection is best-effort (checked after the full body is read, not streamed) --
acceptable for a local-first, non-internet-facing personal tool; see
docs/adr/0008-guardrail-baseline.md.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from enterprise_rag_knowledge_assistant.config import get_settings
from enterprise_rag_knowledge_assistant.db import get_db
from enterprise_rag_knowledge_assistant.ingestion import (
    SUPPORTED_EXTENSIONS,
    content_hash_bytes,
    guess_content_type,
    ingest_uploaded_document,
)
from enterprise_rag_knowledge_assistant.models import (
    SOURCE_UPLOAD,
    STATUS_FAILED,
    STATUS_INGESTED,
    STATUS_UPLOADED,
    Document,
)
from enterprise_rag_knowledge_assistant.providers import LLMProvider, get_llm_provider
from enterprise_rag_knowledge_assistant.storage import ObjectStorage, get_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    original_filename: str
    content_type: str
    size_bytes: int
    status: str
    ingestion_error: str | None
    source: str
    created_at: datetime
    chunk_count: int


def _to_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        status=document.status,
        ingestion_error=document.ingestion_error,
        source=document.source,
        created_at=document.created_at,
        chunk_count=len(document.chunks),
    )


def _log_event(event: str, **fields: object) -> None:
    # Never include filename/content here -- document_id + counters/flags only (ADR-0008).
    logger.info(json.dumps({"event": event, **fields}))


def _sanitize_display_filename(raw_name: str) -> str:
    base = os.path.basename(raw_name or "upload")
    cleaned = "".join(ch for ch in base if ch.isprintable()).strip()
    return (cleaned or "upload")[:512]


def _extension_of(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile,
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[ObjectStorage, Depends(get_storage)],
) -> DocumentResponse:
    settings = get_settings()
    display_name = _sanitize_display_filename(file.filename or "upload")
    extension = _extension_of(display_name)

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=422, detail=f"unsupported file extension: {extension or '(none)'}"
        )

    data = await file.read()
    size_bytes = len(data)

    if size_bytes == 0:
        raise HTTPException(status_code=422, detail="uploaded file is empty")

    if size_bytes > settings.max_ingest_file_size_bytes:
        _log_event(
            "document_upload", outcome="rejected_too_large", size_bytes=size_bytes
        )
        raise HTTPException(
            status_code=413,
            detail=(
                f"file too large: {size_bytes} bytes > "
                f"{settings.max_ingest_file_size_bytes} byte limit"
            ),
        )

    content_hash = content_hash_bytes(data)
    existing = session.query(Document).filter_by(content_hash=content_hash).first()
    if existing is not None:
        _log_event("document_upload", outcome="duplicate_content", document_id=existing.id)
        return _to_response(existing)

    content_type = file.content_type or guess_content_type(extension)
    object_key = f"uploads/{uuid.uuid4().hex}{extension}"

    storage.put_object(object_key, data, content_type)

    document = Document(
        object_key=object_key,
        original_filename=display_name,
        content_hash=content_hash,
        content_type=content_type,
        size_bytes=size_bytes,
        status=STATUS_UPLOADED,
        source=SOURCE_UPLOAD,
    )
    session.add(document)
    session.commit()

    _log_event(
        "document_upload",
        outcome="accepted",
        document_id=document.id,
        size_bytes=size_bytes,
        content_type=content_type,
    )
    return _to_response(document)


@router.get("", response_model=list[DocumentResponse])
def list_documents(session: Annotated[Session, Depends(get_db)]) -> list[DocumentResponse]:
    documents = session.query(Document).order_by(Document.created_at.desc()).all()
    return [_to_response(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int, session: Annotated[Session, Depends(get_db)]
) -> DocumentResponse:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    return _to_response(document)


@router.post("/{document_id}/ingest", response_model=DocumentResponse)
def trigger_ingestion(
    document_id: int,
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[ObjectStorage, Depends(get_storage)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> DocumentResponse:
    settings = get_settings()
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")

    if document.status == STATUS_INGESTED:
        # Idempotent no-op -- matches the CLI path's "unchanged" philosophy (FR-002).
        return _to_response(document)

    try:
        raw = storage.get_object(document.object_key)
    except Exception:
        document.status = STATUS_FAILED
        document.ingestion_error = "could not read uploaded file from storage"
        session.commit()
        logger.exception("failed to fetch object for document_id=%s", document_id)
        _log_event("document_ingest", outcome="failed", document_id=document_id)
        return _to_response(document)

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        document.status = STATUS_FAILED
        document.ingestion_error = "file is not valid UTF-8 text"
        session.commit()
        _log_event("document_ingest", outcome="failed", document_id=document_id)
        return _to_response(document)

    result = ingest_uploaded_document(document, content, session, provider, settings)
    _log_event(
        "document_ingest",
        outcome=result.status,
        document_id=document_id,
        chunk_count=result.chunk_count,
    )
    return _to_response(document)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[ObjectStorage, Depends(get_storage)],
) -> None:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")

    storage.delete_object(document.object_key)
    session.delete(document)
    session.commit()
    _log_event("document_deleted", document_id=document_id)
