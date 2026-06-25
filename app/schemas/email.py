from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class EmailSubmissionForm(BaseModel):
    sender_email: EmailStr
    subject: str
    email_body: str


class DocumentSummary(BaseModel):
    id: UUID
    original_filename: str
    source: str
    mime_type: str
    file_size: int
    s3_path: str
    checksum: str
    status: str
    extension: str | None
    page_count: int | None
    sheet_count: int | None
    duplicate: bool
    duplicate_of_document_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestEmailResponse(BaseModel):
    case_id: UUID
    status: str
