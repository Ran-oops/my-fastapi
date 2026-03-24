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
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Enterprise FastAPI Project"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    USER_DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/user_db"

    BUSINESS_DATABASE_URL: str = (
        "mssql+aioodbc://sa:password@localhost:1433/business_db?driver=ODBC+Driver+17+for+SQL+Server"
    )

    CONFIG_DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/config_db"

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
