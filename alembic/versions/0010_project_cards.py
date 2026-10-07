"""store card numbers used to assign extracted receipts

Revision ID: 0010_project_cards
Revises: 0009_work_log_document
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_project_cards"
down_revision: Union[str, Sequence[str], None] = "0009_work_log_document"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("number", sa.String(length=40), nullable=False),
        sa.Column("number_key", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number_key", name="uq_project_card_number"),
    )
    op.create_index("ix_project_cards_project_id", "project_cards", ["project_id"])
    op.alter_column("project_cards", "label", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_project_cards_project_id", table_name="project_cards")
    op.drop_table("project_cards")
