"""store memos for spreadsheet usage rows

Revision ID: 0013_usage_memos
Revises: 0012_timestamp_not_null
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_usage_memos"
down_revision: Union[str, Sequence[str], None] = "0012_timestamp_not_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usage_memos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_gid", sa.String(length=32), nullable=False),
        sa.Column("row_key", sa.String(length=64), nullable=False),
        sa.Column("memo", sa.String(length=4000), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_gid", "row_key", name="uq_usage_memo"),
    )
    op.create_index("ix_usage_memos_project_gid", "usage_memos", ["project_gid"])
    op.alter_column("usage_memos", "memo", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_usage_memos_project_gid", table_name="usage_memos")
    op.drop_table("usage_memos")
