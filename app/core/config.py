from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-secret-key-in-production"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Enterprise FastAPI Project"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # User Database (PostgreSQL) - Read/Write
    USER_DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:password@localhost:5432/user_db"
    )

    # Business Database (SQL Server) - Read/Write
    BUSINESS_DATABASE_URL: str = "mssql+aioodbc://sa:password@localhost:1433/business_db?driver=ODBC+Driver+17+for+SQL+Server"

    # Config Database (MySQL) - Read Only
    CONFIG_DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/config_db"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
