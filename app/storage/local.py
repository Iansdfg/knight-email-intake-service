from pathlib import Path
from uuid import UUID

from app.config import Settings
from app.storage.base import AttachmentStorageService


class LocalStorageService(AttachmentStorageService):
    def __init__(self, settings: Settings) -> None:
        self._root = Path(settings.local_storage_root)

    def attachment_collection_path(self, *, case_id: UUID) -> str:
        return str(self._attachment_dir(case_id)) + "/"

    def upload_attachment(
        self,
        *,
        case_id: UUID,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> tuple[str, str]:
        attachment_dir = self._attachment_dir(case_id)
        attachment_dir.mkdir(parents=True, exist_ok=True)
        file_path = attachment_dir / filename
        file_path.write_bytes(content)
        return str(file_path), str(file_path)

    def check_connectivity(self) -> bool:
        self._root.mkdir(parents=True, exist_ok=True)
        return self._root.exists()

    def _attachment_dir(self, case_id: UUID) -> Path:
        return self._root / "cases" / str(case_id) / "original"
