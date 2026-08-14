"""arq worker: scheduled ingestion + embedding.

Run locally:  arq worker.main.WorkerSettings   (needs REDIS_URL; sources and
store fall back to mocks/memory without credentials)
Deployed on Fly.io (`infra/fly.worker.toml`), Upstash Redis EU as the broker."""

import logging
import os
from typing import ClassVar

import httpx
from arq import cron
from arq.connections import RedisSettings

from worker.config import get_settings
from worker.embedder import make_embedder
from worker.pipeline import run_ingestion
from worker.sources.base import get_sources
from worker.store import make_store

logging.basicConfig(level=logging.INFO)


async def startup(ctx: dict) -> None:
    settings = get_settings()
    ctx["client"] = httpx.AsyncClient(timeout=30)
    ctx["store"] = make_store(settings.database_url)
    ctx["embedder"] = make_embedder(
        settings.voyage_api_key, settings.voyage_model, ctx["client"]
    )


async def shutdown(ctx: dict) -> None:
    await ctx["client"].aclose()


async def ingest_all_sources(ctx: dict) -> dict:
    sources = get_sources(get_settings(), ctx["client"])
    return await run_ingestion(store=ctx["store"], embedder=ctx["embedder"], sources=sources)


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    on_startup = startup
    on_shutdown = shutdown
    functions: ClassVar = [ingest_all_sources]
    cron_jobs: ClassVar = [
        # Twice daily: early morning (fresh for the daily graph runs) + midday top-up
        cron(ingest_all_sources, hour={5, 12}, minute=15, unique=True),
    ]
