"""store receipt PDFs linked to spreadsheet rows

Revision ID: 0006_sheet_receipts
Revises: 0005_unassigned_entries
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_sheet_receipts"
down_revision: Union[str, Sequence[str], None] = "0005_unassigned_entries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sheet_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_gid", sa.String(length=32), nullable=False),
        sa.Column("row_key", sa.String(length=64), nullable=False),
        sa.Column("pdf_path", sa.String(length=500), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_gid", "row_key", name="uq_sheet_receipt"),
    )
    op.create_index("ix_sheet_receipts_project_gid", "sheet_receipts", ["project_gid"])


def downgrade() -> None:
    op.drop_index("ix_sheet_receipts_project_gid", table_name="sheet_receipts")
    op.drop_table("sheet_receipts")
