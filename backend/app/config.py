import json
from functools import lru_cache
from typing import Any, List, Tuple, Type

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class _LenientEnvSettingsSource(EnvSettingsSource):
    """EnvSettingsSource that tolerates non-JSON values for complex fields.

    pydantic-settings tries to ``json.loads`` env vars whose target type is a
    list/dict. If a user supplies a comma-separated string (e.g.
    ``BACKEND_CORS_ORIGINS=http://a,http://b``) the default decoder raises
    ``JSONDecodeError`` and the app fails to start. Here we attempt the normal
    JSON decode first and fall back to returning the raw string so a
    ``field_validator`` can interpret it.
    """

    def decode_complex_value(self, field_name: str, field, value: Any) -> Any:  # type: ignore[override]
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value


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
        if value is None or value == "":
            return ["http://localhost:8080", "http://127.0.0.1:8080"]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "*":
                return ["*"]
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        lenient_env = _LenientEnvSettingsSource(settings_cls)
        return init_settings, lenient_env, dotenv_settings, file_secret_settings


@lru_cache
def get_settings() -> Settings:
    return Settings()
