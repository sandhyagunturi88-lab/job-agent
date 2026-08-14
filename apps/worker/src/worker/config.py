from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""  # empty -> in-memory job store (dev/test)
    redis_url: str = "redis://localhost:6379"

    # Embeddings: Anthropic has no embeddings API; Voyage AI is the
    # Anthropic-recommended provider. Empty key -> deterministic local embedder.
    voyage_api_key: str = ""
    voyage_model: str = "voyage-3"

    # Source credentials (empty -> that source serves mock data)
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    reed_api_key: str = ""

    # What to search the keyed aggregators for (comma-separated)
    ingest_queries: str = "software engineer,python developer"

    # ATS board watchlists (comma-separated slugs; empty -> mock data)
    ats_greenhouse_boards: str = ""
    ats_lever_companies: str = ""
    ats_workable_accounts: str = ""

    @property
    def queries(self) -> list[str]:
        return [q.strip() for q in self.ingest_queries.split(",") if q.strip()]


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
