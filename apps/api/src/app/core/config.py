from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"

    # Supabase (AWS eu-west-2, London)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    # Also used by the LangGraph checkpointer; empty -> in-memory checkpointer (dev only)
    database_url: str = ""

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    redis_url: str = ""

    cors_origins: str = "http://localhost:5173"

    @property
    def is_dev(self) -> bool:
        return self.app_env != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
