from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository[ModelType, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel]:
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, session: AsyncSession, id: Any) -> ModelType | None:
        result = await session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(self, session: AsyncSession, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        result = await session.execute(select(self.model).order_by(self.model.id.desc()).offset(skip).limit(limit))
        return result.scalars().all()

    async def count(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(self.model))
        scalar_result = result.scalar()
        return scalar_result if scalar_result is not None else 0

    async def create(self, session: AsyncSession, data: CreateSchemaType) -> ModelType:
        data_dict = data.model_dump()
        instance = self.model(**data_dict)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance

    async def update(
        self,
        session: AsyncSession,
        instance: ModelType,
        data: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        update_data = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        await session.commit()
        await session.refresh(instance)
        return instance

    async def delete(self, session: AsyncSession, id: int) -> ModelType | None:
        instance = await self.get(session, id)
        if instance:
            await session.delete(instance)
            await session.commit()
        return instance

    async def create_multi(
        self,
        session: AsyncSession,
        data_list: list[CreateSchemaType],
    ) -> Sequence[ModelType]:
        """批量创建记录。"""
        if not data_list:
            return []

        data_dicts = [data.model_dump() for data in data_list]
        stmt = insert(self.model).values(data_dicts).returning(self.model)
        result = await session.execute(stmt)
        await session.commit()
        return result.scalars().all()

    async def delete_multi(self, session: AsyncSession, ids: list[int]) -> int:
        """批量删除记录，返回删除数量。"""
        if not ids:
            return 0

        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount if result.rowcount else 0
