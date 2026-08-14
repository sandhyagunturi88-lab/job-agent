"""arq worker: scheduled ingestion + embedding.

Run locally:  arq worker.main.WorkerSettings   (needs REDIS_URL)
Deployed on Fly.io (`infra/fly.worker.toml`), Upstash Redis EU as the broker."""

import logging
import os
from typing import ClassVar

from arq import cron
from arq.connections import RedisSettings

from worker.dedupe import dedupe
from worker.embed import embed_and_index
from worker.sources import get_sources

logger = logging.getLogger("jobpilot.worker")


async def ingest_all_sources(ctx: dict) -> dict:
    jobs = []
    for source in get_sources():
        fetched = await source.fetch()
        logger.info("source %s returned %d jobs", source.name, len(fetched))
        jobs.extend(fetched)
    unique = dedupe(jobs)
    # Phase 2: upsert `unique` into Supabase jobs table here.
    chunks = await embed_and_index(unique)
    return {"fetched": len(jobs), "unique": len(unique), "chunks_indexed": chunks}


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    functions: ClassVar = [ingest_all_sources]
    cron_jobs: ClassVar = [
        # Twice daily: early morning (fresh for the daily graph runs) + midday top-up
        cron(ingest_all_sources, hour={5, 12}, minute=15, unique=True),
    ]
