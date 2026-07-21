"""add assistant opening message

Revision ID: 8f1d6e7a2c41
Revises: 50b34180333d
Create Date: 2026-07-21 23:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8f1d6e7a2c41"
down_revision: str | None = "50b34180333d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("assistants") as batch:
        batch.add_column(sa.Column("opening_message", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("assistants") as batch:
        batch.drop_column("opening_message")
