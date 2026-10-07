"""store generated overtime work logs

Revision ID: 0008_work_logs
Revises: 0007_project_profile
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_work_logs"
down_revision: Union[str, Sequence[str], None] = "0007_project_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "work_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_gid", sa.String(length=32), nullable=False),
        sa.Column("project_name", sa.String(length=200), nullable=False),
        sa.Column("source_key", sa.String(length=80), nullable=False),
        sa.Column("filename", sa.String(length=200), nullable=False),
        sa.Column("usage_date", sa.String(length=32), nullable=False),
        sa.Column("store_name", sa.String(length=200), nullable=False),
        sa.Column("pdf_path", sa.String(length=500), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_gid", "source_key", name="uq_work_log"),
    )
    op.create_index("ix_work_logs_project_gid", "work_logs", ["project_gid"])


def downgrade() -> None:
    op.drop_index("ix_work_logs_project_gid", table_name="work_logs")
    op.drop_table("work_logs")
