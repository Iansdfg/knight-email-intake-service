from abc import ABC, abstractmethod
from uuid import UUID


class AttachmentStorageService(ABC):
    @abstractmethod
    def upload_attachment(
        self,
        *,
        submission_id: UUID,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> str:
        raise NotImplementedError
