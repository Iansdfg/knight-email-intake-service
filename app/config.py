from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    storage_backend: str = "local"
    local_storage_root: str = "local_storage"
    root_path: str = ""
    aws_region: str
    s3_bucket: str
    sqs_queue_url: str | None = None
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 8025
    smtp_reply_from: str = "submissions@knight.local"
    smtp_reply_enabled: bool = False
    duplicate_window_minutes: int = Field(default=60, ge=1)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
