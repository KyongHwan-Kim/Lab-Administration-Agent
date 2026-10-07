"""add research profile fields to projects

Revision ID: 0007_project_profile
Revises: 0006_sheet_receipts
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_project_profile"
down_revision: Union[str, Sequence[str], None] = "0006_sheet_receipts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = (
    ("project_number", 100),
    ("principal_investigator", 200),
    ("funding_agency", 200),
    ("program_name", 200),
    ("research_title", 200),
)


def upgrade() -> None:
    for name, length in _COLUMNS:
        op.add_column("projects", sa.Column(name, sa.String(length=length), nullable=False, server_default=""))
        op.alter_column("projects", name, server_default=None)


def downgrade() -> None:
    for name, _length in reversed(_COLUMNS):
        op.drop_column("projects", name)
