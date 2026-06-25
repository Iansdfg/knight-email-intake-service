from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Document, KnightCase, Submission


class SubmissionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_case(
        self,
        *,
        case_id: UUID,
        sender_email: str,
        recipients: list[str],
        subject: str,
        email_body: str,
        message_id: str | None,
        attachment_count: int,
        idempotency_key: str,
        s3_location: str,
        report_location: str | None = None,
    ) -> KnightCase:
        knight_case = KnightCase(
            case_id=case_id,
            sender_email=sender_email,
            recipients=",".join(recipients) if recipients else None,
            subject=subject,
            email_body=email_body,
            message_id=message_id,
            idempotency_key=idempotency_key,
            received_at=datetime.now(timezone.utc),
            status="RECEIVED",
            attachment_count=attachment_count,
            s3_location=s3_location,
            report_location=report_location,
        )
        self._db.add(knight_case)
        self._db.flush()
        return knight_case

    def create_submission(
        self,
        *,
        case_id: UUID,
        sender_email: str,
        recipients: list[str],
        subject: str,
        email_body: str,
        message_id: str | None,
        attachment_count: int,
        idempotency_key: str,
    ) -> Submission:
        submission = Submission(
            case_id=case_id,
            sender_email=sender_email,
            recipients=",".join(recipients) if recipients else None,
            subject=subject,
            email_body=email_body,
            message_id=message_id,
            received_at=datetime.now(timezone.utc),
            status="RECEIVED",
            attachment_count=attachment_count,
            idempotency_key=idempotency_key,
        )
        self._db.add(submission)
        self._db.flush()
        return submission

    def add_document(self, document: Document) -> Document:
        self._db.add(document)
        self._db.flush()
        return document

    def find_recent_duplicate_case(
        self,
        *,
        idempotency_key: str,
        since: datetime,
    ) -> KnightCase | None:
        statement = (
            select(KnightCase)
            .where(KnightCase.idempotency_key == idempotency_key)
            .where(KnightCase.received_at >= since)
            .order_by(KnightCase.received_at.desc())
            .limit(1)
        )
        return self._db.execute(statement).scalar_one_or_none()

    def check_connectivity(self) -> bool:
        self._db.execute(text("SELECT 1"))
        return True

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()
