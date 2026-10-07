"""allow overtime entries before project assignment

Revision ID: 0005_unassigned_entries
Revises: 0004_external_attendees
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_unassigned_entries"
down_revision: Union[str, Sequence[str], None] = "0004_external_attendees"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("overtime_entries", "project_gid", existing_type=sa.String(length=32), nullable=True)
    op.alter_column("overtime_entries", "project_name", existing_type=sa.String(length=200), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM overtime_entries WHERE project_gid IS NULL")
    op.alter_column("overtime_entries", "project_gid", existing_type=sa.String(length=32), nullable=False)
    op.alter_column("overtime_entries", "project_name", existing_type=sa.String(length=200), nullable=False)
