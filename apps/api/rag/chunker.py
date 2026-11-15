
def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[str]:
    """
    Split text into overlapping character-based chunks.

    This initial implementation uses character counts,
    not model token counts.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be >= 0 and less than chunk_size"
        )

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        chunk = text[start:end]
        chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks
