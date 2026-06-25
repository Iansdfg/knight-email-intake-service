from datetime import datetime
from uuid import UUID
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(1024), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="attachment", index=True)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    s3_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="stored", index=True)
    extension: Mapped[str | None] = mapped_column(String(32), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sheet_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duplicate_of_document_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    submission = relationship("Submission", back_populates="documents")
    duplicate_of = relationship("Document", remote_side=[id])
