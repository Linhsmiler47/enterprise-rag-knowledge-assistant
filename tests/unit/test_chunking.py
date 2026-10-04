import pytest

from enterprise_rag_knowledge_assistant.chunking import chunk_text


def test_empty_text_returns_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_stays_one_chunk() -> None:
    chunks = chunk_text("Just one short paragraph.", chunk_size=800, overlap=100)
    assert chunks == ["Just one short paragraph."]


def test_paragraphs_merge_until_size_limit() -> None:
    text = "Para one.\n\nPara two.\n\nPara three."
    chunks = chunk_text(text, chunk_size=1000, overlap=0)
    assert len(chunks) == 1
    assert "Para one." in chunks[0]
    assert "Para three." in chunks[0]


def test_paragraphs_split_when_exceeding_chunk_size() -> None:
    para_a = "A" * 50
    para_b = "B" * 50
    text = f"{para_a}\n\n{para_b}"
    chunks = chunk_text(text, chunk_size=60, overlap=10)
    assert len(chunks) >= 2
    assert any(para_a in c for c in chunks)
    assert any(para_b in c for c in chunks)


def test_oversized_single_paragraph_is_hard_split() -> None:
    huge_paragraph = "X" * 500
    chunks = chunk_text(huge_paragraph, chunk_size=100, overlap=10)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)
    # No content lost across the hard split.
    assert sum(len(c) for c in chunks) >= len(huge_paragraph)


def test_accumulated_paragraph_followed_by_oversized_paragraph_stays_within_chunk_size() -> None:
    """Bug: an accumulated (fitting) paragraph followed by one oversized paragraph used to be
    concatenated whole onto `current` instead of being hard-split, producing a chunk far larger
    than chunk_size. See docs/refactor-plan.md 'High risk' / Missing tests item 1."""
    para_a = "A" * 50
    para_b = "B" * 300
    text = f"{para_a}\n\n{para_b}"

    chunks = chunk_text(text, chunk_size=100, overlap=10)

    assert all(len(c) <= 100 for c in chunks), [len(c) for c in chunks]
    assert any(c == para_a for c in chunks)
    assert sum(c.count("B") for c in chunks) >= len(para_b)


def test_overlap_equal_to_chunk_size_raises() -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("short text", chunk_size=50, overlap=50)


def test_overlap_greater_than_chunk_size_raises() -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("short text", chunk_size=50, overlap=60)


def test_zero_overlap_hard_split_covers_all_content_without_overlap_duplication() -> None:
    huge_paragraph = "C" * 250
    chunks = chunk_text(huge_paragraph, chunk_size=100, overlap=0)
    assert all(len(c) <= 100 for c in chunks)
    assert "".join(chunks) == huge_paragraph


def test_paragraph_exactly_chunk_size_length_is_not_hard_split() -> None:
    para = "X" * 100
    chunks = chunk_text(para, chunk_size=100, overlap=10)
    assert chunks == [para]


def test_combined_paragraphs_exactly_at_chunk_size_boundary_merge() -> None:
    para_a = "A" * 40
    para_b = "B" * 58
    text = f"{para_a}\n\n{para_b}"
    assert len(text) == 100

    chunks = chunk_text(text, chunk_size=100, overlap=0)

    assert chunks == [text]
