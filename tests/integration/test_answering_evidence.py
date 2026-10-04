"""Characterization tests for the threshold/filter behavior in answer_question() and
has_sufficient_evidence(), pinned before R3 (docs/refactor-plan.md) consolidates the two-pass
threshold check into one helper. These tests must keep passing unchanged after that refactor."""

import pytest
from sqlalchemy.orm import Session
from tests.fakes import FakeLLMProvider

from enterprise_rag_knowledge_assistant.answering import answer_question
from enterprise_rag_knowledge_assistant.config import get_settings
from enterprise_rag_knowledge_assistant.ingestion import ingest_file
from enterprise_rag_knowledge_assistant.retrieval import has_sufficient_evidence, retrieve

pytestmark = pytest.mark.integration


def _ingest(db_session: Session, fake_provider: FakeLLMProvider, tmp_path, name: str, content: str):
    path = tmp_path / name
    path.write_text(content)
    ingest_file(path, db_session, fake_provider, get_settings())


def test_has_sufficient_evidence_is_inclusive_at_threshold() -> None:
    """Pins the `>=` (not `>`) comparison in has_sufficient_evidence()."""
    from enterprise_rag_knowledge_assistant.retrieval import RetrievedChunk

    settings = get_settings().model_copy(update={"retrieval_similarity_threshold": 0.5})
    chunk_at_threshold = RetrievedChunk(
        document_filename="d.md", chunk_id=1, chunk_index=0, content="x", similarity=0.5
    )
    assert has_sufficient_evidence([chunk_at_threshold], settings) is True


def test_has_sufficient_evidence_false_for_empty_or_below_threshold() -> None:
    from enterprise_rag_knowledge_assistant.retrieval import RetrievedChunk

    settings = get_settings().model_copy(update={"retrieval_similarity_threshold": 0.5})
    below = RetrievedChunk(
        document_filename="d.md", chunk_id=1, chunk_index=0, content="x", similarity=0.49
    )
    assert has_sufficient_evidence([], settings) is False
    assert has_sufficient_evidence([below], settings) is False


def test_answer_question_includes_chunk_exactly_at_threshold(
    db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    """The inclusive boundary must survive end-to-end: a chunk whose similarity equals the
    configured threshold is cited, not dropped."""
    _ingest(
        db_session,
        fake_provider,
        tmp_path,
        "backup.md",
        "Database backups run nightly and are retained for thirty days.",
    )
    question = "How often do database backups run?"

    base_settings = get_settings()
    retrieved = retrieve(question, db_session, fake_provider, base_settings)
    assert retrieved, "test setup must retrieve at least one chunk"
    exact_threshold = retrieved[0].similarity

    settings = base_settings.model_copy(
        update={"retrieval_similarity_threshold": exact_threshold}
    )
    answer = answer_question(question, db_session, fake_provider, settings)

    assert answer.grounded is True
    assert any(c.chunk_id == retrieved[0].chunk_id for c in answer.citations)


def test_answer_question_excludes_chunks_below_threshold_from_citations(
    db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    """Pins the second filter pass in answer_question(): only chunks clearing the threshold
    reach the prompt/citations, even when other chunks were fetched in the same top-k."""
    _ingest(
        db_session,
        fake_provider,
        tmp_path,
        "backup.md",
        "Database backups run nightly and are retained for thirty days.",
    )
    _ingest(
        db_session,
        fake_provider,
        tmp_path,
        "gardening.md",
        "The quarterly gardening club meets on Tuesdays to discuss tomatoes.",
    )
    question = "How often do database backups run?"

    base_settings = get_settings()
    retrieved = retrieve(question, db_session, fake_provider, base_settings)
    similarities = sorted((c.similarity for c in retrieved), reverse=True)
    assert len(similarities) >= 2, "test setup must retrieve chunks from both documents"
    # Threshold strictly between the two similarities: the relevant chunk qualifies, the
    # unrelated one does not.
    threshold = (similarities[0] + similarities[1]) / 2
    assert similarities[0] >= threshold > similarities[1]

    settings = base_settings.model_copy(update={"retrieval_similarity_threshold": threshold})
    answer = answer_question(question, db_session, fake_provider, settings)

    assert answer.grounded is True
    cited_filenames = {c.document_filename for c in answer.citations}
    assert cited_filenames == {"backup.md"}

    # The LLM prompt itself must not include the sub-threshold chunk's content either.
    assert fake_provider.chat_calls
    _, user_prompt = fake_provider.chat_calls[-1]
    assert "tomatoes" not in user_prompt.lower()


def test_answer_question_citations_preserve_retrieval_order(
    db_session: Session, fake_provider: FakeLLMProvider, tmp_path
) -> None:
    """Both qualifying chunks are cited in the same (similarity-descending) order they were
    retrieved in -- R3's single helper must not reorder them."""
    _ingest(
        db_session,
        fake_provider,
        tmp_path,
        "backup.md",
        "Database backups run nightly and are retained for thirty days.",
    )
    _ingest(
        db_session,
        fake_provider,
        tmp_path,
        "restore.md",
        "Database backup restore access is limited to the platform team.",
    )
    question = "Tell me about database backups."

    settings = get_settings()
    retrieved = retrieve(question, db_session, fake_provider, settings)
    assert len(retrieved) >= 2

    answer = answer_question(question, db_session, fake_provider, settings)

    retrieved_order = [
        c.chunk_id for c in retrieved if c.similarity >= settings.retrieval_similarity_threshold
    ]
    cited_order = [c.chunk_id for c in answer.citations]
    assert cited_order == retrieved_order
