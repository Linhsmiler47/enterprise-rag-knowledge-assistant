"""Vector retrieval baseline (see docs/adr/0004-vector-only-retrieval-baseline.md).

No hybrid search, no reranking, no query rewriting in v1 -- plain cosine-similarity top-k over
pgvector. The architecture doesn't preclude adding those later.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from enterprise_rag_knowledge_assistant.config import Settings
from enterprise_rag_knowledge_assistant.models import Chunk, Document
from enterprise_rag_knowledge_assistant.providers import LLMProvider


@dataclass
class RetrievedChunk:
    document_filename: str
    chunk_id: int
    chunk_index: int
    content: str
    similarity: float


def retrieve(
    question: str, session: Session, provider: LLMProvider, settings: Settings
) -> list[RetrievedChunk]:
    query_embedding = provider.embed(question)

    distance = Chunk.embedding.cosine_distance(query_embedding)
    rows = (
        session.query(Chunk, Document, distance.label("distance"))
        .join(Document, Chunk.document_id == Document.id)
        .order_by(distance)
        .limit(settings.retrieval_top_k)
        .all()
    )

    results = []
    for chunk, document, dist in rows:
        similarity = 1.0 - float(dist)
        results.append(
            RetrievedChunk(
                document_filename=document.original_filename,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                similarity=similarity,
            )
        )
    return results


def qualifying_chunks(
    chunks: list[RetrievedChunk], settings: Settings
) -> list[RetrievedChunk]:
    """Chunks that clear the similarity threshold, in retrieval order. An empty result means
    insufficient evidence -- the single source of truth for both that check and context/citation
    selection (see docs/refactor-plan.md R3)."""
    return [c for c in chunks if c.similarity >= settings.retrieval_similarity_threshold]
