"""add search base functionality

Revision ID: 003
Revises: 002
Create Date: 2026-03-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[import-untyped]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
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

    # 3. Create common indexes (SQLite and PostgreSQL both support)
    op.create_index("ix_products_name", "products", ["name"])
    op.create_index("ix_products_sku", "products", ["sku"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_index("ix_products_name", table_name="products")

    op.drop_index("ix_search_history_created_at", table_name="search_history")
    op.drop_index("ix_search_history_user_id", table_name="search_history")
    op.drop_table("search_history")

    op.drop_column("users", "search_vector")
    op.drop_column("orders", "search_vector")
    op.drop_column("products", "search_vector")
