"""add vector memory retrieval

Revision ID: 50b34180333d
Revises: 359039e39387
Create Date: 2026-07-21 18:57:32.466136
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "50b34180333d"
down_revision: str | None = "359039e39387"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute(sa.text("UPDATE memories SET embedding = NULL"))
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        op.alter_column(
            "memories",
            "embedding",
            existing_type=sa.LargeBinary(),
            type_=Vector(256),
            existing_nullable=True,
            postgresql_using="NULL::vector",
        )
    else:
        with op.batch_alter_table("memories") as batch:
            batch.alter_column(
                "embedding",
                existing_type=sa.LargeBinary(),
                type_=sa.JSON(),
                existing_nullable=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    op.execute(sa.text("UPDATE memories SET embedding = NULL"))
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "memories",
            "embedding",
            existing_type=Vector(256),
            type_=sa.LargeBinary(),
            existing_nullable=True,
            postgresql_using="NULL::bytea",
        )
    else:
        with op.batch_alter_table("memories") as batch:
            batch.alter_column(
                "embedding",
                existing_type=sa.JSON(),
                type_=sa.LargeBinary(),
                existing_nullable=True,
            )
