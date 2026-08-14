"""JD chunking for the embedding index (chunks feed retrieve()'s hybrid search)."""

from jobpilot_schemas import Job

CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200


def chunk_jd(job: Job) -> list[str]:
    text = job.jd_text.strip()
    if len(text) <= CHUNK_CHARS:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + CHUNK_CHARS])
        start += CHUNK_CHARS - CHUNK_OVERLAP
    return chunks
