from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/email_intake"
    storage_backend: str = "local"
    local_storage_root: str = "local_storage"
    root_path: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "email-intake-submissions"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
