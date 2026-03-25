from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.base import UserBase

user_roles = Table(
    "user_roles",
    UserBase.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)
