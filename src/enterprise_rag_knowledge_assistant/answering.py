"""Grounded answer generation: retrieved chunks -> prompt -> LLM -> answer + citations.

FR-005: the answer must be produced only from retrieved chunk content.
FR-007: insufficient evidence must be reported explicitly, not papered over.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from enterprise_rag_knowledge_assistant.config import Settings
from enterprise_rag_knowledge_assistant.providers import LLMProvider
from enterprise_rag_knowledge_assistant.retrieval import (
    RetrievedChunk,
    has_sufficient_evidence,
    retrieve,
)

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I don't have enough indexed information to answer this confidently."
)

SYSTEM_PROMPT = (
    "You are an internal knowledge assistant. Answer the user's question using ONLY the "
    "provided context excerpts. Do not use outside knowledge. If the context does not contain "
    "the answer, say so explicitly instead of guessing. Be concise."
)


@dataclass
class Citation:
    document_filename: str
    chunk_id: int
    similarity: float


@dataclass
class Answer:
    question: str
    answer: str
    citations: list[Citation]
    grounded: bool


def _build_user_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    context = "\n\n".join(
        f"[Source: {c.document_filename}#{c.chunk_id}]\n{c.content}" for c in chunks
    )
    return f"Context:\n{context}\n\nQuestion: {question}"


def answer_question(
    question: str, session: Session, provider: LLMProvider, settings: Settings
) -> Answer:
    chunks = retrieve(question, session, provider, settings)

    if not chunks or not has_sufficient_evidence(chunks, settings):
        return Answer(
            question=question,
            answer=INSUFFICIENT_EVIDENCE_MESSAGE,
            citations=[],
            grounded=False,
        )

    # Only cite chunks that clear the threshold, even if a few extra were fetched for context.
    relevant = [c for c in chunks if c.similarity >= settings.retrieval_similarity_threshold]

    user_prompt = _build_user_prompt(question, relevant)
    answer_text = provider.chat(SYSTEM_PROMPT, user_prompt)

    citations = [
        Citation(
            document_filename=c.document_filename, chunk_id=c.chunk_id, similarity=c.similarity
        )
        for c in relevant
    ]

    return Answer(question=question, answer=answer_text, citations=citations, grounded=True)
