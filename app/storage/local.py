from pathlib import Path
from uuid import UUID

from app.config import Settings
from app.storage.base import AttachmentStorageService


class LocalStorageService(AttachmentStorageService):
    def __init__(self, settings: Settings) -> None:
        self._root = Path(settings.local_storage_root)

    def upload_attachment(
        self,
        *,
        submission_id: UUID,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> str:
        attachment_dir = self._root / "submissions" / str(submission_id) / "attachments"
        attachment_dir.mkdir(parents=True, exist_ok=True)
        file_path = attachment_dir / filename
        file_path.write_bytes(content)
        return str(file_path)
