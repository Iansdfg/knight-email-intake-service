from datetime import datetime, timezone
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Document
from app.repositories.submission_repository import SubmissionRepository
from app.schemas.email import DocumentSummary, IngestEmailResponse
from app.storage.factory import create_storage_service
from app.utils.checksum import sha256_checksum
from app.utils.duplicates import find_duplicate_of
from app.utils.email_body import email_body_document_content
from app.utils.email_tables import email_tables_workbook_content
from app.utils.filenames import safe_attachment_filename
from app.utils.inventory import inspect_document


class EmailIntakeService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._repository = SubmissionRepository(db)
        self._storage = create_storage_service(settings)

    async def ingest_email(
        self,
        *,
        sender_email: str,
        subject: str,
        email_body: str,
        attachments: list[UploadFile],
    ) -> IngestEmailResponse:
        try:
            submission = self._repository.create_submission(
                sender_email=sender_email,
                subject=subject,
                email_body=email_body,
            )
            seen_checksums: dict[str, UUID] = {}
            documents: list[Document] = []
            email_body_document = self._create_email_body_document(
                submission_id=submission.id,
                email_body=email_body,
            )
            self._repository.add_document(email_body_document)
            documents.append(email_body_document)
            email_tables_document = self._create_email_tables_document(
                submission_id=submission.id,
                email_body=email_body,
            )
            if email_tables_document is not None:
                self._repository.add_document(email_tables_document)
                documents.append(email_tables_document)

            for attachment in attachments:
                content = await attachment.read()
                filename = safe_attachment_filename(attachment.filename)
                mime_type = attachment.content_type or "application/octet-stream"
                checksum = sha256_checksum(content)
                duplicate_of_document_id = find_duplicate_of(checksum, seen_checksums)
                inventory = inspect_document(filename, content, mime_type)
                storage_path = self._storage.upload_attachment(
                    submission_id=submission.id,
                    filename=filename,
                    content=content,
                    mime_type=mime_type,
                )

                document = Document(
                    submission_id=submission.id,
                    original_filename=filename,
                    source="attachment",
                    mime_type=mime_type,
                    file_size=len(content),
                    s3_path=storage_path,
                    checksum=checksum,
                    status="stored",
                    extension=inventory.extension,
                    page_count=inventory.page_count,
                    sheet_count=inventory.sheet_count,
                    duplicate=duplicate_of_document_id is not None,
                    duplicate_of_document_id=duplicate_of_document_id,
                    created_at=datetime.now(timezone.utc),
                )
                self._repository.add_document(document)
                documents.append(document)

                if duplicate_of_document_id is None:
                    seen_checksums[checksum] = document.id

            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        return IngestEmailResponse(
            submission_id=submission.id,
            document_count=len(documents),
            duplicate_count=sum(1 for document in documents if document.duplicate),
            documents=[DocumentSummary.model_validate(document) for document in documents],
        )

    def _create_email_body_document(self, *, submission_id: UUID, email_body: str) -> Document:
        filename = "email_body.html"
        content = email_body_document_content(email_body)
        checksum = sha256_checksum(content)
        storage_path = self._storage.upload_attachment(
            submission_id=submission_id,
            filename=filename,
            content=content,
            mime_type="text/html",
        )
        return Document(
            submission_id=submission_id,
            original_filename=filename,
            source="email_body",
            mime_type="text/html",
            file_size=len(content),
            s3_path=storage_path,
            checksum=checksum,
            status="stored",
            extension="html",
            page_count=None,
            sheet_count=None,
            duplicate=False,
            duplicate_of_document_id=None,
            created_at=datetime.now(timezone.utc),
        )

    def _create_email_tables_document(self, *, submission_id: UUID, email_body: str) -> Document | None:
        content, table_count = email_tables_workbook_content(email_body)
        if content is None:
            return None

        filename = "email_tables.xlsx"
        checksum = sha256_checksum(content)
        storage_path = self._storage.upload_attachment(
            submission_id=submission_id,
            filename=filename,
            content=content,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return Document(
            submission_id=submission_id,
            original_filename=filename,
            source="email_tables",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size=len(content),
            s3_path=storage_path,
            checksum=checksum,
            status="stored",
            extension="xlsx",
            page_count=None,
            sheet_count=table_count,
            duplicate=False,
            duplicate_of_document_id=None,
            created_at=datetime.now(timezone.utc),
        )
