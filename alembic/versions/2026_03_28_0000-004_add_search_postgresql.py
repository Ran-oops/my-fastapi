"""add search PostgreSQL functionality

Revision ID: 004
Revises: 003
Create Date: 2026-03-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # 1. Install pg_trgm extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2. Create GIN indexes for search_vector columns
    op.execute("CREATE INDEX ix_products_search_vector ON products USING GIN(search_vector)")
    op.execute("CREATE INDEX ix_products_name_trgm ON products USING GIN(name gin_trgm_ops)")
    op.execute("CREATE INDEX ix_products_sku_trgm ON products USING GIN(sku gin_trgm_ops)")

    op.execute("CREATE INDEX ix_orders_search_vector ON orders USING GIN(search_vector)")
    op.execute("CREATE INDEX ix_orders_status_trgm ON orders USING GIN(status gin_trgm_ops)")

    op.execute("CREATE INDEX ix_users_search_vector ON users USING GIN(search_vector)")
    op.execute("CREATE INDEX ix_users_username_trgm ON users USING GIN(username gin_trgm_ops)")
    op.execute("CREATE INDEX ix_users_email_trgm ON users USING GIN(email gin_trgm_ops)")

    # 3. Create trigger functions for automatic search_vector updates
    op.execute("""
        CREATE OR REPLACE FUNCTION product_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('simple', COALESCE(NEW.name, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(NEW.sku, '')), 'B') ||
                setweight(to_tsvector('simple', COALESCE(NEW.category, '')), 'C') ||
                setweight(to_tsvector('simple', COALESCE(NEW.description, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION order_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('simple', COALESCE(NEW.status, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(NEW.user_id::text, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION user_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('simple', COALESCE(NEW.username, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(NEW.email, '')), 'B') ||
                setweight(to_tsvector('simple', COALESCE(NEW.full_name, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    # 4. Create triggers
    op.execute("""
        CREATE TRIGGER product_search_vector_trigger
            BEFORE INSERT OR UPDATE ON products
            FOR EACH ROW EXECUTE FUNCTION product_search_vector_update()
    """)

    op.execute("""
        CREATE TRIGGER order_search_vector_trigger
            BEFORE INSERT OR UPDATE ON orders
            FOR EACH ROW EXECUTE FUNCTION order_search_vector_update()
    """)

    op.execute("""
        CREATE TRIGGER user_search_vector_trigger
            BEFORE INSERT OR UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION user_search_vector_update()
    """)

    # 5. Backfill existing data with search_vector
    op.execute("""
        UPDATE products SET search_vector =
            setweight(to_tsvector('simple', COALESCE(name, '')), 'A') ||
            setweight(to_tsvector('simple', COALESCE(sku, '')), 'B') ||
            setweight(to_tsvector('simple', COALESCE(category, '')), 'C') ||
            setweight(to_tsvector('simple', COALESCE(description, '')), 'D')
    """)

    op.execute("""
        UPDATE orders SET search_vector =
            setweight(to_tsvector('simple', COALESCE(status, '')), 'A') ||
            setweight(to_tsvector('simple', COALESCE(user_id::text, '')), 'B')
    """)

    op.execute("""
        UPDATE users SET search_vector =
            setweight(to_tsvector('simple', COALESCE(username, '')), 'A') ||
            setweight(to_tsvector('simple', COALESCE(email, '')), 'B') ||
            setweight(to_tsvector('simple', COALESCE(full_name, '')), 'C')
    """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP TRIGGER IF EXISTS user_search_vector_trigger ON users")
    op.execute("DROP TRIGGER IF EXISTS order_search_vector_trigger ON orders")
    op.execute("DROP TRIGGER IF EXISTS product_search_vector_trigger ON products")

    op.execute("DROP FUNCTION IF EXISTS user_search_vector_update()")
    op.execute("DROP FUNCTION IF EXISTS order_search_vector_update()")
    op.execute("DROP FUNCTION IF EXISTS product_search_vector_update()")

    op.drop_index("ix_users_email_trgm", table_name="users")
    op.drop_index("ix_users_username_trgm", table_name="users")
    op.drop_index("ix_users_search_vector", table_name="users")

    op.drop_index("ix_orders_status_trgm", table_name="orders")
    op.drop_index("ix_orders_search_vector", table_name="orders")

    op.drop_index("ix_products_sku_trgm", table_name="products")
    op.drop_index("ix_products_name_trgm", table_name="products")
    op.drop_index("ix_products_search_vector", table_name="products")

    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
