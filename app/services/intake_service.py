import logging
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Document
from app.repositories.submission_repository import SubmissionRepository
from app.schemas.email import IngestEmailResponse
from app.services.intake_models import ParsedEmail
from app.services.reply_service import ReplyService
from app.services.sqs_service import SqsService
from app.storage.factory import create_storage_service
from app.utils.checksum import sha256_checksum
from app.utils.email_body import email_body_document_content
from app.utils.email_tables import email_tables_workbook_content
from app.utils.filenames import safe_attachment_filename
from app.utils.logging import log_event, monotonic_duration

logger = logging.getLogger(__name__)


class IntakeService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._settings = settings
        self._repository = SubmissionRepository(db)
        self._storage = create_storage_service(settings)
        self._sqs = SqsService(settings)
        self._reply = ReplyService(settings)

    def ingest(self, parsed_email: ParsedEmail, *, request_id: str | None = None) -> IngestEmailResponse:
        started_at = time.monotonic()
        attachment_hashes = [sha256_checksum(attachment.content) for attachment in parsed_email.attachments]
        idempotency_key = self._idempotency_key(
            sender_email=parsed_email.sender_email,
            subject=parsed_email.subject,
            message_id=parsed_email.message_id,
            attachment_hashes=attachment_hashes,
        )
        duplicate = self._repository.find_recent_duplicate_case(
            idempotency_key=idempotency_key,
            since=datetime.now(timezone.utc) - timedelta(minutes=self._settings.duplicate_window_minutes),
        )
        if duplicate is not None:
            log_event(
                logger,
                event="duplicate_submission_detected",
                case_id=str(duplicate.case_id),
                request_id=request_id,
                duration=monotonic_duration(started_at),
            )
            return IngestEmailResponse(case_id=duplicate.case_id, status=duplicate.status)

        case_id = uuid4()
        s3_location = self._storage.attachment_collection_path(case_id=case_id)
        try:
            knight_case = self._repository.create_case(
                case_id=case_id,
                sender_email=parsed_email.sender_email,
                recipients=parsed_email.recipients,
                subject=parsed_email.subject,
                email_body=parsed_email.email_body,
                message_id=parsed_email.message_id,
                attachment_count=len(parsed_email.attachments),
                idempotency_key=idempotency_key,
                s3_location=s3_location,
            )
            submission = self._repository.create_submission(
                case_id=case_id,
                sender_email=parsed_email.sender_email,
                recipients=parsed_email.recipients,
                subject=parsed_email.subject,
                email_body=parsed_email.email_body,
                message_id=parsed_email.message_id,
                attachment_count=len(parsed_email.attachments),
                idempotency_key=idempotency_key,
            )
            log_event(logger, event="case_created", case_id=str(case_id), request_id=request_id)

            email_body_content = email_body_document_content(parsed_email.email_body)
            email_body_path, email_body_key = self._storage.upload_attachment(
                case_id=case_id,
                filename="email_body.html",
                content=email_body_content,
                mime_type="text/html",
            )
            self._repository.add_document(
                self._document(
                    case_id=case_id,
                    submission_id=submission.id,
                    filename="email_body.html",
                    source="email_body",
                    mime_type="text/html",
                    content=email_body_content,
                    s3_path=email_body_path,
                    s3_key=email_body_key,
                    sheet_count=None,
                )
            )

            email_tables_content, table_count = email_tables_workbook_content(parsed_email.email_body)
            if email_tables_content is not None:
                email_tables_path, email_tables_key = self._storage.upload_attachment(
                    case_id=case_id,
                    filename="email_tables.xlsx",
                    content=email_tables_content,
                    mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                knight_case.report_location = email_tables_path
                self._repository.add_document(
                    self._document(
                        case_id=case_id,
                        submission_id=submission.id,
                        filename="email_tables.xlsx",
                        source="email_tables",
                        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        content=email_tables_content,
                        s3_path=email_tables_path,
                        s3_key=email_tables_key,
                        sheet_count=table_count,
                    )
                )
                log_event(
                    logger,
                    event="email_tables_stored",
                    case_id=str(case_id),
                    request_id=request_id,
                    extra={"table_count": table_count},
                )

            for index, attachment in enumerate(parsed_email.attachments):
                filename = safe_attachment_filename(attachment.filename)
                s3_path, s3_key = self._storage.upload_attachment(
                    case_id=case_id,
                    filename=filename,
                    content=attachment.content,
                    mime_type=attachment.mime_type,
                )
                document = self._document(
                    case_id=case_id,
                    submission_id=submission.id,
                    filename=filename,
                    source="attachment",
                    mime_type=attachment.mime_type,
                    content=attachment.content,
                    s3_path=s3_path,
                    s3_key=s3_key,
                    checksum=attachment_hashes[index],
                    sheet_count=None,
                )
                self._repository.add_document(document)

            log_event(
                logger,
                event="attachments_uploaded",
                case_id=str(case_id),
                request_id=request_id,
                extra={"attachment_count": len(parsed_email.attachments)},
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            log_event(
                logger,
                event="intake_failed",
                case_id=str(case_id),
                request_id=request_id,
                duration=monotonic_duration(started_at),
                level=logging.ERROR,
            )
            raise

        self._sqs.publish_case_created(
            case_id=knight_case.case_id,
            received_at=knight_case.received_at,
            attachment_count=knight_case.attachment_count,
        )
        log_event(logger, event="sqs_published", case_id=str(case_id), request_id=request_id)

        try:
            self._reply.send_acknowledgement(
                recipient=parsed_email.sender_email,
                case_id=knight_case.case_id,
            )
            log_event(logger, event="acknowledgement_sent", case_id=str(case_id), request_id=request_id)
        except Exception:
            log_event(
                logger,
                event="acknowledgement_failed",
                case_id=str(case_id),
                request_id=request_id,
                level=logging.ERROR,
            )

        log_event(
            logger,
            event="email_received",
            case_id=str(case_id),
            request_id=request_id,
            duration=monotonic_duration(started_at),
        )
        return IngestEmailResponse(case_id=knight_case.case_id, status=knight_case.status)

    def _document(
        self,
        *,
        case_id,
        submission_id,
        filename: str,
        source: str,
        mime_type: str,
        content: bytes,
        s3_path: str,
        s3_key: str,
        sheet_count: int | None,
        checksum: str | None = None,
    ) -> Document:
        return Document(
            case_id=case_id,
            submission_id=submission_id,
            original_filename=filename,
            source=source,
            mime_type=mime_type,
            file_size=len(content),
            s3_path=s3_path,
            s3_key=s3_key,
            checksum=checksum or sha256_checksum(content),
            status="stored",
            extension=filename.rsplit(".", 1)[-1].lower() if "." in filename else None,
            page_count=None,
            sheet_count=sheet_count,
            duplicate=False,
            duplicate_of_document_id=None,
            created_at=datetime.now(timezone.utc),
        )

    def _idempotency_key(
        self,
        *,
        sender_email: str,
        subject: str,
        message_id: str | None,
        attachment_hashes: list[str],
    ) -> str:
        raw = "|".join(
            [
                sender_email.strip().lower(),
                subject.strip(),
                message_id or "",
                ",".join(sorted(attachment_hashes)),
            ]
        )
        return sha256_checksum(raw.encode("utf-8"))
