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
    # Dev alternative: persist checkpoints to a local SQLite file so runs
    # survive restarts without Postgres. Ignored when database_url is set.
    checkpoint_sqlite_path: str = ""

    anthropic_api_key: str = ""
    # claude-opus-5 is the default; set ANTHROPIC_MODEL=claude-sonnet-5 to trade
    # some capability for lower cost per rerank/tailor call.
    anthropic_model: str = "claude-opus-5"

    voyage_api_key: str = ""
    voyage_model: str = "voyage-3"

    redis_url: str = ""

    cors_origins: str = "http://localhost:5173"

    # Billing (phase 6). Empty secret key -> mock provider: checkout/portal
    # resolve to in-app dev endpoints instead of Stripe.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    pro_price_display: str = "£9/month"
    # Where Stripe redirects after checkout/portal (the PWA origin)
    app_base_url: str = "http://localhost:5173"

    @property
    def is_dev(self) -> bool:
        return self.app_env != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
