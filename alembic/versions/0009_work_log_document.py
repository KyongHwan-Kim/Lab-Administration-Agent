"""store the overtime log form as structured rows

Revision ID: 0009_work_log_document
Revises: 0008_work_logs
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_work_log_document"
down_revision: Union[str, Sequence[str], None] = "0008_work_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("work_logs", sa.Column("document", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.alter_column("work_logs", "document", server_default=None)


def downgrade() -> None:
    op.drop_column("work_logs", "document")
