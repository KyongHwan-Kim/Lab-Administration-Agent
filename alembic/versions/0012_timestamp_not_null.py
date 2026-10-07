"""make receipt and work log timestamps required

Revision ID: 0012_timestamp_not_null
Revises: 0011_sheet_rows
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_timestamp_not_null"
down_revision: Union[str, Sequence[str], None] = "0011_sheet_rows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE sheet_receipts SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
    op.execute(sa.text("UPDATE work_logs SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
    op.execute(sa.text("UPDATE work_logs SET updated_at = created_at WHERE updated_at IS NULL"))
    op.alter_column("sheet_receipts", "created_at", existing_type=sa.DateTime(), nullable=False)
    op.alter_column("work_logs", "created_at", existing_type=sa.DateTime(), nullable=False)
    op.alter_column("work_logs", "updated_at", existing_type=sa.DateTime(), nullable=False)


def downgrade() -> None:
    op.alter_column("sheet_receipts", "created_at", existing_type=sa.DateTime(), nullable=True)
    op.alter_column("work_logs", "created_at", existing_type=sa.DateTime(), nullable=True)
    op.alter_column("work_logs", "updated_at", existing_type=sa.DateTime(), nullable=True)
