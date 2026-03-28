"""add search base functionality

Revision ID: 2026_03_28_0000-003
Revises: 2026_03_27_0000-001
Create Date: 2026-03-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026_03_28_0000-003"
down_revision: Union[str, None] = "2026_03_27_0000-001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add search_vector columns (TEXT type, compatible with both databases)
    op.add_column("products", sa.Column("search_vector", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("search_vector", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("search_vector", sa.Text(), nullable=True))

    # 2. Create search_history table
    op.create_table(
        "search_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query", sa.String(length=200), nullable=False),
        sa.Column("search_type", sa.String(length=20), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_search_history_user_id", "search_history", ["user_id"])
    op.create_index("ix_search_history_created_at", "search_history", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_search_history_created_at", table_name="search_history")
    op.drop_index("ix_search_history_user_id", table_name="search_history")
    op.drop_table("search_history")

    op.drop_column("users", "search_vector")
    op.drop_column("orders", "search_vector")
    op.drop_column("products", "search_vector")
