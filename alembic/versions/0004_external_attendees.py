"""add external attendees

Revision ID: 0004_external_attendees
Revises: 0003_projects
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_external_attendees"
down_revision: Union[str, Sequence[str], None] = "0003_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "external_attendees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("affiliation", sa.String(length=100), nullable=False),
        sa.Column("position", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("affiliation", "position", "name", name="uq_external_attendee"),
    )


def downgrade() -> None:
    op.drop_table("external_attendees")
