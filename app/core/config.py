from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Resume Screening"
    app_env: str = "development"
    database_url: str = "sqlite:///./resume_screening.db"
    allowed_origins: str = "*"
    max_upload_mb: int = Field(default=8, ge=1, le=50)
    enable_hosted_llm: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
