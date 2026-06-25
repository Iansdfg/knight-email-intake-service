"""add document source

Revision ID: 20260624_0002
Revises: 20260624_0001
Create Date: 2026-06-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260624_0002"
down_revision: Union[str, None] = "20260624_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("source", sa.String(length=50), nullable=False, server_default="attachment"),
    )
    op.create_index("ix_documents_source", "documents", ["source"])
    op.alter_column("documents", "source", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_documents_source", table_name="documents")
    op.drop_column("documents", "source")
