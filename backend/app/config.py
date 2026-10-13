from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App configuration loaded from environment variables / .env file."""

    APP_NAME: str = "AskYourWallet"

    # SQLite keeps local development zero-setup. Hosted deployments provide a
    # PostgreSQL DATABASE_URL through their environment.
    DATABASE_URL: str = "sqlite+aiosqlite:///./askyourwallet.db"

    JWT_SECRET_KEY: str = "dev-secret-key-do-not-use-in-production-1234567890"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day -- avoids mid-session logouts

    # --- Groq (free tier) -----------------------------------------------------
    GROQ_API_KEY: str = ""
    # The project brief specified llama-3.3-70b-versatile, but Groq removed that
    # model from the free and developer tiers (shutdown 2026-08-16; it is now
    # enterprise/committed-spend only). GROQ_MODEL therefore defaults to Groq's
    # own documented replacement, which is free-tier and supports tool calling.
    # Override in .env to use any other Groq-hosted tool-capable model.
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    # Smaller/cheaper model for the single-label categorization fallback.
    GROQ_CATEGORIZATION_MODEL: str = "openai/gpt-oss-20b"
    # Hard cap on tool-call round trips in the chat loop, so a model that keeps
    # requesting tools can never spin forever.
    GROQ_MAX_TOOL_ROUNDS: int = 5

    FRONTEND_URL: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def use_async_postgres_driver(cls, value: str) -> str:
        """Adapt standard hosted-Postgres URLs for SQLAlchemy's async engine.

        Render and other providers expose a ``postgresql://`` connection string,
        while this app uses SQLAlchemy with asyncpg. Keeping this conversion here
        means the provider URL can be pasted directly into its environment settings.
        """
        url = str(value)
        if url.startswith("postgres://"):
            return "postgresql+asyncpg://" + url.removeprefix("postgres://")
        if url.startswith("postgresql://"):
            return "postgresql+asyncpg://" + url.removeprefix("postgresql://")
        return url

    @property
    def groq_enabled(self) -> bool:
        """True when a Groq API key is configured, so callers can degrade gracefully."""
        return bool(self.GROQ_API_KEY.strip())


settings = Settings()
