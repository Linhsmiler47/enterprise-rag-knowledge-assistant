"""FR-004: POST /query -- grounded question answering with citations."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from enterprise_rag_knowledge_assistant.answering import answer_question
from enterprise_rag_knowledge_assistant.config import get_settings
from enterprise_rag_knowledge_assistant.db import get_db
from enterprise_rag_knowledge_assistant.providers import LLMProvider, get_llm_provider

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class CitationResponse(BaseModel):
    document: str
    chunk_id: int
    similarity: float


class QueryResponse(BaseModel):
    question: str
    answer: str
    grounded: bool
    citations: list[CitationResponse]


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    session: Annotated[Session, Depends(get_db)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> QueryResponse:
    settings = get_settings()
    result = answer_question(request.question, session, provider, settings)

    return QueryResponse(
        question=result.question,
        answer=result.answer,
        grounded=result.grounded,
        citations=[
            CitationResponse(
                document=c.document_filename, chunk_id=c.chunk_id, similarity=c.similarity
            )
            for c in result.citations
        ],
    )
