"""phase 2 case intake

Revision ID: 20260625_0004
Revises: 20260625_0003
Create Date: 2026-06-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260625_0004"
down_revision: Union[str, None] = "20260625_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "knight-case-table",
        sa.Column("sender_email", sa.String(length=320), nullable=False, server_default="unknown"),
        schema="public",
    )
    op.add_column("knight-case-table", sa.Column("recipients", sa.Text(), nullable=True), schema="public")
    op.add_column(
        "knight-case-table",
        sa.Column("subject", sa.String(length=998), nullable=False, server_default="unknown"),
        schema="public",
    )
    op.add_column(
        "knight-case-table",
        sa.Column("email_body", sa.Text(), nullable=False, server_default=""),
        schema="public",
    )
    op.add_column(
        "knight-case-table",
        sa.Column("message_id", sa.String(length=998), nullable=True),
        schema="public",
    )
    op.add_column(
        "knight-case-table",
        sa.Column("idempotency_key", sa.String(length=64), nullable=False, server_default="legacy"),
        schema="public",
    )
    op.add_column(
        "knight-case-table",
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.add_column(
        "knight-case-table",
        sa.Column("status", sa.String(length=50), nullable=False, server_default="RECEIVED"),
        schema="public",
    )
    op.add_column(
        "knight-case-table",
        sa.Column("attachment_count", sa.Integer(), nullable=False, server_default="0"),
        schema="public",
    )
    op.create_index("ix_knight_case_sender_email", "knight-case-table", ["sender_email"], schema="public")
    op.create_index("ix_knight_case_message_id", "knight-case-table", ["message_id"], schema="public")
    op.create_index("ix_knight_case_idempotency_key", "knight-case-table", ["idempotency_key"], schema="public")
    op.create_index("ix_knight_case_status", "knight-case-table", ["status"], schema="public")

    op.add_column("submissions", sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("submissions", sa.Column("recipients", sa.Text(), nullable=True))
    op.add_column("submissions", sa.Column("message_id", sa.String(length=998), nullable=True))
    op.add_column("submissions", sa.Column("attachment_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("submissions", sa.Column("idempotency_key", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_submissions_case_id_knight_case",
        "submissions",
        "knight-case-table",
        ["case_id"],
        ["case_id"],
        source_schema=None,
        referent_schema="public",
        ondelete="SET NULL",
    )
    op.create_index("ix_submissions_case_id", "submissions", ["case_id"])
    op.create_index("ix_submissions_message_id", "submissions", ["message_id"])
    op.create_index("ix_submissions_idempotency_key", "submissions", ["idempotency_key"])

    op.add_column("documents", sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("documents", sa.Column("s3_key", sa.String(length=2048), nullable=True))
    op.create_foreign_key(
        "fk_documents_case_id_knight_case",
        "documents",
        "knight-case-table",
        ["case_id"],
        ["case_id"],
        source_schema=None,
        referent_schema="public",
        ondelete="CASCADE",
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"])

    for column_name in [
        "sender_email",
        "subject",
        "email_body",
        "idempotency_key",
        "received_at",
        "status",
        "attachment_count",
    ]:
        op.alter_column("knight-case-table", column_name, server_default=None, schema="public")
    op.alter_column("submissions", "attachment_count", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_documents_case_id", table_name="documents")
    op.drop_constraint("fk_documents_case_id_knight_case", "documents", type_="foreignkey")
    op.drop_column("documents", "s3_key")
    op.drop_column("documents", "case_id")

    op.drop_index("ix_submissions_idempotency_key", table_name="submissions")
    op.drop_index("ix_submissions_message_id", table_name="submissions")
    op.drop_index("ix_submissions_case_id", table_name="submissions")
    op.drop_constraint("fk_submissions_case_id_knight_case", "submissions", type_="foreignkey")
    op.drop_column("submissions", "idempotency_key")
    op.drop_column("submissions", "attachment_count")
    op.drop_column("submissions", "message_id")
    op.drop_column("submissions", "recipients")
    op.drop_column("submissions", "case_id")

    op.drop_index("ix_knight_case_status", table_name="knight-case-table", schema="public")
    op.drop_index("ix_knight_case_idempotency_key", table_name="knight-case-table", schema="public")
    op.drop_index("ix_knight_case_message_id", table_name="knight-case-table", schema="public")
    op.drop_index("ix_knight_case_sender_email", table_name="knight-case-table", schema="public")
    op.drop_column("knight-case-table", "attachment_count", schema="public")
    op.drop_column("knight-case-table", "status", schema="public")
    op.drop_column("knight-case-table", "received_at", schema="public")
    op.drop_column("knight-case-table", "idempotency_key", schema="public")
    op.drop_column("knight-case-table", "message_id", schema="public")
    op.drop_column("knight-case-table", "email_body", schema="public")
    op.drop_column("knight-case-table", "subject", schema="public")
    op.drop_column("knight-case-table", "recipients", schema="public")
    op.drop_column("knight-case-table", "sender_email", schema="public")
