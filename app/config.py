from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Entra App Auditor"
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"

    # Mock data mode — set MOCK_DATA=false and fill in Azure credentials for prod
    MOCK_DATA: bool = True

    # Microsoft Entra ID OAuth
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_TENANT_ID: str = ""
    AZURE_REDIRECT_URI: str = "http://localhost:33333/auth/callback"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/audit.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
