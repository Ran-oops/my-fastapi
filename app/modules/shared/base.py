from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


ModelType = type["ModelType"]
CreateSchemaType = type["CreateSchemaType"]
UpdateSchemaType = type["UpdateSchemaType"]


class CRUDBase[ModelType, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel]:
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        result = await db.execute(select(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        return result.scalar_one_or_none()

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        result = await db.execute(
            select(self.model)
            .order_by(self.model.id.desc())  # type: ignore[attr-defined]
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self, db: AsyncSession) -> int:
        result = await db.execute(select(func.count()).select_from(self.model))
        scalar_result = result.scalar()
        return scalar_result if scalar_result is not None else 0

    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, id: int) -> ModelType | None:
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
