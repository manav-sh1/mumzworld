"""Application settings loaded from environment / .env file."""
from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — instantiated once at import time."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = Field(..., description="OpenRouter API key")
    model_name: str = Field(
        "openrouter/free",
        description="Model identifier on OpenRouter",
    )
    temperature: float = Field(0.4, ge=0.0, le=2.0)
    log_level: str = Field("INFO")

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper


settings = Settings()  # type: ignore[call-arg]
