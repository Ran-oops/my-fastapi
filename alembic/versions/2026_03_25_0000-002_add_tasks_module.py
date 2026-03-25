"""add tasks module

Revision ID: 002
Revises: 001
Create Date: 2026-03-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[import-untyped]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_name", sa.String(length=100), nullable=False),
        sa.Column("celery_task_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_records_id"), "task_records", ["id"], unique=False)
    op.create_index(op.f("ix_task_records_task_name"), "task_records", ["task_name"], unique=False)
    op.create_index(op.f("ix_task_records_celery_task_id"), "task_records", ["celery_task_id"], unique=False)
    op.create_index(op.f("ix_task_records_status"), "task_records", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_task_records_status"), table_name="task_records")
    op.drop_index(op.f("ix_task_records_celery_task_id"), table_name="task_records")
    op.drop_index(op.f("ix_task_records_task_name"), table_name="task_records")
    op.drop_index(op.f("ix_task_records_id"), table_name="task_records")
    op.drop_table("task_records")
