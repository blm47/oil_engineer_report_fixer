from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+psycopg2://oil_user:oil_password@postgres:5432/oil_reports",
        alias="DATABASE_URL",
    )
    backend_cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:8080", "http://127.0.0.1:8080"],
        alias="BACKEND_CORS_ORIGINS",
    )
    upload_dir: str = Field(default="/app/tmp_uploads", alias="UPLOAD_DIR")
    session_ttl_hours: int = Field(default=24, alias="SESSION_TTL_HOURS")
    channel_criteria_path: str = Field(
        default="/app/channel_criteria.yaml", alias="CHANNEL_CRITERIA_PATH"
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
