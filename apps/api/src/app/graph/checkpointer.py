"""Checkpointer factory.

Production: langgraph-checkpoint-postgres against Supabase (AWS eu-west-2) so a
run survives app closes, deploys and restarts — a user can pick jobs on the
train and approve the CV that evening, resuming mid-graph.

Dev/test (no DATABASE_URL): in-memory checkpointer; runs do not survive restarts.
"""

from contextlib import asynccontextmanager

from app.core.config import Settings


@asynccontextmanager
async def open_checkpointer(settings: Settings):
    if settings.database_url:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(settings.database_url) as saver:
            # Idempotent; the SQL in supabase/migrations/0002 mirrors this schema,
            # but setup() is the authoritative source.
            await saver.setup()
            yield saver
    else:
        from langgraph.checkpoint.memory import MemorySaver

        yield MemorySaver()
