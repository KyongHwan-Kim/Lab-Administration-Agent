"""store a display name and email on each user

Revision ID: 0014_user_profile
Revises: 0013_usage_memos
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_user_profile"
down_revision: Union[str, Sequence[str], None] = "0013_usage_memos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("users", sa.Column("email", sa.String(length=200), nullable=True))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.alter_column("users", "name", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "email")
    op.drop_column("users", "name")
