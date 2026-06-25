from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.schemas.email import IngestEmailResponse
from app.services.email_intake import EmailIntakeService

router = APIRouter()


@router.post(
    "/ingest-email",
    response_model=IngestEmailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_email(
    sender_email: Annotated[EmailStr, Form()],
    subject: Annotated[str, Form()],
    email_body: Annotated[str, Form()],
    attachments: Annotated[list[UploadFile], File()],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestEmailResponse:
    service = EmailIntakeService(db, settings)
    return await service.ingest_email(
        sender_email=str(sender_email),
        subject=subject,
        email_body=email_body,
        attachments=attachments,
    )
