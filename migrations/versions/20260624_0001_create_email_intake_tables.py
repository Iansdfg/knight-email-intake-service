"""create email intake tables

Revision ID: 20260624_0001
Revises:
Create Date: 2026-06-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260624_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_email", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False),
        sa.Column("email_body", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_submissions_sender_email", "submissions", ["sender_email"])
    op.create_index("ix_submissions_status", "submissions", ["status"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("s3_path", sa.String(length=2048), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("extension", sa.String(length=32), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("sheet_count", sa.Integer(), nullable=True),
        sa.Column("duplicate", sa.Boolean(), nullable=False),
        sa.Column("duplicate_of_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["duplicate_of_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_checksum", "documents", ["checksum"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_submission_id", "documents", ["submission_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_submission_id", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_checksum", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_submissions_status", table_name="submissions")
    op.drop_index("ix_submissions_sender_email", table_name="submissions")
    op.drop_table("submissions")
