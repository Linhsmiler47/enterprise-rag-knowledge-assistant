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
