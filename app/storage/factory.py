from app.config import Settings
from app.storage.base import AttachmentStorageService
from app.storage.local import LocalStorageService
from app.storage.s3 import S3StorageService


def create_storage_service(settings: Settings) -> AttachmentStorageService:
    backend = settings.storage_backend.strip().lower()
    if backend == "local":
        return LocalStorageService(settings)
    if backend == "s3":
        return S3StorageService(settings)
    raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")
