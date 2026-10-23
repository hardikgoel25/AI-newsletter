"""Application settings loaded from environment / .env files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
ASSETS_DIR = APP_DIR / "assets"


class Settings(BaseSettings):
    """All runtime configuration. Secrets never have defaults."""

    model_config = SettingsConfigDict(
        # Later files win. Root .env is for local dev, backend/.env for deploys.
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "AI Newsletter Studio"
    version: str = "2.0.0"
    environment: str = Field(default="development", pattern="^(development|production|test)$")
    log_level: str = "INFO"

    # --- Providers ---
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    unsplash_access_key: str | None = None

    default_provider: str = "groq"
    default_model: str = "openai/gpt-oss-120b"
    # Comma-separated. Tried in order when the default model fails.
    fallback_models: str = "qwen/qwen3.8-27b,openai/gpt-oss-20b"
    llm_timeout_seconds: float = 90.0
    llm_max_retries: int = 3
    llm_max_output_tokens: int = 6000

    # --- Security ---
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Optional shared secret. When set, every /api route except /api/health requires
    # the `X-App-Key` header to match.
    app_access_key: str | None = None
    rate_limit_generate: str = "10/minute"
    rate_limit_default: str = "60/minute"
    max_json_body_bytes: int = 1_500_000  # 1.5 MB (data-URI logos are allowed)
    max_upload_bytes: int = 5 * 1024 * 1024
    max_content_chars: int = 40_000
    max_sources: int = 6
    max_image_dimension: int = 1600

    # --- Outbound fetch ---
    fetch_timeout_seconds: float = 10.0
    fetch_max_bytes: int = 2 * 1024 * 1024
    unsplash_budget_seconds: float = 8.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def fallback_model_list(self) -> list[str]:
        return [m.strip() for m in self.fallback_models.split(",") if m.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
