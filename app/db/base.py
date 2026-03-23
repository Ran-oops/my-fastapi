from datetime import datetime
from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import declarative_base, declared_attr


class UserBase:
    """Base class for User Database models (PostgreSQL)"""

    @declared_attr
    def created_at(cls):
        return Column(DateTime, server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
        )


class BusinessBase:
    """Base class for Business Database models (SQL Server)"""

    @declared_attr
    def created_at(cls):
        return Column(DateTime, server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
        )


class ConfigBase:
    """Base class for Config Database models (MySQL - Read Only)"""

    pass


UserDBBase = declarative_base(cls=UserBase)
BusinessDBBase = declarative_base(cls=BusinessBase)
ConfigDBBase = declarative_base(cls=ConfigBase)
