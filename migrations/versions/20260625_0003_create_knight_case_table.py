"""create knight case table

Revision ID: 20260625_0003
Revises: 20260624_0002
Create Date: 2026-06-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260625_0003"
down_revision: Union[str, None] = "20260624_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knight-case-table",
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("s3_location", sa.String(length=2048), nullable=False),
        sa.Column("report_location", sa.String(length=2048), nullable=True),
        sa.PrimaryKeyConstraint("case_id"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("knight-case-table", schema="public")
