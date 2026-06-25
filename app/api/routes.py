from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.repositories.submission_repository import SubmissionRepository
from app.schemas.email import IngestEmailResponse
from app.services.email_intake import EmailIntakeService
from app.services.sqs_service import SqsService
from app.storage.factory import create_storage_service

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
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
    message_id: Annotated[str | None, Form()] = None,
) -> IngestEmailResponse:
    service = EmailIntakeService(db, settings)
    return await service.ingest_email(
        sender_email=str(sender_email),
        subject=subject,
        email_body=email_body,
        attachments=attachments,
        message_id=message_id,
        request_id=request_id,
    )


@router.get("/health")
def health(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    checks = {"api": "ok", "database": "ok", "s3": "ok", "sqs": "ok"}
    try:
        SubmissionRepository(db).check_connectivity()
    except Exception:
        checks["database"] = "error"
    try:
        create_storage_service(settings).check_connectivity()
    except Exception:
        checks["s3"] = "error"
    try:
        SqsService(settings).check_connectivity()
    except Exception:
        checks["sqs"] = "error"
    checks["status"] = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return checks
