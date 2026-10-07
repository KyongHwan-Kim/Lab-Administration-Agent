"""add user signature path

Revision ID: 0002_user_signature
Revises: 0001_initial
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_signature"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("signature_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "signature_path")
