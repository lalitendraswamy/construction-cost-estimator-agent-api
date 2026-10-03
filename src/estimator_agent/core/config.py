"""Typed, validated settings loaded from environment / .env (12-factor config)."""

from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: AppEnv = AppEnv.LOCAL
    app_name: str = "estimator-agent"
    log_level: str = "INFO"
    log_json: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Security
    admin_api_key: SecretStr = SecretStr("change-me")
    rate_limit_chat: str = "20/minute"
    rate_limit_storage_uri: str = "memory://"

    # LLMs: "provider:model" strings understood by langchain.chat_models.init_chat_model
    llm_small_model: str = "google_genai:gemini-3.5-flash-lite"
    llm_strong_model: str = "google_genai:gemini-3.8-flash"
    # None = provider default. Gemini 3 is tuned for its default temperature (1.0);
    # lowering it can cause looping. Determinism comes from structured output instead.
    llm_small_temperature: float | None = None
    # Gemini 3 reasoning depth: minimal | low | medium | high (support varies by model).
    llm_small_thinking_level: str | None = None
    llm_strong_thinking_level: str | None = None
    llm_timeout_seconds: float = 60
    llm_max_retries: int = 3  # free tier has low RPM; retries back off on 429

    # Embeddings
    embeddings_model: str = "gemini-embedding-2"
    embeddings_dimensions: int = 768  # must match the Atlas vector index

    # MongoDB
    mongodb_uri: str = ""  # Atlas SRV string; required at runtime (see db/mongo.require_uri)
    mongodb_db: str = "estimator"
    vector_index_name: str = "kb_vector_index"

    # Checkpointer
    checkpointer: str = "memory"  # memory | mongodb

    # Business rules
    owner_approval_threshold_inr: float = 1_00_00_000  # ₹1 Cr
    default_city: str = "visakhapatnam"
    owner_name: str = "Ravikumar"
    owner_email: str = "owner@example.com"
    owner_whatsapp: str = "919999999999"

    # Notifications
    email_provider: str = "console"  # console | resend
    resend_api_key: SecretStr | None = None
    email_from: str = "estimator@example.com"

    # Observability
    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "construction-estimator"

    # Provider keys (read from .env; exported to os.environ for the SDKs, see below)
    google_api_key: SecretStr | None = None  # Gemini (free tier via Google AI Studio)

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnv.PRODUCTION


def export_provider_env(settings: Settings) -> None:
    """pydantic-settings reads .env but does NOT populate os.environ. LangChain/LangSmith
    SDKs read their keys from os.environ, so export them once at startup. Real env vars win."""
    pairs: dict[str, str | None] = {
        "GOOGLE_API_KEY": _secret(settings.google_api_key),
        "LANGSMITH_API_KEY": _secret(settings.langsmith_api_key),
        "LANGSMITH_TRACING": "true" if settings.langsmith_tracing else "false",
        "LANGSMITH_PROJECT": settings.langsmith_project,
    }
    for key, value in pairs.items():
        if value and key not in os.environ:
            os.environ[key] = value


def _secret(value: SecretStr | None) -> str | None:
    return value.get_secret_value() if value else None


@lru_cache
def get_settings() -> Settings:
    """Cached singleton; override in tests with `get_settings.cache_clear()` or DI."""
    return Settings()
