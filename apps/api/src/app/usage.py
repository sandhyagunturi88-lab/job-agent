"""Token usage logging — quality bar: usage per node per user in the `usage` table.

The only LLM call sites are llm_rerank and tailor_cv, so those are the only
nodes that ever record usage. Dev/tests use the in-memory logger; production
writes to Supabase (service role).
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class UsageRow:
    user_id: str
    run_date: str
    node: str
    model: str
    input_tokens: int
    output_tokens: int


class UsageLogger(Protocol):
    def record(self, row: UsageRow) -> None: ...


class MemoryUsageLogger:
    def __init__(self) -> None:
        self.rows: list[UsageRow] = []

    def record(self, row: UsageRow) -> None:
        self.rows.append(row)


_INSERT = """
insert into public.usage (user_id, run_date, node, model, input_tokens, output_tokens)
values (%s, %s, %s, %s, %s, %s)
"""


class PostgresUsageLogger:
    """Requires the api [postgres] extra and DATABASE_URL."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def record(self, row: UsageRow) -> None:
        import psycopg

        with psycopg.connect(self.database_url) as conn:
            conn.execute(
                _INSERT,
                (row.user_id, row.run_date, row.node, row.model,
                 row.input_tokens, row.output_tokens),
            )


# Module-level singleton so graph nodes (plain functions) can record without
# threading app state through LangGraph. main.py swaps in Postgres on boot.
usage_logger: UsageLogger = MemoryUsageLogger()


def configure_usage_logger(logger: UsageLogger) -> None:
    global usage_logger
    usage_logger = logger


def record_usage(row: UsageRow) -> None:
    usage_logger.record(row)
