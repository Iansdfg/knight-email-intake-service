from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.database import SessionLocal
from app.models import Document
from app.services.email_intake import EmailIntakeService


def main() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        service = EmailIntakeService(db, settings)
        email_body_documents = (
            db.query(Document)
            .filter(Document.source == "email_body")
            .order_by(Document.created_at.asc())
            .all()
        )

        created = 0
        for email_body_document in email_body_documents:
            existing = (
                db.query(Document)
                .filter(
                    Document.submission_id == email_body_document.submission_id,
                    Document.source == "email_tables",
                )
                .first()
            )
            if existing is not None:
                continue

            body_path = Path(email_body_document.s3_path)
            if not body_path.exists():
                continue

            document = service._create_email_tables_document(
                submission_id=email_body_document.submission_id,
                email_body=body_path.read_text(encoding="utf-8"),
            )
            if document is None:
                continue

            db.add(document)
            created += 1

        db.commit()
        print(f"Created {created} email table workbook document(s).")


if __name__ == "__main__":
    main()
