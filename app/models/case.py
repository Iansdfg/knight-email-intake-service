from datetime import datetime
from uuid import UUID
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class KnightCase(Base):
    __tablename__ = "knight-case-table"

    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sender_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    recipients: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    email_body: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[str | None] = mapped_column(String(998), nullable=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="RECEIVED", index=True)
    attachment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    s3_location: Mapped[str] = mapped_column(String(2048), nullable=False)
    report_location: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    submissions = relationship("Submission", back_populates="case")
    documents = relationship("Document", back_populates="case")
