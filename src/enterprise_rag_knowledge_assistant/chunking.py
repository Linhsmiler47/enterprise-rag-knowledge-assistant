"""Simple paragraph-aware chunker.

Splits on paragraph boundaries first (respects document structure), then merges/splits to hit
the target chunk size with overlap. Deliberately simple — see
docs/adr/0003-ingestion-format-scope.md for why a fuller splitter is deferred.
"""


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks, respecting paragraph boundaries where possible."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = current[-overlap:] + "\n\n" + para if overlap else para
        else:
            # A single paragraph longer than chunk_size: hard-split it.
            for i in range(0, len(para), chunk_size - overlap):
                chunks.append(para[i : i + chunk_size])
            current = ""

    if current:
        chunks.append(current)

    return chunks
