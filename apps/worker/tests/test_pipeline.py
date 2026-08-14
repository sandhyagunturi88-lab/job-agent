"""End-to-end pipeline against the in-memory store + deterministic embedder."""

import asyncio

from jobpilot_schemas.embeddings import EMBEDDING_DIM, DeterministicEmbedder
from worker.config import WorkerSettings
from worker.pipeline import run_ingestion
from worker.sources.base import get_sources
from worker.store import MemoryJobStore


def _settings() -> WorkerSettings:
    # No credentials/watchlists: every source serves deterministic mocks
    return WorkerSettings(_env_file=None)


def test_pipeline_ingests_dedupes_and_indexes():
    store = MemoryJobStore()
    stats = asyncio.run(
        run_ingestion(store, DeterministicEmbedder(), get_sources(_settings()))
    )

    assert stats["fetched"] == 12  # 6 sources x 2 mock jobs
    # The same mock vacancies appear across boards with near-identical
    # title/company/location — fuzzy dedupe collapses those cross-board dupes.
    assert stats["unique"] < stats["fetched"]
    assert stats["unique"] == len(store.jobs)
    assert stats["jobs_indexed"] == len(store.jobs)
    assert set(store.chunks) == set(store.jobs)

    (_, content, embedding) = next(iter(store.chunks.values()))[0]
    assert "\n" in content  # title/company prefix line
    assert len(embedding) == EMBEDDING_DIM


def test_pipeline_rerun_is_idempotent():
    store = MemoryJobStore()
    embedder = DeterministicEmbedder()
    sources = get_sources(_settings())

    first = asyncio.run(run_ingestion(store, embedder, sources))
    jobs_after_first = dict(store.jobs)

    second = asyncio.run(run_ingestion(store, embedder, sources))
    assert store.jobs == jobs_after_first  # no duplicates
    assert second["jobs_indexed"] == 0  # nothing re-embedded
    assert first["jobs_indexed"] > 0


def test_failing_source_does_not_sink_the_batch():
    class BrokenSource:
        name = "broken"

        async def fetch(self):
            raise RuntimeError("board down")

    store = MemoryJobStore()
    sources = [BrokenSource(), *get_sources(_settings())]
    stats = asyncio.run(run_ingestion(store, DeterministicEmbedder(), sources))
    assert stats["fetched"] == 12  # the other six sources still landed
