"""
app/core/config.py
──────────────────
Fuente única de verdad para toda la configuración de la aplicación.
Lee variables del archivo .env automáticamente via pydantic-settings.

Uso:
    from app.core.config import settings
    print(settings.app_name)
"""
from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Aplicación ───────────────────────────────────────────────────
    app_name: str = Field(default="Farmadil System")
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=True)
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)

    # ── Base de Datos ────────────────────────────────────────────────
    database_url: str = Field(default="sqlite+aiosqlite:///./farmadil.db")

    @computed_field  # type: ignore[misc]
    @property
    def database_url_async(self) -> str:
        """URL async para asyncpg/aiosqlite (uso en runtime)."""
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif self.database_url.startswith("sqlite://"):
            return self.database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return self.database_url

    @computed_field  # type: ignore[misc]
    @property
    def database_url_sync(self) -> str:
        """URL síncrona para Alembic (uso en migraciones)."""
        if self.database_url.startswith("postgresql://") or self.database_url.startswith("postgres://"):
            return self.database_url.replace("+asyncpg", "").replace("postgresql+psycopg2://", "postgresql://")
        return self.database_url.replace("sqlite+aiosqlite", "sqlite")


    # ── Redis ────────────────────────────────────────────────────────
    direct_redis_url: str | None = Field(default=None, validation_alias="REDIS_URL")
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")

    @computed_field  # type: ignore[misc]
    @property
    def redis_url(self) -> str:
        if self.direct_redis_url:
            return self.direct_redis_url
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # ── JWT ──────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(default="insecure-dev-secret-change-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30)
    jwt_refresh_token_expire_days: int = Field(default=7)

    # ── CORS ─────────────────────────────────────────────────────────
    allowed_origins: str = Field(default="http://localhost:3000,http://localhost:5173")

    @computed_field  # type: ignore[misc]
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    # ── Logging ──────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Singleton cacheado de la configuración.
    Usar siempre esta función en lugar de instanciar Settings() directamente.
    """
    return Settings()


# Instancia global para importación directa
settings = get_settings()
