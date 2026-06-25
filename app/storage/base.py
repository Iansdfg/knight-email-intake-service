from abc import ABC, abstractmethod
from uuid import UUID


class AttachmentStorageService(ABC):
    @abstractmethod
    def attachment_collection_path(self, *, case_id: UUID) -> str:
        raise NotImplementedError

    @abstractmethod
    def upload_attachment(
        self,
        *,
        case_id: UUID,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> tuple[str, str]:
        raise NotImplementedError

    @abstractmethod
    def check_connectivity(self) -> bool:
        raise NotImplementedError
