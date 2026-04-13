import secrets
import warnings

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = ""
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # Options: json, console
    LOG_TIMESTAMP_FORMAT: str = "iso"  # Options: iso, epoch
    API_V1_STR: str = "/api/v1"  # Kept for backward compatibility
    API_LATEST_STR: str = "/api/latest"
    PROJECT_NAME: str = "Enterprise FastAPI Project"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    ORDER_CANCEL_TIMEOUT: int = 1800

    # Redis Cache Configuration
    REDIS_CACHE_URL: str = "redis://localhost:6379/1"
    REDIS_PASSWORD: str | None = None
    REDIS_POOL_MAX_CONNECTIONS: int = 100
    REDIS_SOCKET_TIMEOUT: float = 5.0
    REDIS_SOCKET_CONNECT_TIMEOUT: float = 5.0

    # Redis Sentinel Configuration
    REDIS_USE_SENTINEL: bool = False
    REDIS_SENTINEL_HOSTS: list[str] = ["localhost:26379"]
    REDIS_SENTINEL_MASTER_NAME: str = "mymaster"

    # Cache Configuration
    CACHE_DEFAULT_TTL: int = 300  # 5 minutes
    CACHE_SERIALIZER: str = "json"  # "json" or "pickle"

    @field_validator("REDIS_SENTINEL_HOSTS", mode="before")
    @classmethod
    def parse_sentinel_hosts(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [h.strip() for h in v.split(",")]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v:
            if cls.model_config.get("APP_ENV") == "production":
                raise ValueError("SECRET_KEY must be set in production!")
            v = secrets.token_urlsafe(32)
            warnings.warn(
                "SECRET_KEY not set, using auto-generated key. Set SECRET_KEY environment variable for production!",
                UserWarning,
                stacklevel=2,
            )
        elif len(v) < 32:
            warnings.warn(
                "SECRET_KEY should be at least 32 characters for security!",
                UserWarning,
                stacklevel=2,
            )
        return v

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> str | list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            if isinstance(v, list) and "*" in v:
                env = cls.model_config.get("APP_ENV", "development")
                if env == "production":
                    raise ValueError("CORS wildcard '*' not allowed in production")
            return v
        raise ValueError(v)


settings = Settings()
