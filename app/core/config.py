from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """Validated application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Sales AI 2.0"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    log_level: str = "INFO"

    groq_api_key: SecretStr | None = None
    groq_model_fast: str = "openai/gpt-oss-20b"
    groq_model_powerful: str = "openai/gpt-oss-120b"
    groq_timeout_seconds: float = Field(default=30, gt=0, le=120)
    groq_max_retries: int = Field(default=2, ge=0, le=5)
    groq_reasoning_effort_fast: Literal["low", "medium", "high"] = "low"
    groq_reasoning_effort_powerful: Literal["low", "medium", "high"] = "medium"
    groq_allow_powerful_fallback: bool = True
    intent_api_enabled: bool = True
    intent_validation_debug: bool = False
    chat_max_history_messages: int = Field(default=30, ge=4, le=100)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    session_cookie_secure: bool = False
    session_days: int = Field(default=14, ge=1, le=90)

    postgres_host: str = "127.0.0.1"
    postgres_port: int = Field(default=55432, ge=1, le=65535)
    postgres_user: str = "sales_ai"
    postgres_password: SecretStr
    postgres_db: str = "sales_ai"

    embedding_model: str = "intfloat/multilingual-e5-small"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("LOG_LEVEL must be a standard Python logging level")
        return normalized

    @field_validator("postgres_password")
    @classmethod
    def validate_database_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("POSTGRES_PASSWORD must not be empty")
        return value

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def checkpoint_database_uri(self) -> str:
        return self.database_url.render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
