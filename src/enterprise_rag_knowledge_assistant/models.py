"""ORM models: Document (an ingested/uploaded file) and Chunk (a retrievable unit with its
embedding).

Document identity (see docs/adr/0011-phase2-stack.md): `object_key` is the unique identifier --
for CLI ingestion it's the source filename (unchanged behavior from v0.1); for uploads it's a
server-generated MinIO key. `original_filename` is display-only and NOT unique -- two uploads may
share a display name. `content_hash` remains the idempotency key (unchanged content -> no-op).
"""

from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBEDDING_DIM = 384  # must match config.embedding_dimensions / the embedding model in use

# Document.status values.
STATUS_UPLOADED = "uploaded"
STATUS_INGESTING = "ingesting"
STATUS_INGESTED = "ingested"
STATUS_FAILED = "failed"

# Document.source values.
SOURCE_CLI = "cli"
SOURCE_UPLOAD = "upload"


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("object_key", name="uq_documents_object_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="text/plain")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_UPLOADED)
    ingestion_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default=SOURCE_UPLOAD)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)

    document: Mapped["Document"] = relationship(back_populates="chunks")
