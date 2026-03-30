from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


# Convert async URL to sync URL
sync_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")

sync_engine = create_engine(sync_url, pool_pre_ping=True)

SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=sync_engine)


def get_sync_session():
    """Yield a sync session for Celery worker tasks."""
    with SyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
