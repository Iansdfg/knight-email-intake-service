from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import Settings
from app.schemas.email import IngestEmailResponse
from app.services.intake_models import IntakeAttachment, ParsedEmail
from app.services.intake_service import IntakeService
from app.utils.filenames import safe_attachment_filename


class EmailIntakeService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._intake_service = IntakeService(db, settings)

    async def ingest_email(
        self,
        *,
        sender_email: str,
        subject: str,
        email_body: str,
        attachments: list[UploadFile],
        recipients: list[str] | None = None,
        message_id: str | None = None,
        request_id: str | None = None,
    ) -> IngestEmailResponse:
        parsed_email = ParsedEmail(
            sender_email=sender_email,
            recipients=recipients or [],
            subject=subject,
            email_body=email_body,
            attachments=[
                IntakeAttachment(
                    filename=safe_attachment_filename(attachment.filename),
                    content=await attachment.read(),
                    mime_type=attachment.content_type or "application/octet-stream",
                )
                for attachment in attachments
            ],
            message_id=message_id,
        )
        return self._intake_service.ingest(parsed_email, request_id=request_id)
