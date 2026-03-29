from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import declarative_base, declared_attr


class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return Column(DateTime, server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


Base = declarative_base(cls=TimestampMixin)

UserBase = Base  # Compatibility alias for existing models
