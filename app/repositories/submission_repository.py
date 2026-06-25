from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Document, Submission


class SubmissionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_submission(self, *, sender_email: str, subject: str, email_body: str) -> Submission:
        submission = Submission(
            sender_email=sender_email,
            subject=subject,
            email_body=email_body,
            received_at=datetime.now(timezone.utc),
            status="received",
        )
        self._db.add(submission)
        self._db.flush()
        return submission

    def add_document(self, document: Document) -> Document:
        self._db.add(document)
        self._db.flush()
        return document

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()
