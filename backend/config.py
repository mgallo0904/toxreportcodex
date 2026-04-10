"""Configuration module for the backend service.

This module defines a `Settings` class using `pydantic-settings` to read
environment variables into strongly typed configuration attributes. The
class can be instantiated once at process startup and re‑used wherever
configuration values are required. Values default to sensible defaults
where appropriate and may be overridden via a `.env` file or the
deployment environment.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Database connection string, e.g. postgresql+asyncpg://user:pass@host/db
    database_url: str = Field(..., alias="DATABASE_URL")

    # Redis connection string for ARQ background tasks
    redis_url: str = Field(..., alias="REDIS_URL")

    # Base URL for the inference API provider (Ollama or Together.ai)
    inference_base_url: str = Field("https://ollama.com", alias="INFERENCE_BASE_URL")

    # API key for the inference provider
    inference_api_key: str = Field(..., alias="INFERENCE_API_KEY")

    # Default model tag to use if none is configured in the database
    default_model_tag: str = Field("deepseek-r1", alias="DEFAULT_MODEL_TAG")

    # Path on disk where uploaded files and model adapters are stored
    storage_path: str = Field("/var/data", alias="STORAGE_PATH")

    # Modal.com API credentials for fine‑tuning jobs
    modal_token_id: str = Field(..., alias="MODAL_TOKEN_ID")
    modal_token_secret: str = Field(..., alias="MODAL_TOKEN_SECRET")

    # Environment (development/production) hint
    environment: str = Field("production", alias="ENVIRONMENT")

    # Allowed CORS origins for the FastAPI application, comma‑separated
    cors_origins: str = Field("", alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def get_settings() -> Settings:
    """Helper to instantiate and cache the settings object.

    Importing the settings directly at module scope will read environment
    variables on import. Providing a function makes it easier to mock
    configuration in tests and ensures a single instance is reused.

    Returns
    -------
    Settings
        A new or cached Settings instance.
    """
    return Settings()