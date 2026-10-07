"""store a cleaned snapshot of google sheet usage rows

Revision ID: 0011_sheet_rows
Revises: 0010_project_cards
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_sheet_rows"
down_revision: Union[str, Sequence[str], None] = "0010_project_cards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sheet_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_gid", sa.String(length=32), nullable=False),
        sa.Column("project_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("row_key", sa.String(length=64), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_gid", "row_key", name="uq_sheet_row"),
    )
    op.create_index("ix_sheet_rows_project_gid", "sheet_rows", ["project_gid"])
    op.alter_column("sheet_rows", "project_name", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_sheet_rows_project_gid", table_name="sheet_rows")
    op.drop_table("sheet_rows")
