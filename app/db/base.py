from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import declarative_base, declared_attr


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    @declared_attr
    def created_at(cls):
        return Column(DateTime, server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ConfigMixin:
    """Mixin for config database models (no timestamps)."""

    pass


UserBase = declarative_base(cls=TimestampMixin)
BusinessBase = declarative_base(cls=TimestampMixin)
ConfigBase = declarative_base(cls=ConfigMixin)
