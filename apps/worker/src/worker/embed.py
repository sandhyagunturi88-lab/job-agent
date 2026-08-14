"""Embedding worker: chunk new JDs and index them into pgvector.

Phase 2 wires a real embedding model + Supabase writes; the chunker and the
interface are fixed now so retrieve()'s hybrid search has a stable contract."""

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


async def embed_and_index(jobs: list[Job]) -> int:
    """Chunk + embed + upsert into job_chunks. Stubbed until phase 2."""
    return sum(len(chunk_jd(job)) for job in jobs)
