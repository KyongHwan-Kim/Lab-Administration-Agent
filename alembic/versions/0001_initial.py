"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table(
        "overtime_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_gid", sa.String(length=32), nullable=False),
        sa.Column("project_name", sa.String(length=200), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("pdf_path", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_overtime_entries_project_gid", "overtime_entries", ["project_gid"])


def downgrade() -> None:
    op.drop_index("ix_overtime_entries_project_gid", table_name="overtime_entries")
    op.drop_table("overtime_entries")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
