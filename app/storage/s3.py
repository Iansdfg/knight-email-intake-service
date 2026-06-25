from uuid import UUID

import boto3

from app.config import Settings
from app.storage.base import AttachmentStorageService


class S3StorageService(AttachmentStorageService):
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        self._client = boto3.client("s3", region_name=settings.aws_region)

    def attachment_collection_path(self, *, case_id: UUID) -> str:
        return f"s3://{self._bucket}/cases/{case_id}/original/"

    def upload_attachment(
        self,
        *,
        case_id: UUID,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> tuple[str, str]:
        key = f"cases/{case_id}/original/{filename}"
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=mime_type,
        )
        return f"s3://{self._bucket}/{key}", key

    def check_connectivity(self) -> bool:
        self._client.head_bucket(Bucket=self._bucket)
        return True
