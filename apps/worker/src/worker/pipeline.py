"""Ingestion pipeline: fetch all sources → fuzzy dedupe → upsert to the job
store → chunk + embed anything not yet indexed.

Idempotent end to end: upserts are keyed on Job.id and chunk indexing only
touches jobs with no chunks yet, so re-running a batch never duplicates."""

import logging

from worker.dedupe import dedupe
from worker.embed import chunk_jd
from worker.embedder import Embedder
from worker.sources.base import IngestionSource
from worker.store import JobStore

logger = logging.getLogger("jobpilot.worker")


async def run_ingestion(
    store: JobStore, embedder: Embedder, sources: list[IngestionSource]
) -> dict:
    fetched = []
    for source in sources:
        try:
            jobs = await source.fetch()
        except Exception:
            # One broken board must not sink the whole batch
            logger.exception("source %s failed; continuing", source.name)
            continue
        logger.info("source %s returned %d jobs", source.name, len(jobs))
        fetched.extend(jobs)

    unique = dedupe(fetched)
    upserted = await store.upsert_jobs(unique)

    to_index = await store.jobs_missing_chunks()
    chunks_indexed = 0
    for job in to_index:
        # Prefix each chunk with title/company so retrieval matches on them too
        contents = [f"{job.title} at {job.company}\n{chunk}" for chunk in chunk_jd(job)]
        embeddings = await embedder.embed(contents, input_type="document")
        await store.upsert_chunks(
            job.id, list(zip(range(len(contents)), contents, embeddings, strict=True))
        )
        chunks_indexed += len(contents)

    stats = {
        "fetched": len(fetched),
        "unique": len(unique),
        "upserted": upserted,
        "jobs_indexed": len(to_index),
        "chunks_indexed": chunks_indexed,
    }
    logger.info("ingestion complete: %s", stats)
    return stats
